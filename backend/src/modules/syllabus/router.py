from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import Syllabus
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.syllabus.schemas import SyllabusDetailResponse, SyllabusListResponse, SyllabusUploadResponse
from src.modules.syllabus.services import process_syllabus_upload, validate_pdf_file
from src.services.storage import SupabaseStorageService, get_storage_service

router = APIRouter(prefix="/syllabus", tags=["syllabus"])


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

    return SyllabusUploadResponse.model_validate(syllabus)


@router.get("", response_model=SyllabusListResponse, summary="Histórico dos próprios planos de ensino")
def list_syllabuses(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SyllabusListResponse:
    ownership = Syllabus.user_id == current_user.id
    total = db.scalar(select(func.count()).select_from(Syllabus).where(ownership))
    plans = db.scalars(
        select(Syllabus)
        .where(ownership)
        .order_by(Syllabus.created_at.desc(), Syllabus.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    return SyllabusListResponse(
        items=[SyllabusDetailResponse.model_validate(plan) for plan in plans],
        total=total,
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

    return SyllabusDetailResponse.model_validate(syllabus)
