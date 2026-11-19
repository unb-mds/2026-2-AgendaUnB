import re
import time
import hashlib
import json
from datetime import datetime, time as dt_time, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool

from src.database.connection import get_db
from src.database.models import (
    CandidateVote,
    ClassFollow,
    ImportItem,
    ImportOperation,
    PersonalEvent,
    Profile,
    Syllabus,
    SyllabusCandidate,
    SyllabusVersion,
)
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.events.router import _category_id, _personal_read
from src.modules.classes.services import followed_available_offering
from src.modules.syllabus.schemas import (
    CandidateVoteSummaryRead,
    ConfirmSyllabusRequest,
    ConfirmSyllabusResponse,
    ConfirmItemResult,
    CreateRevisionRequest,
    RevisionCandidateInput,
    SyllabusCandidateRead,
    SyllabusDetailResponse,
    SyllabusListItem,
    SyllabusListResponse,
    SyllabusUploadResponse,
    SyllabusVersionListResponse,
    UpdateVersionRequest,
    ValidateProvenanceRequest,
    VersionStatusResponse,
    VersionVotesResponse,
    VoteVersionRequest,
    VoteVersionResponse,
)
from src.modules.syllabus.services import process_syllabus_upload, validate_pdf_file
from src.modules.syllabus.timing import duration_ms
from src.modules.syllabus.processing_config import ProcessingConfig
from src.modules.syllabus.preparation import (
    TextInput, ExtractionAuthorization, PreparationPreview, checked_pages, extract_pdf_isolated,
    owned_plan, preview, authorize,
)
from src.modules.syllabus.services import UPLOAD_VALIDATION_TIMEOUT_SECONDS
from src.modules.syllabus.versions import SHARED_CONTENT_NOTICE, summarize_version_votes
from src.modules.syllabus.worker import spawn_worker_drain, utcnow

router = APIRouter(prefix="/syllabus", tags=["syllabus"])


def _sqlstate(error: DBAPIError) -> str | None:
    original = getattr(error, "orig", None)
    return getattr(original, "sqlstate", None) or getattr(original, "pgcode", None)


def _confirmation_error(error: DBAPIError) -> HTTPException:
    code = _sqlstate(error)
    mapping = {
        "42501": (403, "Você não tem permissão para acessar esta versão do plano."),
        "P0002": (404, "Plano, versão ou candidato não encontrado."),
        "22023": (422, "A seleção contém dados inválidos ou uma data que precisa ser corrigida."),
        "55000": (409, "O plano ainda não está pronto para confirmação."),
        "AG409": (409, "Esta chave de idempotência já foi usada com outro conteúdo."),
    }
    status_code, detail = mapping.get(code, (503, "Não foi possível confirmar os candidatos agora."))
    return HTTPException(status_code=status_code, detail=detail)


def _confirmation_payload(payload: ConfirmSyllabusRequest) -> list[dict]:
    items = []
    for candidate in payload.candidates:
        item = {"candidato_id": str(candidate.candidate_id)}
        if candidate.title is not None:
            item["titulo"] = candidate.title
        if candidate.description is not None:
            item["descricao"] = candidate.description
        if candidate.kind is not None:
            item["tipo"] = candidate.kind
        if candidate.all_day:
            item["dia_inteiro"] = True
            item["data_inicio"] = candidate.start_date.isoformat()
            if candidate.end_date is not None:
                item["data_fim"] = candidate.end_date.isoformat()
        elif candidate.starts_at is not None:
            item["inicio"] = candidate.starts_at.isoformat()
        if candidate.category is not None:
            item["categoria"] = candidate.category
        items.append(item)
    return items


def _confirmation_response(db, syllabus_id: UUID, user_id: UUID, operation_id: UUID,
                           rows: list[dict], requested: list, *, repeated: bool) -> ConfirmSyllabusResponse:
    event_ids = [UUID(str(row["evento_id"])) for row in rows if row.get("evento_id")]
    events = db.scalars(
        select(PersonalEvent)
        .where(PersonalEvent.user_id == user_id, PersonalEvent.id.in_(event_ids))
        .options(joinedload(PersonalEvent.campus), joinedload(PersonalEvent.category))
        .order_by(PersonalEvent.starts_at.asc(), PersonalEvent.id.asc())
    ).all() if event_ids else []
    row_by_candidate = {UUID(str(row["candidato_id"])): row for row in rows}
    item_results = []
    for reviewed in requested:
        saved = row_by_candidate[reviewed.candidate_id]
        event_id = UUID(str(saved["evento_id"])) if saved.get("evento_id") else None
        item_results.append(ConfirmItemResult(
            candidateId=reviewed.candidate_id,
            eventId=event_id,
            result=saved["resultado"],
            removed=bool(saved.get("removido", event_id is None)),
            type=reviewed.kind or saved.get("tipo_revisado"),
        ))
    return ConfirmSyllabusResponse(
        syllabusId=syllabus_id,
        operationId=operation_id,
        repeated=repeated,
        items=item_results,
        events=[_personal_read(event) for event in events],
    )


def _can_read_version(db: Session, user_id: UUID, syllabus: Syllabus, version: SyllabusVersion | None) -> bool:
    if version is not None and db.bind.dialect.name == "postgresql":
        try:
            return bool(db.scalar(
                text("select public.ator_pode_ler_versao(:actor_id, :version_id)"),
                {"actor_id": user_id, "version_id": version.id},
            ))
        except DBAPIError as error:
            db.rollback()
            raise HTTPException(status_code=503, detail="Não foi possível verificar o acesso ao plano.") from error
    if version is None:
        return syllabus.user_id == user_id
    if version.author_id == user_id:
        return True
    return (
        version.visibility == "compartilhada"
        and syllabus.offering_id is not None
        and db.get(ClassFollow, (user_id, syllabus.offering_id)) is not None
    )


def _auto_share_version_if_eligible(
    db: Session,
    syllabus: Syllabus,
    version: SyllabusVersion | None,
    *,
    candidates_count: int = 1,
    initial_only: bool = False,
) -> bool:
    """Compartilha automaticamente v1 vinculada a oferta concluída, salvo se retirada anteriormente (ADR-010)."""
    if (
        version is None
        or syllabus.offering_id is None
        or syllabus.status not in {"completed", "concluido"}
        or version.visibility != "privada"
        or version.withdrawn_at is not None
        or candidates_count <= 0
        or (initial_only and version.number != 1)
    ):
        return False
    version.visibility = "compartilhada"
    version.shared_at = version.shared_at or utcnow()
    return True


def _rebind_events_for_revision(
    db: Session,
    *,
    user_id: UUID,
    syllabus_id: UUID,
    version_id: UUID | None,
    idempotency_key: str,
    requested_candidates: list,
) -> None:
    if version_id is None or not requested_candidates:
        return
    existing_op = db.scalar(
        select(ImportOperation.id).where(
            ImportOperation.user_id == user_id,
            ImportOperation.idempotency_key == idempotency_key,
        )
    )
    if existing_op is not None:
        return
    requested_ids = [item.candidate_id for item in requested_candidates]
    target_candidates = db.scalars(
        select(SyllabusCandidate).where(
            SyllabusCandidate.syllabus_id == syllabus_id,
            SyllabusCandidate.version_id == version_id,
            SyllabusCandidate.id.in_(requested_ids),
        )
    ).all()
    if not any(c.order is not None for c in target_candidates):
        return
    user_events = db.scalars(
        select(PersonalEvent).where(
            PersonalEvent.user_id == user_id,
            PersonalEvent.origin_syllabus_id == syllabus_id,
            PersonalEvent.origin_candidate_id.is_not(None),
        )
    ).all()
    if not user_events:
        return
    origin_ids = [ev.origin_candidate_id for ev in user_events if ev.origin_candidate_id is not None]
    origin_candidates = db.scalars(
        select(SyllabusCandidate).where(SyllabusCandidate.id.in_(origin_ids))
    ).all()
    order_by_origin_id = {c.id: c.order for c in origin_candidates if c.order is not None}
    event_by_order = {
        order_by_origin_id[ev.origin_candidate_id]: ev
        for ev in user_events
        if ev.origin_candidate_id in order_by_origin_id
    }
    for candidate in target_candidates:
        if candidate.order is None:
            continue
        existing_event = event_by_order.get(candidate.order)
        if existing_event is not None and existing_event.origin_candidate_id != candidate.id:
            existing_event.origin_candidate_id = candidate.id
            existing_event.origin_version_id = candidate.version_id
            existing_event.origin_page = candidate.source_page
            existing_event.origin_excerpt = candidate.source_excerpt
    db.flush()


def _confirm_sqlite(syllabus_id: UUID, payload: ConfirmSyllabusRequest, user_id: UUID,
                    idempotency_key: str, db: Session, resolved_version_id: UUID | None = None) -> ConfirmSyllabusResponse:
    """ORM equivalente usado pela suíte SQLite; produção usa a função PostgreSQL."""
    syllabus = db.get(Syllabus, syllabus_id)
    if syllabus is None:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
    version_id = resolved_version_id if resolved_version_id is not None else syllabus.approved_version_id
    version = db.get(SyllabusVersion, version_id) if version_id is not None else None
    if not _can_read_version(db, user_id, syllabus, version):
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
    if syllabus.status not in {"completed", "concluido"}:
        raise HTTPException(status_code=409, detail="O plano ainda não está pronto para confirmação.")

    items = _confirmation_payload(payload)
    canonical = json.dumps({"version": str(version_id or ""), "items": items},
                           ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    operation = db.scalar(select(ImportOperation).where(
        ImportOperation.user_id == user_id,
        ImportOperation.idempotency_key == idempotency_key,
    ))
    if operation is not None:
        if operation.content_hash != content_hash:
            raise HTTPException(status_code=409, detail="Esta chave de idempotência já foi usada com outro conteúdo.")
        saved = db.scalars(select(ImportItem).where(ImportItem.operation_id == operation.id)).all()
        rows = []
        for item in saved:
            removed = item.event_id is None or db.get(PersonalEvent, item.event_id) is None
            rows.append({
                "candidato_id": item.candidate_id,
                "evento_id": None if removed else item.event_id,
                "resultado": item.result,
                "removido": removed,
                "tipo_revisado": item.candidate_type,
            })
        return _confirmation_response(db, syllabus_id, user_id, operation.id, rows, payload.candidates,
                                      repeated=True)

    _rebind_events_for_revision(
        db,
        user_id=user_id,
        syllabus_id=syllabus_id,
        version_id=version_id,
        idempotency_key=idempotency_key,
        requested_candidates=payload.candidates,
    )

    requested_ids = [item.candidate_id for item in payload.candidates]
    query = select(SyllabusCandidate).where(
        SyllabusCandidate.syllabus_id == syllabus_id,
        SyllabusCandidate.id.in_(requested_ids),
    )
    if version_id is not None:
        query = query.where(SyllabusCandidate.version_id == version_id)
    candidates = db.scalars(query).all()
    by_id = {candidate.id: candidate for candidate in candidates}
    if len(by_id) != len(requested_ids):
        raise HTTPException(status_code=422, detail="Um ou mais candidatos não pertencem a este plano.")

    prepared = []
    for reviewed in payload.candidates:
        candidate = by_id[reviewed.candidate_id]
        if candidate.status == "descartado" and (version is None or version.author_id == user_id):
            raise HTTPException(status_code=422, detail="Um candidato descartado não pode ser confirmado.")
        title = (reviewed.title or candidate.title).strip()
        if len(title) < 3:
            raise HTTPException(status_code=422, detail="O título revisado deve ter ao menos 3 caracteres.")
        if reviewed.all_day:
            start_date = reviewed.start_date
            end_date = reviewed.end_date or (start_date + timedelta(days=1))
            starts_at = datetime.combine(start_date, dt_time.min, tzinfo=timezone(timedelta(hours=-3)))
        else:
            start_date = None
            end_date = None
            if reviewed.starts_at is not None:
                starts_at = reviewed.starts_at
            elif not candidate.ambiguous and candidate.starts_at is not None:
                starts_at = (
                    candidate.starts_at.replace(tzinfo=timezone.utc)
                    if candidate.starts_at.tzinfo is None
                    else candidate.starts_at
                )
            elif (
                not candidate.ambiguous
                and candidate.data_sugerida is not None
                and candidate.hora_sugerida is not None
            ):
                starts_at = datetime.combine(
                    candidate.data_sugerida,
                    candidate.hora_sugerida,
                    tzinfo=timezone(timedelta(hours=-3)),
                )
            else:
                starts_at = None
            if starts_at is None or starts_at.tzinfo is None or starts_at.utcoffset() is None:
                raise HTTPException(status_code=422, detail="Corrija a data ambígua antes de confirmar o candidato.")
        prepared.append((reviewed, candidate, title, starts_at, reviewed.all_day, start_date, end_date))

    operation = ImportOperation(
        user_id=user_id,
        idempotency_key=idempotency_key,
        version_id=version_id,
        content_hash=content_hash,
    )
    db.add(operation)
    db.flush()
    rows = []
    for reviewed, candidate, title, starts_at, all_day, start_date, end_date in prepared:
        event = db.scalar(select(PersonalEvent).where(
            PersonalEvent.user_id == user_id,
            PersonalEvent.origin_candidate_id == candidate.id,
        ))
        result = "ja_importado" if event else "criado"
        if event is None:
            event = PersonalEvent(
                user_id=user_id,
                title=title,
                description=reviewed.description or candidate.source_excerpt,
                starts_at=starts_at,
                all_day=all_day,
                start_date=start_date,
                end_date=end_date,
                category_id=_category_id(db, reviewed.category),
                origin_syllabus_id=syllabus.id,
                origin_candidate_id=candidate.id,
                origin_version_id=candidate.version_id or version_id,
                origin_page=candidate.source_page,
                origin_excerpt=candidate.source_excerpt,
            )
            db.add(event)
            db.flush()
        else:
            if reviewed.title is not None:
                event.title = title
            if reviewed.starts_at is not None or reviewed.all_day:
                event.starts_at = starts_at
                event.all_day = all_day
                event.start_date = start_date
                event.end_date = end_date
            if reviewed.description is not None:
                event.description = reviewed.description
            if reviewed.category is not None:
                event.category_id = _category_id(db, reviewed.category)
        if version is None or (version.author_id == user_id and version.visibility == "privada"):
            if reviewed.kind is not None:
                candidate.kind = reviewed.kind
            candidate.status = "confirmado"
        saved = ImportItem(
            operation_id=operation.id,
            candidate_id=candidate.id,
            event_id=event.id,
            result=result,
            candidate_type=reviewed.kind,
        )
        db.add(saved)
        rows.append({
            "candidato_id": candidate.id,
            "evento_id": event.id,
            "resultado": result,
            "removido": False,
            "tipo_revisado": reviewed.kind,
        })
    if syllabus.user_id == user_id:
        _auto_share_version_if_eligible(db, syllabus, version, candidates_count=len(prepared), initial_only=True)
    db.commit()
    return _confirmation_response(db, syllabus_id, user_id, operation.id, rows, payload.candidates, repeated=False)


def _candidate_read(
    candidate: SyllabusCandidate,
    *,
    status_override: str | None = None,
    kind_override: str | None = None,
    confirm_count: int = 0,
    contest_count: int = 0,
    my_vote: str | None = None,
) -> SyllabusCandidateRead:
    return SyllabusCandidateRead(
        id=candidate.id,
        title=candidate.title,
        type=kind_override or candidate.kind,
        startsAt=candidate.starts_at,
        ambiguous=candidate.ambiguous,
        sourcePage=candidate.source_page,
        sourceExcerpt=candidate.source_excerpt,
        status=status_override or candidate.status,
        suggestedDate=candidate.data_sugerida,
        suggestedTime=candidate.hora_sugerida,
        ambiguousFields=candidate.campos_ambiguos or [],
        versionId=candidate.version_id,
        confirmCount=confirm_count,
        contestCount=contest_count,
        divergent=contest_count > 0,
        myVote=my_vote,
    )


@router.get("", response_model=SyllabusListResponse, summary="Lista planos do usuário")
def list_syllabi(
    offering_id: UUID | None = Query(None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyllabusListResponse:
    owned = (Syllabus.user_id == current_user.id)
    if offering_id is not None:
        owned = owned & (Syllabus.offering_id == offering_id)
    total = db.scalar(select(func.count()).select_from(Syllabus).where(owned)) or 0
    records = db.scalars(
        select(Syllabus)
        .where(owned)
        .order_by(Syllabus.created_at.desc(), Syllabus.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return SyllabusListResponse(
        items=[SyllabusListItem.model_validate(record) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/upload",
    response_model=SyllabusUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload e rastreamento de plano de ensino em PDF",
)
async def upload_syllabus(
    offering_id: UUID = Form(...),
    file: UploadFile = File(..., description="Arquivo PDF do plano de ensino"),
    disciplina: str | None = Form(None, description="Nome da disciplina (opcional)"),
    turma: str | None = Form(None, description="Turma da disciplina (opcional)"),
    ano: int | None = Form(None, ge=2000, le=2100, description="Ano de referência"),
    semestre: int | None = Form(None, ge=1, le=2, description="Semestre de referência"),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyllabusUploadResponse:
    """
    Recebe o arquivo PDF do plano de ensino, realiza validações estruturais rigorosas
    (extensão .pdf, MIME type, assinatura de bytes, integridade, texto legível e tamanho máximo)
    e extrai o texto localmente, sem enviar ou armazenar o PDF original.

    Retorna 202 com texto privado preparado. A fila só fica elegível após
    autorização explícita do dono em /{id}/extractions.
    """
    offer = followed_available_offering(db, offering_id, current_user.id)
    started = time.monotonic()
    try:
        content = await validate_pdf_file(file)
        pages = await run_in_threadpool(extract_pdf_isolated, content, UPLOAD_VALIDATION_TIMEOUT_SECONDS)
    finally:
        await file.close()  # Fecha/remove o temporário ao fim da extração, inclusive em falha.
    file_size = len(content)
    del content
    syllabus = await run_in_threadpool(
        process_syllabus_upload, user_id=current_user.id,
        filename=file.filename or "syllabus.pdf", file_size=file_size, pages=pages,
        preparation_duration_ms=round((time.monotonic()-started)*1000),
        db=db, offering_id=offer.id, disciplina=offer.subject.name, turma=offer.class_number, ano=offer.year, semestre=offer.semester,
    )

    return SyllabusUploadResponse.model_validate(syllabus)


@router.post("/text", response_model=SyllabusUploadResponse, status_code=202)
def prepare_syllabus_text(payload: TextInput, current_user: CurrentUser = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    offer = followed_available_offering(db, payload.offering_id, current_user.id)
    started = time.monotonic()
    pages = checked_pages([{"pagina": None, "texto": payload.text}])
    plan = process_syllabus_upload(user_id=current_user.id, filename="texto-revisado.txt",
        file_size=len(pages[0]["texto"].encode("utf-8")), pages=pages, file_type="text", db=db,
        preparation_duration_ms=round((time.monotonic()-started)*1000),
        offering_id=offer.id, disciplina=offer.subject.name, turma=offer.class_number, ano=offer.year, semestre=offer.semester)
    return SyllabusUploadResponse.model_validate(plan)


@router.get("/{syllabus_id}/text", response_model=PreparationPreview)
def get_syllabus_text(syllabus_id: UUID, response: Response, current_user: CurrentUser = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return preview(owned_plan(db, current_user.id, syllabus_id))


@router.post("/{syllabus_id}/extractions", response_model=SyllabusUploadResponse, status_code=202)
def authorize_syllabus_text(syllabus_id: UUID, payload: ExtractionAuthorization,
                            current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = owned_plan(db, current_user.id, syllabus_id, lock=True)
    try:
        plan = authorize(db, plan, payload, ProcessingConfig.from_env())
        spawn_worker_drain()
        response = SyllabusUploadResponse.model_validate(plan)
        response.message = "Autorização registrada. Consulte o andamento do plano."
        return response
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(503, "Não foi possível registrar a autorização. Tente novamente.") from None


@router.get(
    "/{syllabus_id}",
    response_model=SyllabusDetailResponse,
    summary="Consulta o status e dados de rastreamento do plano de ensino",
)
def get_syllabus_status(
    syllabus_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyllabusDetailResponse:
    """Consulta o plano privado do autor ou uma versão compartilhada autorizada."""
    syllabus = db.get(Syllabus, syllabus_id)

    if not syllabus:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")

    is_owner = syllabus.user_id == current_user.id
    version_id = syllabus.approved_version_id
    version = db.get(SyllabusVersion, version_id) if version_id is not None else None
    if not _can_read_version(db, current_user.id, syllabus, version):
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")

    candidate_query = select(SyllabusCandidate).where(SyllabusCandidate.syllabus_id == syllabus.id)
    if version_id is not None:
        candidate_query = candidate_query.where(SyllabusCandidate.version_id == version_id)
    candidates = db.scalars(
        candidate_query.order_by(SyllabusCandidate.source_page.asc(), SyllabusCandidate.id.asc())
    ).all()
    if is_owner and _auto_share_version_if_eligible(
        db, syllabus, version, candidates_count=len(candidates), initial_only=True
    ):
        db.commit()
    own_imports: dict[UUID, tuple[str, UUID | None, str | None]] = {}
    active_owner_events: set[UUID] = set()
    if not is_owner and candidates:
        candidate_ids = [candidate.id for candidate in candidates]
        decisions = db.execute(
            select(ImportItem.candidate_id, ImportItem.result, ImportItem.event_id, ImportItem.candidate_type)
            .join(ImportOperation, ImportOperation.id == ImportItem.operation_id)
            .where(
                ImportOperation.user_id == current_user.id,
                ImportItem.candidate_id.in_(candidate_ids),
            )
            .order_by(ImportOperation.created_at.desc())
        ).all()
        for candidate_id, result, event_id, kind in decisions:
            own_imports.setdefault(candidate_id, (result, event_id, kind))
    elif is_owner and candidates:
        candidate_ids = [candidate.id for candidate in candidates]
        active_owner_events = set(
            db.scalars(
                select(PersonalEvent.origin_candidate_id).where(
                    PersonalEvent.user_id == current_user.id,
                    PersonalEvent.origin_candidate_id.in_(candidate_ids),
                )
            ).all()
        )
    if is_owner and syllabus.status == "pendente" and syllabus.authorized_at is not None:
        next_at = syllabus.next_attempt_at
        if next_at is not None and next_at.tzinfo is None:
            next_at = next_at.replace(tzinfo=timezone.utc)
        if next_at is None or next_at <= utcnow():
            spawn_worker_drain()

    return SyllabusDetailResponse(
        id=syllabus.id,
        offeringId=syllabus.offering_id,
        userId=syllabus.user_id,
        fileName=syllabus.file_name if is_owner else None,
        filePath=syllabus.file_path if is_owner else None,
        fileSize=syllabus.file_size if is_owner else None,
        fileType=syllabus.file_type,
        status=syllabus.status,
        extractedEventsCount=syllabus.extracted_events_count if is_owner else len(candidates),
        errorMessage=syllabus.error_message if is_owner else None,
        errorCode=syllabus.erro_codigo if is_owner else None,
        pageCount=syllabus.paginas if is_owner else None,
        attempts=syllabus.execucao_atual if is_owner else 0,
        processingStartedAt=syllabus.processamento_iniciado_em if is_owner else None,
        processedAt=syllabus.processado_em if is_owner else None,
        processingDurationMs=syllabus.processing_duration_ms if is_owner else None,
        totalDurationMs=duration_ms(syllabus.queued_at or syllabus.created_at, syllabus.processado_em) if is_owner else None,
        authorizationRequired=syllabus.authorization_required if is_owner else False,
        preparedTextAvailable=bool(syllabus.prepared_pages) if is_owner else False,
        preparationDurationMs=syllabus.preparation_duration_ms if is_owner else None,
        redactedCount=syllabus.redacted_count if is_owner else None,
        reviewDurationMs=duration_ms(syllabus.created_at, syllabus.authorized_at) if is_owner else None,
        disciplina=syllabus.disciplina,
        turma=syllabus.turma,
        ano=syllabus.ano,
        semestre=syllabus.semestre,
        createdAt=syllabus.created_at,
        candidates=[
            _candidate_read(
                candidate,
                status_override=(
                    ("confirmado" if own_imports.get(candidate.id, (None, None, None))[1] is not None else "pendente")
                    if not is_owner
                    else (
                        "confirmado"
                        if candidate.id in active_owner_events
                        else ("pendente" if candidate.status == "confirmado" else None)
                    )
                ),
                kind_override=own_imports.get(candidate.id, (None, None, None))[2] if not is_owner else None,
            )
            for candidate in candidates
        ],
    )


@router.post(
    "/{syllabus_id}/confirm",
    response_model=ConfirmSyllabusResponse,
    summary="Confirma candidatos revisados na agenda pessoal",
)
def confirm_syllabus_candidates(
    syllabus_id: UUID,
    payload: ConfirmSyllabusRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConfirmSyllabusResponse:
    syllabus = db.get(Syllabus, syllabus_id)
    if syllabus is None:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")

    version_id = payload.version_id or syllabus.approved_version_id
    if payload.version_id is not None:
        version = db.get(SyllabusVersion, payload.version_id)
        if version is None or version.syllabus_id != syllabus_id:
            raise HTTPException(status_code=404, detail="Versão do plano não encontrada.")
    else:
        if version_id is None:
            version_id = db.scalar(select(SyllabusCandidate.version_id).where(
                SyllabusCandidate.syllabus_id == syllabus_id,
                SyllabusCandidate.id == payload.candidates[0].candidate_id,
            ))
        version = db.get(SyllabusVersion, version_id) if version_id is not None else None

    if not _can_read_version(db, current_user.id, syllabus, version):
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")

    if syllabus.status not in {"completed", "concluido"}:
        raise HTTPException(status_code=409, detail="O plano ainda não está pronto para confirmação.")

    if db.bind.dialect.name != "postgresql":
        return _confirm_sqlite(
            syllabus_id, payload, current_user.id, idempotency_key, db, resolved_version_id=version_id
        )
    if version_id is None:
        raise HTTPException(status_code=409, detail="O plano não possui uma versão aprovada para confirmação.")

    _rebind_events_for_revision(
        db,
        user_id=current_user.id,
        syllabus_id=syllabus_id,
        version_id=version_id,
        idempotency_key=idempotency_key,
        requested_candidates=payload.candidates,
    )

    items = _confirmation_payload(payload)
    try:
        result = db.execute(
            text("select public.confirmar_importacao(:actor_id, :key, :version_id, cast(:items as jsonb))"),
            {
                "actor_id": current_user.id,
                "key": idempotency_key,
                "version_id": version_id,
                "items": json.dumps(items, ensure_ascii=False),
            },
        ).scalar_one()
        result = result if isinstance(result, dict) else json.loads(result)
        operation_id = UUID(str(result["operacao_id"]))
        if syllabus.user_id == current_user.id:
            _auto_share_version_if_eligible(
                db, syllabus, version, candidates_count=len(payload.candidates), initial_only=True
            )
        db.commit()
    except DBAPIError as error:
        db.rollback()
        raise _confirmation_error(error) from error

    rows = result.get("itens") or []
    for row in rows:
        row.setdefault("tipo_revisado", next((item.kind for item in payload.candidates
                                               if str(item.candidate_id) == str(row.get("candidato_id"))), None))
    return _confirmation_response(
        db,
        syllabus_id,
        current_user.id,
        operation_id,
        rows,
        payload.candidates,
        repeated=bool(result.get("repetida")),
    )


@router.delete(
    "/{syllabus_id}/candidates/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Descarta um candidato de um plano privado",
)
def discard_syllabus_candidate(
    syllabus_id: UUID,
    candidate_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    syllabus = db.scalar(
        select(Syllabus).where(Syllabus.id == syllabus_id, Syllabus.user_id == current_user.id).with_for_update()
    )
    if syllabus is None:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
    if syllabus.status not in {"completed", "concluido"}:
        raise HTTPException(status_code=409, detail="Só é possível descartar candidatos de um plano concluído.")
    version_id = syllabus.approved_version_id
    version = db.get(SyllabusVersion, version_id) if version_id else None
    if version is not None and version.visibility != "privada":
        raise HTTPException(
            status_code=409,
            detail="O descarte individual de candidatos compartilhados exige criar uma revisão.",
        )
    candidate_query = select(SyllabusCandidate).where(
        SyllabusCandidate.id == candidate_id,
        SyllabusCandidate.syllabus_id == syllabus_id,
    )
    if version_id is not None:
        candidate_query = candidate_query.where(SyllabusCandidate.version_id == version_id)
    candidate = db.scalar(candidate_query.with_for_update())
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidato não encontrado neste plano.")
    if candidate.status == "confirmado":
        event = db.scalar(select(PersonalEvent.id).where(
            PersonalEvent.user_id == current_user.id,
            PersonalEvent.origin_candidate_id == candidate_id,
        ))
        if event is not None:
            raise HTTPException(status_code=409, detail="Remova primeiro o evento da agenda pessoal.")
    candidate.status = "descartado"
    candidate.revisado_em = utcnow()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _get_syllabus_version(db: Session, syllabus_id: UUID, version_id: UUID) -> tuple[Syllabus, SyllabusVersion]:
    syllabus = db.get(Syllabus, syllabus_id)
    version = db.get(SyllabusVersion, version_id)
    if syllabus is None or version is None or version.syllabus_id != syllabus_id:
        raise HTTPException(status_code=404, detail="Versão do plano não encontrada.")
    return syllabus, version


def _build_version_response(
    db: Session,
    syllabus: Syllabus,
    version: SyllabusVersion,
    current_user_id: UUID,
) -> VersionStatusResponse:
    candidates = db.scalars(
        select(SyllabusCandidate)
        .where(
            SyllabusCandidate.version_id == version.id,
            SyllabusCandidate.status != "descartado",
        )
        .order_by(
            SyllabusCandidate.order.asc().nulls_last(),
            SyllabusCandidate.source_page.asc().nulls_last(),
            SyllabusCandidate.id.asc(),
        )
    ).all()
    candidate_ids = [c.id for c in candidates]
    votes = (
        db.scalars(select(CandidateVote).where(CandidateVote.candidate_id.in_(candidate_ids))).all()
        if candidate_ids else []
    )
    votes_by_candidate: dict[UUID, list[CandidateVote]] = {}
    for vote in votes:
        votes_by_candidate.setdefault(vote.candidate_id, []).append(vote)

    candidate_reads = []
    for candidate in candidates:
        c_votes = votes_by_candidate.get(candidate.id, [])
        c_confirm = sum(1 for v in c_votes if v.value == "confirma")
        c_contest = sum(1 for v in c_votes if v.value == "contesta")
        c_my_vote = next((v.value for v in c_votes if v.user_id == current_user_id), None)
        candidate_reads.append(
            _candidate_read(
                candidate,
                confirm_count=c_confirm,
                contest_count=c_contest,
                my_vote=c_my_vote,
            )
        )

    return VersionStatusResponse(
        id=version.id,
        syllabusId=version.syllabus_id,
        offeringId=syllabus.offering_id,
        number=version.number,
        visibility=version.visibility,
        authorId=version.author_id,
        authorRole=version.author_role,
        sourceVersionId=version.source_version_id,
        institutionalProvenance=version.institutional_provenance,
        institutionalSourceUrl=version.institutional_source_url,
        sharedAt=version.shared_at,
        withdrawnAt=version.withdrawn_at,
        createdAt=version.created_at,
        membershipType="autodeclarado",
        sharedContentNotice=SHARED_CONTENT_NOTICE,
        candidates=candidate_reads,
    )


def _populate_revision_candidates(
    db: Session,
    *,
    syllabus_id: UUID,
    new_version_id: UUID,
    origin_id: UUID,
    candidate_inputs: list[RevisionCandidateInput],
) -> None:
    origin_candidates = {
        c.id: c
        for c in db.scalars(select(SyllabusCandidate).where(SyllabusCandidate.version_id == origin_id)).all()
    }
    db.execute(delete(SyllabusCandidate).where(SyllabusCandidate.version_id == new_version_id))
    db.flush()

    brasilia_tz = timezone(timedelta(hours=-3))
    used_orders: set[int] = set()
    for idx, item in enumerate(candidate_inputs):
        orig = origin_candidates.get(item.candidate_id) if item.candidate_id else None
        order = orig.order if orig is not None and orig.order is not None and orig.order not in used_orders else None
        if order is None:
            candidate_order = idx
            while candidate_order in used_orders:
                candidate_order += 1
            order = candidate_order
        used_orders.add(order)

        starts_at = item.starts_at
        if starts_at is not None:
            if starts_at.tzinfo is None:
                starts_at = starts_at.replace(tzinfo=timezone.utc)
            local_dt = starts_at.astimezone(brasilia_tz)
            suggested_date = item.suggested_date or local_dt.date()
            suggested_time = item.suggested_time or local_dt.time().replace(tzinfo=None)
        elif item.suggested_date is not None:
            suggested_date = item.suggested_date
            suggested_time = item.suggested_time
            starts_at = (
                datetime.combine(suggested_date, suggested_time, tzinfo=brasilia_tz)
                if suggested_time is not None
                else None
            )
        else:
            suggested_date = None
            suggested_time = None

        db.add(
            SyllabusCandidate(
                syllabus_id=syllabus_id,
                version_id=new_version_id,
                order=order,
                title=item.title,
                kind=item.kind or (orig.kind if orig else None),
                starts_at=starts_at,
                data_sugerida=suggested_date,
                hora_sugerida=suggested_time,
                ambiguous=item.ambiguous,
                campos_ambiguos=list(item.ambiguous_fields),
                source_page=item.source_page if item.source_page is not None else (orig.source_page if orig else None),
                source_excerpt=(
                    item.source_excerpt if item.source_excerpt is not None else (orig.source_excerpt if orig else None)
                ),
                status="pendente",
                processing_version=orig.processing_version if orig else None,
                provider=orig.provider if orig else None,
            )
        )
    db.flush()


@router.get(
    "/{syllabus_id}/versions",
    response_model=SyllabusVersionListResponse,
    summary="Lista versões autorizadas de um plano de ensino",
)
def list_syllabus_versions(
    syllabus_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyllabusVersionListResponse:
    syllabus = db.get(Syllabus, syllabus_id)
    if syllabus is None:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
    all_versions = db.scalars(
        select(SyllabusVersion)
        .where(SyllabusVersion.syllabus_id == syllabus_id)
        .order_by(SyllabusVersion.number.desc(), SyllabusVersion.id.asc())
    ).all()
    readable = [v for v in all_versions if _can_read_version(db, current_user.id, syllabus, v)]
    if not readable and syllabus.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
    return SyllabusVersionListResponse(
        syllabusId=syllabus.id,
        offeringId=syllabus.offering_id,
        membershipType="autodeclarado",
        sharedContentNotice=SHARED_CONTENT_NOTICE,
        items=[_build_version_response(db, syllabus, v, current_user.id) for v in readable],
        total=len(readable),
    )


@router.get(
    "/{syllabus_id}/versions/{version_id}",
    response_model=VersionStatusResponse,
    summary="Consulta os detalhes e avaliações de uma versão autorizada",
)
def get_syllabus_version(
    syllabus_id: UUID,
    version_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionStatusResponse:
    syllabus, version = _get_syllabus_version(db, syllabus_id, version_id)
    if not _can_read_version(db, current_user.id, syllabus, version):
        raise HTTPException(status_code=404, detail="Versão do plano não encontrada.")
    return _build_version_response(db, syllabus, version, current_user.id)


@router.put(
    "/{syllabus_id}/versions/{version_id}/sharing",
    response_model=VersionStatusResponse,
    summary="Compartilha voluntariamente uma versão do plano com os seguidores da turma",
)
def share_syllabus_version(
    syllabus_id: UUID,
    version_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionStatusResponse:
    syllabus, version = _get_syllabus_version(db, syllabus_id, version_id)
    if version.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o autor compartilha a versão.")
    if syllabus.offering_id is None:
        raise HTTPException(status_code=409, detail="Associe o plano a uma turma antes de compartilhar.")
    if syllabus.status not in {"completed", "concluido"}:
        raise HTTPException(status_code=409, detail="O plano ainda não terminou de ser processado.")

    if db.bind.dialect.name == "postgresql":
        try:
            db.execute(
                text("select (public.compartilhar_versao(:actor_id, :version_id)).id"),
                {"actor_id": current_user.id, "version_id": version_id},
            )
            db.commit()
            db.refresh(version)
        except DBAPIError as error:
            db.rollback()
            raise _confirmation_error(error) from error
    else:
        if version.visibility != "compartilhada":
            version.visibility = "compartilhada"
            version.shared_at = utcnow()
            db.commit()
            db.refresh(version)
    return _build_version_response(db, syllabus, version, current_user.id)


@router.delete(
    "/{syllabus_id}/versions/{version_id}/sharing",
    response_model=VersionStatusResponse,
    summary="Retira o compartilhamento de uma versão",
)
def withdraw_syllabus_version(
    syllabus_id: UUID,
    version_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionStatusResponse:
    syllabus, version = _get_syllabus_version(db, syllabus_id, version_id)
    if version.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas o autor ou um administrador retira o compartilhamento.")

    if db.bind.dialect.name == "postgresql":
        try:
            db.execute(
                text("select (public.retirar_compartilhamento(:actor_id, :version_id)).id"),
                {"actor_id": current_user.id, "version_id": version_id},
            )
            db.commit()
            db.refresh(version)
        except DBAPIError as error:
            db.rollback()
            raise _confirmation_error(error) from error
    else:
        if version.visibility != "privada":
            version.visibility = "privada"
            version.shared_at = None
            version.withdrawn_at = utcnow()
            version.withdrawn_by = current_user.id
            db.commit()
            db.refresh(version)
    return _build_version_response(db, syllabus, version, current_user.id)


@router.post(
    "/{syllabus_id}/versions",
    response_model=VersionStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cria uma nova versão revisada do plano",
)
def create_syllabus_revision(
    syllabus_id: UUID,
    payload: CreateRevisionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionStatusResponse:
    syllabus = db.get(Syllabus, syllabus_id)
    if syllabus is None:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
    source_id = payload.source_version_id or syllabus.approved_version_id
    if source_id is None:
        raise HTTPException(status_code=404, detail="Versão de origem não encontrada.")
    _, origin = _get_syllabus_version(db, syllabus_id, source_id)

    # Papel de professor ou admin nunca dá acesso a versões privadas de outra conta.
    if origin.author_id != current_user.id and origin.visibility != "compartilhada":
        raise HTTPException(status_code=404, detail="Versão do plano não encontrada.")

    author_role = db.scalar(select(Profile.papel).where(Profile.id == current_user.id)) or current_user.role or "student"
    if origin.author_id != current_user.id and not (
        origin.visibility == "compartilhada"
        and (
            author_role in ("professor", "admin")
            or (
                syllabus.offering_id is not None
                and db.get(ClassFollow, (current_user.id, syllabus.offering_id)) is not None
            )
        )
    ):
        raise HTTPException(status_code=403, detail="Siga a turma para revisar esta versão.")

    if syllabus.status not in {"completed", "concluido"}:
        raise HTTPException(status_code=409, detail="O plano ainda não terminou de ser processado.")

    should_share = payload.share or (payload.candidates is not None and syllabus.offering_id is not None)

    if db.bind.dialect.name == "postgresql":
        try:
            new_id = db.scalar(
                text("select (public.criar_revisao(:actor_id, :source_id)).id"),
                {"actor_id": current_user.id, "source_id": origin.id},
            )
            new_version = db.get(SyllabusVersion, new_id)
            if payload.candidates is not None:
                _populate_revision_candidates(
                    db,
                    syllabus_id=syllabus_id,
                    new_version_id=new_version.id,
                    origin_id=origin.id,
                    candidate_inputs=payload.candidates,
                )
            if should_share:
                db.execute(
                    text("select (public.compartilhar_versao(:actor_id, :version_id)).id"),
                    {"actor_id": current_user.id, "version_id": new_version.id},
                )
            if syllabus.user_id == current_user.id and origin.id == syllabus.approved_version_id:
                syllabus.approved_version_id = new_version.id
            db.commit()
            db.refresh(new_version)
        except DBAPIError as error:
            db.rollback()
            raise _confirmation_error(error) from error
    else:
        next_number = (db.scalar(
            select(func.max(SyllabusVersion.number)).where(SyllabusVersion.syllabus_id == syllabus_id)
        ) or 0) + 1
        inherits_provenance = bool(origin.institutional_provenance and author_role in ("professor", "admin"))
        new_version = SyllabusVersion(
            syllabus_id=syllabus_id,
            number=next_number,
            author_id=current_user.id,
            author_role=author_role,
            source_version_id=origin.id,
            visibility="privada",
            institutional_provenance=inherits_provenance,
            institutional_source_url=origin.institutional_source_url if inherits_provenance else None,
            provenance_validated_by=origin.provenance_validated_by if inherits_provenance else None,
            provenance_validated_at=origin.provenance_validated_at if inherits_provenance else None,
        )
        db.add(new_version)
        db.flush()

        if payload.candidates is not None:
            _populate_revision_candidates(
                db,
                syllabus_id=syllabus_id,
                new_version_id=new_version.id,
                origin_id=origin.id,
                candidate_inputs=payload.candidates,
            )
        else:
            origin_candidates = db.scalars(
                select(SyllabusCandidate)
                .where(
                    SyllabusCandidate.version_id == origin.id,
                    SyllabusCandidate.status != "descartado",
                )
                .order_by(SyllabusCandidate.order.asc().nulls_last(), SyllabusCandidate.id.asc())
            ).all()
            for orig in origin_candidates:
                db.add(
                    SyllabusCandidate(
                        syllabus_id=syllabus_id,
                        version_id=new_version.id,
                        order=orig.order,
                        title=orig.title,
                        kind=orig.kind,
                        starts_at=orig.starts_at,
                        data_sugerida=orig.data_sugerida,
                        hora_sugerida=orig.hora_sugerida,
                        ambiguous=orig.ambiguous,
                        campos_ambiguos=list(orig.campos_ambiguos or []),
                        source_page=orig.source_page,
                        source_excerpt=orig.source_excerpt,
                        status="pendente",
                        processing_version=orig.processing_version,
                        provider=orig.provider,
                    )
                )
            db.flush()

        if should_share:
            if syllabus.offering_id is None:
                db.rollback()
                raise HTTPException(status_code=409, detail="Associe o plano a uma turma antes de compartilhar.")
            new_version.visibility = "compartilhada"
            new_version.shared_at = utcnow()
        if syllabus.user_id == current_user.id and origin.id == syllabus.approved_version_id:
            syllabus.approved_version_id = new_version.id
        db.commit()
        db.refresh(new_version)

    return _build_version_response(db, syllabus, new_version, current_user.id)


@router.put(
    "/{syllabus_id}/versions/{version_id}",
    response_model=VersionStatusResponse,
    summary="Edita os candidatos de uma versão privada antes do compartilhamento",
)
def update_private_version(
    syllabus_id: UUID,
    version_id: UUID,
    payload: UpdateVersionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionStatusResponse:
    syllabus, version = _get_syllabus_version(db, syllabus_id, version_id)
    if version.author_id != current_user.id:
        if version.visibility != "compartilhada":
            raise HTTPException(status_code=404, detail="Versão do plano não encontrada.")
        raise HTTPException(status_code=403, detail="Apenas o autor pode editar um rascunho de versão.")
    if version.visibility == "compartilhada":
        raise HTTPException(
            status_code=409,
            detail="Conteúdo compartilhado não é editado diretamente: crie uma revisão.",
        )

    _populate_revision_candidates(
        db,
        syllabus_id=syllabus_id,
        new_version_id=version.id,
        origin_id=version.source_version_id or version.id,
        candidate_inputs=payload.candidates,
    )
    db.commit()
    db.refresh(version)
    return _build_version_response(db, syllabus, version, current_user.id)


@router.put(
    "/{syllabus_id}/versions/{version_id}/provenance",
    response_model=VersionStatusResponse,
    summary="Valida a procedência institucional de uma versão compartilhada",
)
def validate_version_institutional_provenance(
    syllabus_id: UUID,
    version_id: UUID,
    payload: ValidateProvenanceRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionStatusResponse:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas administradores validam a origem institucional.")
    url = payload.institutional_source_url.strip()
    if len(url) > 2048 or not re.match(r"^https?://[^\s<>\"]+$", url, flags=re.IGNORECASE):
        raise HTTPException(status_code=422, detail="Informe a URL pública oficial da evidência.")

    syllabus, version = _get_syllabus_version(db, syllabus_id, version_id)
    if version.visibility != "compartilhada":
        raise HTTPException(status_code=404, detail="Versão compartilhada não encontrada.")

    if db.bind.dialect.name == "postgresql":
        try:
            db.execute(
                text("select (public.validar_procedencia_institucional(:actor_id, :version_id, :url)).id"),
                {"actor_id": current_user.id, "version_id": version_id, "url": url},
            )
            db.commit()
            db.refresh(version)
        except DBAPIError as error:
            db.rollback()
            raise _confirmation_error(error) from error
    else:
        version.institutional_provenance = True
        version.institutional_source_url = url
        version.provenance_validated_by = current_user.id
        version.provenance_validated_at = utcnow()
        db.commit()
        db.refresh(version)
    return _build_version_response(db, syllabus, version, current_user.id)


def _normalize_vote_value(raw: str) -> str:
    return {"confirm": "confirma", "confirma": "confirma", "contest": "contesta", "contesta": "contesta"}[raw]


def _cast_votes(
    db: Session,
    *,
    syllabus: Syllabus,
    version: SyllabusVersion,
    targets: list[SyllabusCandidate],
    current_user_id: UUID,
    vote_value: str,
) -> None:
    if db.bind.dialect.name == "postgresql":
        try:
            for target in targets:
                db.execute(
                    text("select public.votar_avaliacao(:actor_id, :candidate_id, :val)"),
                    {"actor_id": current_user_id, "candidate_id": target.id, "val": vote_value},
                )
            db.commit()
        except DBAPIError as error:
            db.rollback()
            raise _confirmation_error(error) from error
    else:
        now = utcnow()
        for target in targets:
            existing = db.get(CandidateVote, (current_user_id, target.id))
            if existing is None:
                db.add(CandidateVote(user_id=current_user_id, candidate_id=target.id, value=vote_value, updated_at=now))
            elif existing.value != vote_value:
                existing.value = vote_value
                existing.updated_at = now
        db.commit()


@router.put(
    "/{syllabus_id}/versions/{version_id}/candidates/{candidate_id}/vote",
    response_model=CandidateVoteSummaryRead,
    summary="Registra ou atualiza o voto único do usuário sobre um candidato compartilhado",
)
def vote_syllabus_candidate(
    syllabus_id: UUID,
    version_id: UUID,
    candidate_id: UUID,
    payload: VoteVersionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CandidateVoteSummaryRead:
    syllabus, version = _get_syllabus_version(db, syllabus_id, version_id)
    if version.visibility != "compartilhada":
        raise HTTPException(status_code=404, detail="Candidato não disponível para voto.")
    if not _can_read_version(db, current_user.id, syllabus, version):
        raise HTTPException(status_code=403, detail="Siga a turma para votar.")

    candidate = db.scalar(
        select(SyllabusCandidate).where(
            SyllabusCandidate.id == candidate_id,
            SyllabusCandidate.syllabus_id == syllabus_id,
            SyllabusCandidate.version_id == version_id,
            SyllabusCandidate.status != "descartado",
        )
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidato não disponível para voto.")

    vote_value = _normalize_vote_value(payload.value)
    _cast_votes(
        db,
        syllabus=syllabus,
        version=version,
        targets=[candidate],
        current_user_id=current_user.id,
        vote_value=vote_value,
    )

    votes = db.scalars(select(CandidateVote).where(CandidateVote.candidate_id == candidate_id)).all()
    confirm_count = sum(1 for v in votes if v.value == "confirma")
    contest_count = sum(1 for v in votes if v.value == "contesta")
    return CandidateVoteSummaryRead(
        candidateId=candidate_id,
        versionId=version_id,
        confirmCount=confirm_count,
        contestCount=contest_count,
        divergent=contest_count > 0,
        myVote=vote_value,
    )


@router.put(
    "/{syllabus_id}/versions/{version_id}/vote",
    response_model=VoteVersionResponse,
    summary="Registra ou atualiza voto em uma versão compartilhada",
)
def vote_syllabus_version(
    syllabus_id: UUID,
    version_id: UUID,
    payload: VoteVersionRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VoteVersionResponse:
    syllabus, version = _get_syllabus_version(db, syllabus_id, version_id)
    if version.visibility != "compartilhada":
        raise HTTPException(status_code=404, detail="Versão compartilhada não encontrada.")
    if not _can_read_version(db, current_user.id, syllabus, version):
        raise HTTPException(status_code=403, detail="Siga a turma para votar nesta versão.")

    active_candidates = db.scalars(
        select(SyllabusCandidate)
        .where(SyllabusCandidate.version_id == version_id, SyllabusCandidate.status != "descartado")
        .order_by(SyllabusCandidate.order.asc().nulls_last(), SyllabusCandidate.id.asc())
    ).all()
    if payload.candidate_id is not None:
        targets = [c for c in active_candidates if c.id == payload.candidate_id]
        if not targets:
            raise HTTPException(status_code=404, detail="Avaliação não encontrada nesta versão.")
    else:
        targets = active_candidates
    if not targets:
        raise HTTPException(status_code=422, detail="Esta versão não possui avaliações para votar.")

    vote_value = _normalize_vote_value(payload.value)
    _cast_votes(
        db,
        syllabus=syllabus,
        version=version,
        targets=targets,
        current_user_id=current_user.id,
        vote_value=vote_value,
    )

    all_ids = [c.id for c in active_candidates]
    votes = db.scalars(select(CandidateVote).where(CandidateVote.candidate_id.in_(all_ids))).all()
    votes_by_candidate: dict[UUID, list[CandidateVote]] = {}
    for vote in votes:
        votes_by_candidate.setdefault(vote.candidate_id, []).append(vote)
    confirm_count, contest_count, my_vote = summarize_version_votes(all_ids, votes_by_candidate, current_user.id)
    return VoteVersionResponse(
        versionId=version_id,
        candidateId=payload.candidate_id,
        confirmCount=confirm_count,
        contestCount=contest_count,
        divergent=contest_count > 0,
        myVote=my_vote or vote_value,
    )


@router.get(
    "/{syllabus_id}/versions/{version_id}/votes",
    response_model=VersionVotesResponse,
    summary="Consulta o resumo de votos e divergências de uma versão",
)
def get_syllabus_version_votes(
    syllabus_id: UUID,
    version_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> VersionVotesResponse:
    syllabus, version = _get_syllabus_version(db, syllabus_id, version_id)
    if not _can_read_version(db, current_user.id, syllabus, version):
        raise HTTPException(status_code=403, detail="Sem acesso a esta versão.")

    if db.bind.dialect.name == "postgresql":
        try:
            rows = db.execute(
                text("select * from public.resumo_votos_versao(:actor_id, :version_id)"),
                {"actor_id": current_user.id, "version_id": version_id},
            ).mappings().all()
        except DBAPIError as error:
            db.rollback()
            raise _confirmation_error(error) from error
        items = [
            CandidateVoteSummaryRead(
                candidateId=r["avaliacao_id"],
                versionId=version_id,
                confirmCount=int(r["confirmam"] or 0),
                contestCount=int(r["contestam"] or 0),
                divergent=int(r["contestam"] or 0) > 0,
                myVote=r["meu_voto"],
            )
            for r in rows
        ]
        confirm_count = sum(item.confirm_count for item in items)
        contest_count = sum(item.contest_count for item in items)
        my_vote = next((item.my_vote for item in items if item.my_vote is not None), None)
        return VersionVotesResponse(
            versionId=version_id,
            confirmCount=confirm_count,
            contestCount=contest_count,
            divergent=contest_count > 0,
            myVote=my_vote,
            items=items,
        )

    candidates = db.scalars(
        select(SyllabusCandidate)
        .where(SyllabusCandidate.version_id == version_id, SyllabusCandidate.status != "descartado")
        .order_by(SyllabusCandidate.order.asc().nulls_last(), SyllabusCandidate.id.asc())
    ).all()
    all_ids = [c.id for c in candidates]
    votes = db.scalars(select(CandidateVote).where(CandidateVote.candidate_id.in_(all_ids))).all() if all_ids else []
    votes_by_candidate: dict[UUID, list[CandidateVote]] = {}
    for vote in votes:
        votes_by_candidate.setdefault(vote.candidate_id, []).append(vote)

    items = []
    for candidate in candidates:
        c_votes = votes_by_candidate.get(candidate.id, [])
        c_confirm = sum(1 for v in c_votes if v.value == "confirma")
        c_contest = sum(1 for v in c_votes if v.value == "contesta")
        c_my_vote = next((v.value for v in c_votes if v.user_id == current_user.id), None)
        items.append(
            CandidateVoteSummaryRead(
                candidateId=candidate.id,
                versionId=version_id,
                confirmCount=c_confirm,
                contestCount=c_contest,
                divergent=c_contest > 0,
                myVote=c_my_vote,
            )
        )
    confirm_count, contest_count, my_vote = summarize_version_votes(all_ids, votes_by_candidate, current_user.id)
    return VersionVotesResponse(
        versionId=version_id,
        confirmCount=confirm_count,
        contestCount=contest_count,
        divergent=contest_count > 0,
        myVote=my_vote,
        items=items,
    )


@router.delete(
    "/{syllabus_id}/versions/{version_id}/candidates/{candidate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Retira um evento/candidato de uma versão do plano",
)
def withdraw_version_candidate(
    syllabus_id: UUID,
    version_id: UUID,
    candidate_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    _, version = _get_syllabus_version(db, syllabus_id, version_id)
    if version.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Apenas o autor ou um administrador pode retirar este evento.")
    candidate = db.scalar(
        select(SyllabusCandidate).where(
            SyllabusCandidate.id == candidate_id,
            SyllabusCandidate.syllabus_id == syllabus_id,
            SyllabusCandidate.version_id == version_id,
        ).with_for_update()
    )
    if candidate is None:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada nesta versão.")
    candidate.status = "descartado"
    candidate.revisado_em = utcnow()
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


