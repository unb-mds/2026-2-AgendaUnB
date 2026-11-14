import time
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload
from starlette.concurrency import run_in_threadpool

from src.database.connection import get_db
from src.database.models import PersonalEvent, Syllabus, SyllabusCandidate
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.events.router import _category_id, _personal_read
from src.modules.classes.services import followed_available_offering
from src.modules.syllabus.schemas import (
    ConfirmSyllabusRequest,
    ConfirmSyllabusResponse,
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


def _candidate_read(candidate: SyllabusCandidate) -> SyllabusCandidateRead:
    return SyllabusCandidateRead(
        id=candidate.id,
        title=candidate.title,
        type=candidate.kind,
        startsAt=candidate.starts_at,
        ambiguous=candidate.ambiguous,
        sourcePage=candidate.source_page,
        sourceExcerpt=candidate.source_excerpt,
        status=candidate.status,
        suggestedDate=candidate.data_sugerida,
        suggestedTime=candidate.hora_sugerida,
        ambiguousFields=candidate.campos_ambiguos or [],
        versionId=candidate.version_id,
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
    pages = checked_pages([{"pagina": None, "texto": minimize(pages[0]["texto"])}])
    plan = process_syllabus_upload(user_id=current_user.id, filename="texto-revisado.txt",
        file_size=len(payload.text.encode("utf-8")), pages=pages, file_type="text", db=db,
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
    """
    Consulta o status de processamento e dados do plano de ensino enviado.
    Apenas o próprio usuário que realizou o upload tem permissão para consultar.
    """
    syllabus = db.scalar(
        select(Syllabus).where(
            Syllabus.id == syllabus_id,
            Syllabus.user_id == current_user.id,
        )
    )

    if not syllabus:
        raise HTTPException(
            status_code=404,
            detail="Plano de ensino não encontrado.",
        )

    candidates = db.scalars(
        select(SyllabusCandidate)
        .where(SyllabusCandidate.syllabus_id == syllabus.id)
        .where(SyllabusCandidate.version_id == syllabus.approved_version_id if syllabus.approved_version_id else True)
        .order_by(SyllabusCandidate.source_page.asc(), SyllabusCandidate.id.asc())
    ).all()

    return SyllabusDetailResponse(
        id=syllabus.id,
        offeringId=syllabus.offering_id,
        userId=syllabus.user_id,
        fileName=syllabus.file_name,
        filePath=syllabus.file_path,
        fileSize=syllabus.file_size,
        fileType=syllabus.file_type,
        status=syllabus.status,
        extractedEventsCount=syllabus.extracted_events_count,
        errorMessage=syllabus.error_message,
        errorCode=syllabus.erro_codigo,
        pageCount=syllabus.paginas,
        attempts=syllabus.execucao_atual,
        processingStartedAt=syllabus.processamento_iniciado_em,
        processedAt=syllabus.processado_em,
        processingDurationMs=syllabus.processing_duration_ms,
        totalDurationMs=duration_ms(syllabus.queued_at or syllabus.created_at, syllabus.processado_em),
        authorizationRequired=syllabus.authorization_required,
        preparedTextAvailable=bool(syllabus.prepared_pages),
        preparationDurationMs=syllabus.preparation_duration_ms,
        reviewDurationMs=duration_ms(syllabus.created_at, syllabus.authorized_at),
        disciplina=syllabus.disciplina,
        turma=syllabus.turma,
        ano=syllabus.ano,
        semestre=syllabus.semestre,
        createdAt=syllabus.created_at,
        candidates=[_candidate_read(candidate) for candidate in candidates],
    )


@router.post(
    "/{syllabus_id}/confirm",
    response_model=ConfirmSyllabusResponse,
    summary="Confirma candidatos revisados na agenda pessoal",
)
def confirm_syllabus_candidates(
    syllabus_id: UUID,
    payload: ConfirmSyllabusRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConfirmSyllabusResponse:
    requested_ids = [item.candidate_id for item in payload.candidates]

    # Lock the owning plan on PostgreSQL so concurrent confirmations serialize.
    # The unique index on eventos_pessoais.origem_avaliacao_id is the final guard.
    for attempt in range(2):
        syllabus = db.scalar(
            select(Syllabus)
            .where(Syllabus.id == syllabus_id, Syllabus.user_id == current_user.id)
            .with_for_update()
        )
        if syllabus is None:
            raise HTTPException(status_code=404, detail="Plano de ensino não encontrado.")
        if syllabus.status not in {"completed", "concluido"}:
            raise HTTPException(
                status_code=409,
                detail="A confirmação estará disponível quando o processamento for concluído.",
            )

        candidates = db.scalars(
            select(SyllabusCandidate).where(
                SyllabusCandidate.syllabus_id == syllabus.id,
                SyllabusCandidate.id.in_(requested_ids),
                SyllabusCandidate.version_id == syllabus.approved_version_id if syllabus.approved_version_id else True,
            )
        ).all()
        by_id = {candidate.id: candidate for candidate in candidates}
        if len(by_id) != len(requested_ids):
            raise HTTPException(
                status_code=422,
                detail="Um ou mais candidatos não pertencem a este plano.",
            )

        existing = db.scalars(
            select(PersonalEvent)
            .where(
                PersonalEvent.user_id == current_user.id,
                PersonalEvent.origin_candidate_id.in_(requested_ids),
            )
            .options(joinedload(PersonalEvent.campus), joinedload(PersonalEvent.category))
        ).all()
        existing_by_candidate = {event.origin_candidate_id: event for event in existing}

        new_events: list[PersonalEvent] = []
        for reviewed in payload.candidates:
            candidate = by_id[reviewed.candidate_id]
            if candidate.status == "descartado":
                raise HTTPException(
                    status_code=422,
                    detail="Um candidato descartado não pode ser confirmado.",
                )
            if candidate.id in existing_by_candidate:
                continue
            if candidate.status == "confirmado":
                continue  # Evento removido não reaparece por retry da confirmação.

            title = reviewed.title or candidate.title
            starts_at = reviewed.starts_at or candidate.starts_at
            if len(title.strip()) < 3:
                raise HTTPException(status_code=422, detail="O título revisado deve ter ao menos 3 caracteres.")
            if starts_at is None or starts_at.tzinfo is None or starts_at.utcoffset() is None:
                raise HTTPException(
                    status_code=422,
                    detail="Informe data e hora com fuso horário para cada candidato selecionado.",
                )

            event = PersonalEvent(
                user_id=current_user.id,
                title=title.strip(),
                description=reviewed.description or candidate.source_excerpt,
                starts_at=starts_at,
                category_id=_category_id(db, reviewed.category),
                origin_syllabus_id=syllabus.id,
                origin_candidate_id=candidate.id,
                origin_version_id=candidate.version_id,
                origin_page=candidate.source_page,
                origin_excerpt=candidate.source_excerpt,
            )
            new_events.append(event)
            candidate.status = "confirmado"

        db.add_all(new_events)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if attempt == 0:
                continue
            raise HTTPException(
                status_code=409,
                detail="A confirmação ocorreu em paralelo. Recarregue o plano e tente novamente.",
            )
        break

    confirmed = db.scalars(
        select(PersonalEvent)
        .where(
            PersonalEvent.user_id == current_user.id,
            PersonalEvent.origin_candidate_id.in_(requested_ids),
        )
        .options(joinedload(PersonalEvent.campus), joinedload(PersonalEvent.category))
        .order_by(PersonalEvent.starts_at.asc(), PersonalEvent.id.asc())
    ).all()
    return ConfirmSyllabusResponse(
        syllabusId=syllabus_id,
        events=[_personal_read(event) for event in confirmed],
    )

