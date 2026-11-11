"""Preparação local, minimização e autorização de snapshots privados de texto."""
from uuid import UUID
import hashlib
import json
import logging
import multiprocessing
import os
import re
import time
from datetime import datetime, timezone

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update

from src.database.models import AssessmentCandidate, Syllabus, SyllabusVersion
from src.modules.syllabus.versions import private_version
from src.modules.syllabus.extraction import extract_pages
from src.modules.syllabus.processing_config import ProcessingConfig, ProcessingError

MAX_TEXT_BYTES = 40000


class ReviewPage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pagina: int | None = Field(default=None, ge=1, le=10, strict=True)
    texto: str = Field(max_length=MAX_TEXT_BYTES)


class TextInput(BaseModel):
    offering_id: UUID
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=MAX_TEXT_BYTES)
    disciplina: str | None = Field(default=None, max_length=200)
    turma: str | None = Field(default=None, max_length=100)


class ExtractionAuthorization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pages: list[ReviewPage] = Field(min_length=1, max_length=10)
    text_hash: str = Field(alias="textHash", pattern="^[a-f0-9]{64}$")
    authorize: bool = Field(strict=True)
    content_eligible: bool = Field(alias="contentEligible", strict=True)
    reprocess: bool = Field(default=False, strict=True)


class PreparationPreview(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    pages: list[ReviewPage]
    text_hash: str = Field(alias="textHash")
    authorization_required: bool = Field(alias="authorizationRequired")
    provider: str
    provider_available: bool = Field(alias="providerAvailable")
    max_text_bytes: int = Field(alias="maxTextBytes")
    warning: str
    preparation_duration_ms: int | None = Field(alias="preparationDurationMs")
    text_revision: int = Field(alias="textRevision")


def checked_pages(pages):
    values = [page.model_dump() if isinstance(page, ReviewPage) else ReviewPage.model_validate(page).model_dump() for page in pages]
    ids = [page["pagina"] for page in values]
    if not 1 <= len(values) <= 10 or len(set(ids)) != len(ids) or (None in ids and ids != [None]):
        raise HTTPException(422, "Referências de página inválidas.")
    if any("\x00" in page["texto"] for page in values):
        raise HTTPException(422, "O texto contém caracteres de controle inválidos.")
    try:
        size = sum(len(page["texto"].encode("utf-8")) for page in values)
    except UnicodeError:
        raise HTTPException(422, "O texto precisa ser UTF-8 válido.") from None
    if size > MAX_TEXT_BYTES:
        raise HTTPException(413, "O texto ultrapassa o limite de 40.000 bytes UTF-8.")
    if not any(page["texto"].strip() for page in values):
        raise HTTPException(422, "Informe um trecho com conteúdo para revisar.")
    return values


def text_hash(pages):
    snapshot = [{"pagina": page["pagina"], "texto": page["texto"]} for page in pages]
    return hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def minimize(text):
    text = re.sub(r"(?im)^(?:professor(?:a)?|docente|aluno(?:a)?|discente|nome|matr[ií]cula|cpf|nascimento)\s*[:=].*$", "[identificador removido]", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}", "[email removido]", text)
    text = re.sub(r"(?<!\d)(?:\d{3}[.]\d{3}[.]\d{3}-\d{2}|\d{9,11})(?!\d)", "[identificador removido]", text)
    text = re.sub(r"(?:\+55\s*)?\(?\d{2}\)?[ -]\d{4,5}-\d{4}", "[telefone removido]", text)
    return text


def _prepare_child(send, content):
    logging.disable(logging.CRITICAL)
    try:
        output = {"pages": [vars(page) for page in extract_pages(content, ProcessingConfig(max_text_bytes=MAX_TEXT_BYTES))]}
    except ProcessingError as error:
        output = {"error": error.code}
    except Exception:
        output = {"error": "pdf_invalido"}
    try:
        send.send_bytes(json.dumps(output, ensure_ascii=False).encode("utf-8"))
    finally:
        send.close()


def extract_pdf_isolated(content, timeout):
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_prepare_child, args=(send, content), daemon=True)
    try:
        deadline = time.monotonic() + timeout
        process.start()
        send.close()
        if not receive.poll(max(0, deadline-time.monotonic())):
            raise HTTPException(422, "A preparação do PDF excedeu o prazo. Use a organização manual.")
        output = json.loads(receive.recv_bytes(maxlength=512000))
        if "error" in output:
            raise HTTPException(400, "Não foi possível preparar o PDF. Use texto selecionável ou a organização manual.")
        return checked_pages([{"pagina": page["pagina"], "texto": minimize(page["texto"])} for page in output["pages"]])
    except (EOFError, OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, "A preparação do PDF está indisponível. Tente novamente ou organize manualmente.") from None
    finally:
        receive.close()
        send.close()
        if process.pid is not None:
            process.join(0.2)
            if process.is_alive():
                process.terminate()
                process.join(1)
            if process.is_alive():
                process.kill()
                process.join(1)
            if not process.is_alive():
                process.close()


def owned_plan(db, user_id, sid, *, lock=False):
    query = select(Syllabus).where(Syllabus.id == sid, Syllabus.user_id == user_id)
    plan = db.scalar(query.with_for_update() if lock else query)
    if plan is None:
        raise HTTPException(404, "Plano de ensino não encontrado.")
    return plan


def preview(plan):
    pages = plan.approved_pages or plan.prepared_pages
    if not pages:
        raise HTTPException(409, "Este plano precisa ser preparado novamente antes de enviar texto à IA.")
    return {"id": str(plan.id), "pages": pages, "textHash": text_hash(pages),
            "authorizationRequired": plan.authorized_at is None,
            "provider": "Google Gemini API", "providerAvailable": os.getenv("SYLLABUS_PROVIDER_TERMS_READY", "false").lower() == "true", "maxTextBytes": MAX_TEXT_BYTES,
            "warning": "A remoção automática de identificadores é limitada. Revise o texto exato. Não envie conteúdo pessoal, sensível ou confidencial. A autorização não substitui os termos do provedor.",
            "preparationDurationMs": plan.preparation_duration_ms,
            "textRevision": plan.text_revision}


def authorize(db, plan, payload, config):
    if not payload.authorize or not payload.content_eligible:
        raise HTTPException(422, "Autorize o envio do texto revisado e confirme que o conteúdo atende às regras do provedor.")
    pages = checked_pages(payload.pages)
    allowed = {page["pagina"] for page in plan.prepared_pages or []}
    if any(page["pagina"] not in allowed for page in pages):
        raise HTTPException(422, "A referência de página não pertence ao texto preparado.")
    digest = text_hash(pages)
    if digest != payload.text_hash:
        raise HTTPException(409, "O texto aprovado não corresponde ao hash informado. Revise novamente.")
    if any(minimize(page["texto"]) != page["texto"] for page in pages):
        raise HTTPException(422, "Remova os identificadores detectados antes de autorizar o envio.")
    if not config.provider_terms_ready:
        raise HTTPException(503, "A análise com Gemini ainda não está disponível. Use a organização manual.")
    if plan.approved_hash == digest and not payload.reprocess:
        return plan
    if plan.status == "processando" or (plan.authorized_at is not None and plan.status == "pendente"):
        raise HTTPException(409, "Aguarde a execução atual antes de autorizar outro texto.")
    if plan.authorized_at is not None and not payload.reprocess:
        raise HTTPException(409, "Confirme explicitamente o reprocessamento deste plano.")
    if plan.execucao_atual >= config.max_attempts or plan.cost_reserved_usd + config.attempt_reservation > config.max_file_cost_usd:
        raise HTTPException(409, "O plano atingiu o limite acumulado de tentativas ou custo.")
    now = datetime.now(timezone.utc)
    db.execute(update(AssessmentCandidate).where(AssessmentCandidate.plano_id == plan.id,
        AssessmentCandidate.status == "pendente",
        AssessmentCandidate.version_id.in_(select(SyllabusVersion.id).where(
            SyllabusVersion.syllabus_id == plan.id, SyllabusVersion.visibility == "privada"
        ))).values(status="descartado", revisado_em=now))
    version = private_version(db, plan, new_analysis=plan.authorized_at is not None)
    plan.approved_version_id = version.id
    plan.prepared_pages = pages  # Não conservar a versão anterior às correções do dono.
    plan.approved_pages = pages
    plan.approved_hash = digest
    plan.authorized_at = now
    plan.queued_at = now
    plan.text_revision += 1
    plan.status = "pendente"
    plan.processado_em = None
    plan.erro_codigo = None
    plan.error_message = None
    plan.extracted_events_count = 0
    plan.processing_token = None
    plan.next_attempt_at = None
    db.commit()
    db.refresh(plan)
    return plan
