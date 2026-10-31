from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import PersonalEvent, Syllabus, SyllabusCandidate
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.events.router import _category_id, _personal_read
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
from src.services.storage import SupabaseStorageService, get_storage_service

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
        items=[
            SyllabusListItem(
                id=record.id,
                fileName=record.file_name,
                fileSize=record.file_size,
                status=record.status,
                extractedEventsCount=record.extracted_events_count,
                errorMessage=record.error_message,
                disciplina=record.disciplina,
                turma=record.turma,
                createdAt=record.created_at,
            )
            for record in records
        ],
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
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: SupabaseStorageService = Depends(get_storage_service),
) -> SyllabusUploadResponse:
    """
    Recebe o arquivo PDF do plano de ensino, realiza validações estruturais rigorosas
    (extensão .pdf, MIME type, assinatura de bytes, integridade, texto legível e tamanho máximo)
    e envia o arquivo para o bucket privado do Supabase Storage.

    Gera um registro na tabela de rastreamento com status inicial 'pendente'
    e retorna HTTP 202 Accepted.
    """
    content = await validate_pdf_file(file)

    syllabus = process_syllabus_upload(
        user_id=current_user.id,
        filename=file.filename or "syllabus.pdf",
        content=content,
        db=db,
        storage=storage,
        disciplina=disciplina,
        turma=turma,
    )

    return SyllabusUploadResponse(
        id=syllabus.id,
        userId=syllabus.user_id,
        fileName=syllabus.file_name,
        filePath=syllabus.file_path,
        fileSize=syllabus.file_size,
        fileType=syllabus.file_type,
        status=syllabus.status,
        createdAt=syllabus.created_at,
        message="Plano de ensino recebido com sucesso e direcionado para processamento.",
    )


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
        .order_by(SyllabusCandidate.source_page.asc(), SyllabusCandidate.id.asc())
    ).all()

    return SyllabusDetailResponse(
        id=syllabus.id,
        userId=syllabus.user_id,
        fileName=syllabus.file_name,
        filePath=syllabus.file_path,
        fileSize=syllabus.file_size,
        fileType=syllabus.file_type,
        status=syllabus.status,
        extractedEventsCount=syllabus.extracted_events_count,
        errorMessage=syllabus.error_message,
        disciplina=syllabus.disciplina,
        turma=syllabus.turma,
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

