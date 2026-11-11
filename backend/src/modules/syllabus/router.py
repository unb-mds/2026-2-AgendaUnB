import time
import hashlib
import json
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool

from src.database.connection import get_db
from src.database.models import (
    ImportItem,
    ImportOperation,
    PersonalEvent,
    Syllabus,
    SyllabusCandidate,
    SyllabusVersion,
)
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.events.router import _category_id, _personal_read
from src.modules.syllabus.schemas import (
    ConfirmSyllabusRequest,
    ConfirmSyllabusResponse,
    ConfirmItemResult,
    SyllabusCandidateRead,
    SyllabusDetailResponse,
    SyllabusListItem,
    SyllabusListResponse,
    SyllabusUploadResponse,
)
from src.modules.syllabus.services import process_syllabus_upload, validate_pdf_file
from src.modules.syllabus.timing import duration_ms
from src.modules.syllabus.processing_config import ProcessingConfig
from src.modules.syllabus.preparation import (
    TextInput, ExtractionAuthorization, PreparationPreview, checked_pages, minimize, extract_pdf_isolated,
    owned_plan, preview, authorize,
)
from src.modules.syllabus.services import UPLOAD_VALIDATION_TIMEOUT_SECONDS

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
        if candidate.starts_at is not None:
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


def _confirm_sqlite(syllabus_id: UUID, payload: ConfirmSyllabusRequest, user_id: UUID,
                    idempotency_key: str, db: Session) -> ConfirmSyllabusResponse:
    """ORM equivalente usado pela suíte SQLite; produção usa a função PostgreSQL."""
    syllabus = db.get(Syllabus, syllabus_id)
    if syllabus is None or syllabus.user_id != user_id:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
    if syllabus.status not in {"completed", "concluido"}:
        raise HTTPException(status_code=409, detail="O plano ainda não está pronto para confirmação.")

    items = _confirmation_payload(payload)
    canonical = json.dumps({"version": str(syllabus.approved_version_id or ""), "items": items},
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

    requested_ids = [item.candidate_id for item in payload.candidates]
    query = select(SyllabusCandidate).where(
        SyllabusCandidate.syllabus_id == syllabus_id,
        SyllabusCandidate.id.in_(requested_ids),
    )
    if syllabus.approved_version_id is not None:
        query = query.where(SyllabusCandidate.version_id == syllabus.approved_version_id)
    candidates = db.scalars(query).all()
    by_id = {candidate.id: candidate for candidate in candidates}
    if len(by_id) != len(requested_ids):
        raise HTTPException(status_code=422, detail="Um ou mais candidatos não pertencem a este plano.")

    prepared = []
    for reviewed in payload.candidates:
        candidate = by_id[reviewed.candidate_id]
        if candidate.status == "descartado":
            raise HTTPException(status_code=422, detail="Um candidato descartado não pode ser confirmado.")
        title = (reviewed.title or candidate.title).strip()
        starts_at = reviewed.starts_at or candidate.starts_at
        if len(title) < 3:
            raise HTTPException(status_code=422, detail="O título revisado deve ter ao menos 3 caracteres.")
        if starts_at is None or starts_at.tzinfo is None or starts_at.utcoffset() is None:
            raise HTTPException(status_code=422, detail="Corrija a data ambígua antes de confirmar o candidato.")
        prepared.append((reviewed, candidate, title, starts_at))

    operation = ImportOperation(
        user_id=user_id,
        idempotency_key=idempotency_key,
        version_id=syllabus.approved_version_id,
        content_hash=content_hash,
    )
    db.add(operation)
    db.flush()
    rows = []
    for reviewed, candidate, title, starts_at in prepared:
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
                category_id=_category_id(db, reviewed.category),
                origin_syllabus_id=syllabus.id,
                origin_candidate_id=candidate.id,
                origin_version_id=candidate.version_id,
                origin_page=candidate.source_page,
                origin_excerpt=candidate.source_excerpt,
            )
            db.add(event)
            db.flush()
        else:
            if reviewed.title is not None:
                event.title = title
            if reviewed.starts_at is not None:
                event.starts_at = starts_at
            if reviewed.description is not None:
                event.description = reviewed.description
            if reviewed.category is not None:
                event.category_id = _category_id(db, reviewed.category)
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
    db.commit()
    return _confirmation_response(db, syllabus_id, user_id, operation.id, rows, payload.candidates, repeated=False)


def _candidate_read(
    candidate: SyllabusCandidate,
    *,
    status_override: str | None = None,
    kind_override: str | None = None,
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
    )


@router.get("", response_model=SyllabusListResponse, summary="Lista planos do usuário")
def list_syllabi(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyllabusListResponse:
    owned = Syllabus.user_id == current_user.id
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
        db=db, disciplina=disciplina, turma=turma, ano=ano, semestre=semestre,
    )

    return SyllabusUploadResponse.model_validate(syllabus)


@router.post("/text", response_model=SyllabusUploadResponse, status_code=202)
def prepare_syllabus_text(payload: TextInput, current_user: CurrentUser = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    started = time.monotonic()
    pages = checked_pages([{"pagina": None, "texto": payload.text}])
    pages = checked_pages([{"pagina": None, "texto": minimize(pages[0]["texto"])}])
    plan = process_syllabus_upload(user_id=current_user.id, filename="texto-revisado.txt",
        file_size=len(payload.text.encode("utf-8")), pages=pages, file_type="text", db=db,
        preparation_duration_ms=round((time.monotonic()-started)*1000),
        disciplina=payload.disciplina, turma=payload.turma)
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
    if version_id is not None and db.bind.dialect.name == "postgresql":
        try:
            can_read = db.scalar(text(
                "select public.ator_pode_ler_versao(:actor_id, :version_id)"
            ), {"actor_id": current_user.id, "version_id": version_id})
        except DBAPIError as error:
            db.rollback()
            raise HTTPException(status_code=503, detail="Não foi possível verificar o acesso ao plano.") from error
        if not can_read:
            raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
    elif not is_owner:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")

    candidate_query = select(SyllabusCandidate).where(SyllabusCandidate.syllabus_id == syllabus.id)
    if version_id is not None:
        candidate_query = candidate_query.where(SyllabusCandidate.version_id == version_id)
    candidates = db.scalars(
        candidate_query.order_by(SyllabusCandidate.source_page.asc(), SyllabusCandidate.id.asc())
    ).all()
    own_imports: dict[UUID, tuple[str, UUID | None, str | None]] = {}
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

    return SyllabusDetailResponse(
        id=syllabus.id,
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
        reviewDurationMs=duration_ms(syllabus.created_at, syllabus.authorized_at) if is_owner else None,
        disciplina=syllabus.disciplina,
        turma=syllabus.turma,
        ano=syllabus.ano,
        semestre=syllabus.semestre,
        createdAt=syllabus.created_at,
        candidates=[
            _candidate_read(
                candidate,
                status_override=("confirmado" if own_imports.get(candidate.id, (None, None, None))[1] is not None else "pendente")
                if not is_owner else None,
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

    is_owner = syllabus.user_id == current_user.id
    version_id = syllabus.approved_version_id
    if version_id is None:
        version_id = db.scalar(select(SyllabusCandidate.version_id).where(
            SyllabusCandidate.syllabus_id == syllabus_id,
            SyllabusCandidate.id == payload.candidates[0].candidate_id,
        ))

    # O backend ignora RLS. Portanto, autorização sobre a versão deve ser
    # checada antes de expor estado do plano (por exemplo, que ainda processa).
    if db.bind.dialect.name == "postgresql" and version_id is not None:
        try:
            can_read = db.scalar(text(
                "select public.ator_pode_ler_versao(:actor_id, :version_id)"
            ), {"actor_id": current_user.id, "version_id": version_id})
        except DBAPIError as error:
            db.rollback()
            raise HTTPException(status_code=503, detail="Não foi possível verificar o acesso ao plano.") from error
        if not can_read:
            raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
    elif not is_owner:
        raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")

    if syllabus.status not in {"completed", "concluido"}:
        raise HTTPException(status_code=409, detail="O plano ainda não está pronto para confirmação.")

    if db.bind.dialect.name != "postgresql":
        return _confirm_sqlite(syllabus_id, payload, current_user.id, idempotency_key, db)
    if version_id is None:
        raise HTTPException(status_code=409, detail="O plano não possui uma versão aprovada para confirmação.")

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
            detail="O descarte individual de candidatos compartilhados ainda não está disponível.",
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
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

