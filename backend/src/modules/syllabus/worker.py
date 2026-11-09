"""Fila SQL durável. Rodar como processo independente da API, nunca BackgroundTasks."""
import argparse
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import or_, select, update

from src.database.connection import SessionLocal
from src.database.models import AssessmentCandidate, Syllabus
from src.modules.syllabus.extraction import VERSION
from src.modules.syllabus.gemini import GeminiProvider
from src.modules.syllabus.processing_config import ERROR_MESSAGES, ProcessingConfig, ProcessingError
from src.modules.syllabus.processing_task import run_isolated
from src.services.storage import SupabaseStorageService

logger = logging.getLogger("agenda_unb.syllabus.worker")


def utcnow():
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Lease:
    id: UUID
    token: UUID
    execution: int
    user_id: UUID
    file_path: str
    terminal: bool = False


class SyllabusWorker:
    def __init__(self, session_factory, storage, provider, config: ProcessingConfig, *, runner=run_isolated):
        self.sessions = session_factory
        self.storage = storage
        self.provider = provider
        self.config = config
        self.runner = runner

    def claim(self) -> Lease | None:
        now = utcnow()
        ready = or_(
            (Syllabus.status == "pendente") & or_(Syllabus.next_attempt_at.is_(None), Syllabus.next_attempt_at <= now),
            (Syllabus.status == "processando") &
            (Syllabus.processamento_iniciado_em < now - timedelta(seconds=self.config.lease_seconds)),
        )
        with self.sessions() as db:
            job = db.scalar(select(Syllabus).where(Syllabus.tipo == "particular", ready)
                            .order_by(Syllabus.created_at, Syllabus.id).with_for_update(skip_locked=True).limit(1))
            if job is None:
                return None
            token = uuid4()
            attempt = job.execucao_atual + 1
            exhausted = (attempt > self.config.max_attempts or
                         job.cost_reserved_usd + self.config.attempt_reservation > self.config.max_file_cost_usd)
            # CAS também protege o caminho SQLite usado nos testes. PostgreSQL
            # usa SKIP LOCKED para permitir múltiplos processos independentes.
            condition = (Syllabus.id == job.id, Syllabus.execucao_atual == job.execucao_atual,
                         Syllabus.status == job.status, Syllabus.processing_token == job.processing_token)
            if exhausted:
                values = dict(status="falha", erro_codigo="falha_ia", error_message=ERROR_MESSAGES["falha_ia"],
                              processado_em=now, processing_token=None, next_attempt_at=None)
            else:
                values = dict(status="processando", execucao_atual=attempt, processing_token=token,
                              processamento_iniciado_em=now, processado_em=None, erro_codigo=None,
                              error_message=None, next_attempt_at=None, provedor_ia="google",
                              modelo_ia=self.config.model, versao_processamento=VERSION,
                              cost_reserved_usd=job.cost_reserved_usd + self.config.attempt_reservation)
            lease = Lease(job.id, token, attempt, job.user_id, job.file_path, terminal=exhausted)
            changed = db.execute(update(Syllabus).where(*condition).values(**values),
                                 execution_options={"synchronize_session": False}).rowcount
            db.commit()
            return lease if changed == 1 else None

    def fail(self, lease: Lease, error: ProcessingError, duration_ms: int):
        retry = error.retryable and lease.execution < self.config.max_attempts
        with self.sessions() as db:
            db.execute(update(Syllabus).where(Syllabus.id == lease.id, Syllabus.processing_token == lease.token,
                                             Syllabus.status == "processando").values(
                status="pendente" if retry else "falha", processing_token=None,
                next_attempt_at=utcnow() + timedelta(seconds=self.config.retry_delay_seconds) if retry else None,
                erro_codigo=None if retry else error.code,
                error_message=None if retry else ERROR_MESSAGES[error.code],
                processado_em=None if retry else utcnow(), processing_duration_ms=duration_ms,
            ))
            db.commit()
        logger.info("syllabus_attempt execution=%d code=%s retry=%s duration_ms=%d",
                    lease.execution, error.code, retry, duration_ms)

    def run_once(self) -> bool:
        lease = self.claim()
        if lease is None:
            return False
        if lease.terminal:
            return True
        started = time.monotonic()
        try:
            prefix = f"syllabus_files/{lease.user_id}/"
            if not lease.file_path.startswith(prefix):
                raise ProcessingError("pdf_invalido")
            relative = lease.file_path.removeprefix("syllabus_files/")
            filename = relative.split("/")[1:]
            if len(filename) != 1 or not re.fullmatch(r"[A-Za-z0-9_.-]+\.pdf", filename[0], flags=re.IGNORECASE):
                raise ProcessingError("pdf_invalido")
            document = self.runner(relative, self.storage, self.provider, self.config)
            result = document.extraction
            with self.sessions() as db:
                duration = round((time.monotonic() - started) * 1000)
                changed = db.execute(update(Syllabus).where(
                    Syllabus.id == lease.id, Syllabus.status == "processando", Syllabus.processing_token == lease.token,
                ).values(status="concluido", processing_token=None, processado_em=utcnow(),
                         paginas=document.page_count, extracted_events_count=len(result.candidates),
                         processing_duration_ms=duration), execution_options={"synchronize_session": False}).rowcount
                if changed != 1:
                    db.rollback()  # Um worker com lease mais novo já assumiu.
                    return True
                for order, candidate in enumerate(result.candidates):
                    db.add(AssessmentCandidate(
                        plano_id=lease.id, execucao=lease.execution, ordem=order,
                        **candidate.model_dump(), provedor_ia="google", modelo_ia=self.config.model,
                        versao_processamento=VERSION, status="pendente",
                    ))
                db.commit()  # Candidatos + estado final são uma única transação.
            logger.info("syllabus_completed candidates=%d unsupported_dates=%d duration_ms=%d over_target=%s",
                        len(result.candidates), result.unsupported_dates, duration, duration >= 20000)
        except ProcessingError as error:
            self.fail(lease, error, round((time.monotonic() - started) * 1000))
        except Exception:
            # Nunca registrar exceções de SQL (parâmetros), PDF, Storage ou IA.
            self.fail(lease, ProcessingError("erro_interno", retryable=True),
                      round((time.monotonic() - started) * 1000))
        return True


def main():
    parser = argparse.ArgumentParser(description="Worker privado de planos de ensino")
    parser.add_argument("--once", action="store_true", help="Processa no máximo um item e sai")
    args = parser.parse_args()
    if os.getenv("SYLLABUS_WORKER_ENABLED", "false").lower() != "true":
        parser.exit(2, "Worker desativado. Consulte docs/processamento-planos.md.\n")
    if os.getenv("SYLLABUS_PRIVACY_READY", "false").lower() != "true":
        parser.exit(2, "A integração aguarda implantação e validação das políticas S6-D02.\n")
    config = ProcessingConfig.from_env()
    if not config.api_key:
        parser.exit(2, "Configure GEMINI_API_KEY somente no servidor.\n")
    storage = SupabaseStorageService()
    if not storage.supabase_url or not (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")):
        parser.exit(2, "Worker exige Storage persistente e credencial de servidor.\n")
    worker = SyllabusWorker(SessionLocal, storage, GeminiProvider(config), config)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        while True:
            worked = worker.run_once()
            if args.once:
                break
            if not worked:
                time.sleep(1)
    except KeyboardInterrupt:
        pass  # Lease expira; outra execução recupera o item com orçamento preservado.


if __name__ == "__main__":
    main()
