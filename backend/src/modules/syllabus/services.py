import io
import logging
import os
import re
from uuid import UUID, uuid4

import pypdf
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.database.models import Syllabus
from src.services.storage import SupabaseStorageService

logger = logging.getLogger("agenda_unb.syllabus")

# Limite padrão de 10 MB (alinhado ao bucket privado do Supabase e Sprint 06 DoD)
MAX_FILE_SIZE_BYTES = int(
    os.getenv("MAX_UPLOAD_SIZE_BYTES", str(10 * 1024 * 1024))
)
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "10"))


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

    # 3. Leitura do conteúdo em memória e validação de tamanho de payload
    try:
        content = await file.read()
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

    # 5. Validação estrutural via leitor de PDF (pypdf)
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
    except Exception as exc:
        logger.warning("Falha ao analisar a estrutura do PDF: %s", exc)
        raise HTTPException(
            status_code=400,
            detail="Arquivo PDF corrompido ou malformado. Verifique o arquivo ou realize o cadastro manual.",
        ) from exc

    # 6. Verificação de proteção por senha / criptografia
    if reader.is_encrypted:
        raise HTTPException(
            status_code=400,
            detail="O arquivo PDF está protegido por senha. Envie uma versão sem proteção ou realize o cadastro manual.",
        )

    # 7. Verificação de quantidade de páginas
    num_pages = len(reader.pages)
    if num_pages == 0:
        raise HTTPException(
            status_code=400,
            detail="O arquivo PDF não possui páginas válidas.",
        )

    if num_pages > MAX_PDF_PAGES:
        raise HTTPException(
            status_code=400,
            detail=f"O arquivo PDF possui {num_pages} páginas, ultrapassando o limite máximo de {MAX_PDF_PAGES} páginas. Reduza o documento ou adicione os eventos manualmente.",
        )

    # 8. Verificação de texto selecionável
    has_text = False
    try:
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                has_text = True
                break
    except Exception as exc:
        logger.warning("Erro ao tentar extrair texto das páginas do PDF: %s", exc)

    if not has_text:
        raise HTTPException(
            status_code=400,
            detail="O arquivo PDF não possui texto selecionável legível (documento escaneado ou imagem). Envie um documento com texto selecionável ou cadastre os eventos manualmente.",
        )

    return content


def process_syllabus_upload(
    user_id: UUID,
    filename: str,
    content: bytes,
    db: Session,
    storage: SupabaseStorageService,
    disciplina: str | None = None,
    turma: str | None = None,
) -> Syllabus:
    """
    Coordena o upload físico para o Storage do Supabase e o registro
    transacional de rastreamento com status inicial 'processing'.
    Compensa a gravação no Storage caso a persistência no banco falhe.
    """
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
        professor_id=user_id,
        file_name=filename,
        file_path=full_storage_path,
        arquivo_url=full_storage_path,
        file_size=len(content),
        file_type="pdf",
        status="processing",
        extracted_events_count=0,
        error_message=None,
        disciplina=disciplina,
        turma=turma,
    )

    try:
        db.add(syllabus_record)
        db.commit()
        db.refresh(syllabus_record)
    except Exception as exc:
        db.rollback()
        logger.error("Falha ao registrar envio no banco de dados. Compensando arquivo no Storage: %s", exc)
        # Compensação: remove o arquivo físico já enviado
        storage.delete_file(storage_relative_path)
        raise HTTPException(
            status_code=503,
            detail="Falha ao registrar o envio do plano de ensino no banco de dados. Operação cancelada.",
        ) from exc

    return syllabus_record

