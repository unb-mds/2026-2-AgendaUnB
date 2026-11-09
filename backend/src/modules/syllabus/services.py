import logging
import math
import os
import re
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select, text as sql_text
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from src.database.models import Syllabus
from src.modules.syllabus.upload_validation import PdfValidationError, validate_pdf_structure
from src.services.storage import SupabaseStorageService

logger = logging.getLogger("agenda_unb.syllabus")

# Limite padrão de 10 MB (alinhado ao bucket privado do Supabase e Sprint 06 DoD)
MAX_FILE_SIZE_BYTES = int(
    os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024))
)
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "10"))
UPLOAD_VALIDATION_TIMEOUT_SECONDS = float(os.getenv("SYLLABUS_UPLOAD_VALIDATION_TIMEOUT_SECONDS", "8"))
if not math.isfinite(UPLOAD_VALIDATION_TIMEOUT_SECONDS) or not 0 < UPLOAD_VALIDATION_TIMEOUT_SECONDS <= 30:
    raise ValueError("SYLLABUS_UPLOAD_VALIDATION_TIMEOUT_SECONDS deve estar entre 0 e 30 segundos")

PDF_VALIDATION_MESSAGES = {
    "malformed": "Arquivo PDF corrompido ou malformado. Verifique o arquivo ou realize o cadastro manual.",
    "encrypted": "O arquivo PDF está protegido por senha. Envie uma versão sem proteção ou realize o cadastro manual.",
    "empty": "O arquivo PDF não possui páginas válidas.",
    "pages": f"O arquivo PDF está ultrapassando o limite máximo de {MAX_PDF_PAGES} páginas. Reduza o documento ou adicione os eventos manualmente.",
    "no_text": "O arquivo PDF não possui texto selecionável legível (documento escaneado ou imagem). Envie um documento com texto selecionável ou cadastre os eventos manualmente.",
    "timeout": "O tempo limite de validação do PDF foi excedido. Reduza o documento ou realize o cadastro manual.",
    "unavailable": "A validação do PDF está indisponível no momento. Tente novamente mais tarde.",
}


def sanitize_filename(filename: str) -> str:
    """Higieniza o nome original do arquivo para uso seguro no caminho de armazenamento."""
    clean = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)
    return clean or "syllabus.pdf"


async def validate_pdf_file(file: UploadFile) -> bytes:
    """
    Executa validação rigorosa de extensão, MIME Type, tamanho de payload,
    assinatura binária e integridade estrutural do arquivo PDF.
    """
    filename = file.filename or ""

    # 1. Validação estrita de extensão
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Extensão de arquivo inválida. Apenas arquivos com extensão .pdf são aceitos.",
        )

    # 2. Validação estrita de MIME type informado
    if file.content_type not in ("application/pdf", "application/x-pdf"):
        raise HTTPException(
            status_code=400,
            detail="MIME Type inválido. O arquivo enviado deve ser do tipo application/pdf.",
        )

    # 3. Leitura limitada antes da validação de tamanho de payload
    try:
        content = await file.read(MAX_FILE_SIZE_BYTES + 1)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível ler o arquivo enviado.",
        ) from exc

    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="O arquivo enviado está vazio.",
        )

    if len(content) > MAX_FILE_SIZE_BYTES:
        max_mb = MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"O tamanho do arquivo excede o limite máximo permitido de {max_mb}MB.",
        )

    # 4. Validação da assinatura mágica do arquivo (%PDF-)
    if not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Assinatura de arquivo inválida. O arquivo enviado não é um PDF legítimo.",
        )

    # Parser e extração em processo com prazo; a espera não bloqueia o event loop.
    try:
        await run_in_threadpool(
            validate_pdf_structure, content, MAX_PDF_PAGES, UPLOAD_VALIDATION_TIMEOUT_SECONDS
        )
    except PdfValidationError as exc:
        status_code = 422 if exc.code == "timeout" else 503 if exc.code == "unavailable" else 400
        raise HTTPException(status_code=status_code, detail=PDF_VALIDATION_MESSAGES[exc.code]) from None

    return content


def process_syllabus_upload(
    user_id: UUID,
    filename: str,
    content: bytes,
    db: Session,
    storage: SupabaseStorageService,
    disciplina: str | None = None,
    turma: str | None = None,
    ano: int | None = None,
    semestre: int | None = None,
) -> Syllabus:
    """
    Coordena o upload físico para o Storage do Supabase e o registro
    transacional de rastreamento com status inicial 'pendente'.
    Compensa a gravação no Storage caso a persistência no banco falhe.
    """
    # Serialize uploads for this user across API workers before counting the
    # rolling window. The lock lasts until the plan and its file are committed.
    if db.bind.dialect.name == "postgresql":
        db.execute(sql_text("SELECT pg_advisory_xact_lock(hashtextextended(:user_id, 0))"),
                   {"user_id": str(user_id)})
    cutoff = datetime.now(timezone.utc) - timedelta(days=5)
    recent_uploads = db.scalar(
        select(func.count()).select_from(Syllabus).where(
            Syllabus.user_id == user_id, Syllabus.created_at >= cutoff
        )
    )
    if recent_uploads >= 10:
        raise HTTPException(status_code=429, detail="Limite de 10 planos enviados em 5 dias. Tente novamente mais tarde.")

    syllabus_id = uuid4()
    safe_name = sanitize_filename(filename)

    # Convenção de caminho no bucket privado: syllabus_files/<user_id>/<syllabus_id>_<nome>.pdf
    storage_relative_path = f"{user_id}/{syllabus_id}_{safe_name}"

    # Upload físico para o Supabase Storage
    full_storage_path = storage.upload_file(
        path=storage_relative_path,
        content=content,
        content_type="application/pdf",
    )

    syllabus_record = Syllabus(
        id=syllabus_id,
        user_id=user_id,
        file_name=filename,
        file_path=full_storage_path,
        arquivo_url=full_storage_path,
        file_size=len(content),
        file_type="pdf",
        status="pendente",
        extracted_events_count=0,
        error_message=None,
        disciplina=disciplina,
        turma=turma,
        ano=ano,
        semestre=semestre,
    )

    try:
        db.add(syllabus_record)
        db.commit()
        db.refresh(syllabus_record)
    except Exception as exc:
        db.rollback()
        logger.error("Falha ao registrar envio; compensando arquivo no Storage")
        # Compensação: remove o arquivo físico já enviado
        storage.delete_file(storage_relative_path)
        raise HTTPException(
            status_code=503,
            detail="Falha ao registrar o envio do plano de ensino no banco de dados. Operação cancelada.",
        ) from exc

    return syllabus_record

