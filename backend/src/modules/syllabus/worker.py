"""Fila SQL durável. Rodar como processo independente da API, nunca BackgroundTasks."""
import argparse
import logging
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import or_, select, update

from src.database.connection import SessionLocal
from src.database.models import AssessmentCandidate, Syllabus, SyllabusVersion
from src.modules.syllabus.extraction import CandidateData, ExtractionResult, VERSION
from src.modules.syllabus.gemini import GeminiProvider
from src.modules.syllabus.processing_config import ERROR_MESSAGES, ProcessingConfig, ProcessingError
from src.modules.syllabus.processing_task import DocumentResult, run_isolated
from src.modules.syllabus.privacy import privacy_checks
from src.modules.syllabus.preparation import checked_pages, contains_personal_data, text_hash
from src.modules.syllabus.versions import private_version
from src.modules.syllabus.timing import duration_ms as elapsed_ms

logger = logging.getLogger("agenda_unb.syllabus.worker")
_SPAWN_LOCK = threading.Lock()
_ACTIVE_WORKER: subprocess.Popen | None = None
_CACHE_CUTOFF = datetime(2026, 11, 16, 4, 7, 0, tzinfo=timezone.utc)


def utcnow():
    return datetime.now(timezone.utc)


def worker_ready_to_spawn() -> bool:
    return (
        os.getenv("SYLLABUS_WORKER_ENABLED", "false").lower() == "true"
        and os.getenv("SYLLABUS_PRIVACY_READY", "false").lower() == "true"
        and os.getenv("SYLLABUS_PROVIDER_TERMS_READY", "false").lower() == "true"
        and bool(os.getenv("GEMINI_API_KEY", "").strip())
    )


def spawn_worker_drain() -> bool:
    """Inicia um worker independente em --drain quando a execução automática está ativa."""
    global _ACTIVE_WORKER
    if os.getenv("SYLLABUS_DAEMON_ACTIVE", "false").lower() == "true":
        return False
    if not worker_ready_to_spawn():
        return False
    with _SPAWN_LOCK:
        if _ACTIVE_WORKER is not None and _ACTIVE_WORKER.poll() is None:
            return False
        backend_dir = str(Path(__file__).resolve().parents[3])
        options: dict = {}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            options["start_new_session"] = True
        try:
            _ACTIVE_WORKER = subprocess.Popen(
                [sys.executable, "-m", "src.modules.syllabus.worker", "--drain", "--max-items", "25"],
                cwd=backend_dir,
                stdin=subprocess.DEVNULL,
                **options,
            )
            return True
        except OSError:
            logger.warning("syllabus_worker_spawn_failed")
            return False


@dataclass(frozen=True)
class Lease:
    id: UUID
    token: UUID
    execution: int
    user_id: UUID
    file_path: str | None
    created_at: datetime
    terminal: bool = False
    approved_pages: list[dict] | None = None
    approved_hash: str | None = None
    version_id: UUID | None = None
    year: int | None = None


class SyllabusWorker:
    def __init__(self, session_factory, storage, provider, config: ProcessingConfig, *,
                 runner=run_isolated, pace: bool = False, sleep=time.sleep, clock=time.monotonic):
        self.sessions = session_factory
        self.storage = storage
        self.provider = provider
        self.config = config
        self.runner = runner
        self.pace = pace
        self.sleep = sleep
        self.clock = clock
        self._last_provider_call_at: float | None = None

    def _find_cached_extraction(self, lease: Lease, pages: list[dict]) -> tuple[DocumentResult, str] | None:
        """Reaproveita candidatos validados de snapshot idêntico (mesmo SHA-256 canônico)."""
        if not lease.approved_hash:
            return None
        with self.sessions() as db:
            source = db.scalar(
                select(Syllabus)
                .where(
                    Syllabus.id != lease.id,
                    Syllabus.status == "concluido",
                    Syllabus.approved_hash == lease.approved_hash,
                    Syllabus.ano == lease.year,
                    Syllabus.versao_processamento == VERSION,
                    Syllabus.provedor_ia == "google",
                    Syllabus.approved_version_id.is_not(None),
                    Syllabus.processado_em >= _CACHE_CUTOFF,
                )
                .order_by(Syllabus.processado_em.asc(), Syllabus.id.asc())
                .limit(1)
            )
            if source is None or not source.approved_pages or source.approved_pages != pages:
                return None
            rows = db.scalars(
                select(AssessmentCandidate)
                .where(
                    AssessmentCandidate.plano_id == source.id,
                    AssessmentCandidate.version_id == source.approved_version_id,
                )
                .order_by(AssessmentCandidate.ordem.asc(), AssessmentCandidate.id.asc())
            ).all()
            if len(rows) != source.extracted_events_count:
                return None
            candidates: list[CandidateData] = []
            try:
                for row in rows:
                    if row.kind not in ("prova", "trabalho"):
                        return None
                    candidates.append(
                        CandidateData(
                            titulo=row.title,
                            tipo=row.kind,
                            data_sugerida=row.data_sugerida.isoformat() if row.data_sugerida else None,
                            hora_sugerida=row.hora_sugerida.strftime("%H:%M") if row.hora_sugerida else None,
                            campos_ambiguos=list(row.campos_ambiguos or []),
                            pagina_origem=row.source_page,
                            trecho_origem=row.source_excerpt or row.title,
                        )
                    )
            except ValidationError:
                return None
            page_count = len(pages) if pages[0]["pagina"] is not None else None
            model_name = source.modelo_ia or self.config.model
            return DocumentResult(page_count, ExtractionResult(candidates)), model_name

    def claim(self) -> Lease | None:
        now = utcnow()
        ready = or_(
            (Syllabus.status == "pendente") & or_(Syllabus.next_attempt_at.is_(None), Syllabus.next_attempt_at <= now),
            (Syllabus.status == "processando") &
            (Syllabus.processamento_iniciado_em < now - timedelta(seconds=self.config.lease_seconds)),
        )
        with self.sessions() as db:
            job = db.scalar(select(Syllabus).where(Syllabus.tipo == "particular", Syllabus.authorized_at.is_not(None),
                                  Syllabus.approved_pages.is_not(None), ready)
                            .order_by(Syllabus.queued_at, Syllabus.id).with_for_update(skip_locked=True).limit(1))
            if job is None:
                return None
            token = uuid4()
            attempt = job.execucao_atual + 1
            exhausted = (attempt > self.config.max_attempts or
                         job.cost_reserved_usd + self.config.attempt_reservation > self.config.max_file_cost_usd)
            version = db.get(SyllabusVersion, job.approved_version_id) if job.approved_version_id else private_version(db, job)
            exhausted = exhausted or (version is None or version.visibility != "privada" or version.syllabus_id != job.id)
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
                              approved_version_id=version.id,
                              cost_reserved_usd=job.cost_reserved_usd + self.config.attempt_reservation)
            lease = Lease(job.id, token, attempt, job.user_id, job.file_path, job.queued_at or job.created_at, terminal=exhausted,
                          approved_pages=job.approved_pages, approved_hash=job.approved_hash,
                          version_id=version.id if version else None, year=job.ano)
            changed = db.execute(update(Syllabus).where(*condition).values(**values),
                                 execution_options={"synchronize_session": False}).rowcount
            db.commit()
            return lease if changed == 1 else None

    def fail(self, lease: Lease, error: ProcessingError, duration_ms: int):
        with self.sessions() as db:
            active = db.scalar(select(Syllabus).where(
                Syllabus.id == lease.id, Syllabus.processing_token == lease.token,
                Syllabus.status == "processando").with_for_update())
            if active is None:
                return  # Não registrar uma falha atribuída a um lease antigo.
            retry = (error.retryable and lease.execution < self.config.max_attempts and
                     active.cost_reserved_usd + self.config.attempt_reservation <= self.config.max_file_cost_usd)
            delay_seconds = (
                self.config.rate_limit_delay_seconds
                if getattr(error, "rate_limited", False) and self.config.retry_delay_seconds > 0
                else self.config.retry_delay_seconds
            )
            db.execute(update(Syllabus).where(Syllabus.id == lease.id, Syllabus.processing_token == lease.token,
                                             Syllabus.status == "processando").values(
                status="pendente" if retry else "falha", processing_token=None,
                next_attempt_at=utcnow() + timedelta(seconds=delay_seconds) if retry else None,
                erro_codigo=None if retry else error.code,
                error_message=None if retry else ERROR_MESSAGES[error.code],
                processado_em=None if retry else utcnow(), processing_duration_ms=duration_ms,
            ))
            db.commit()
        total = elapsed_ms(lease.created_at, utcnow())
        logger.info("syllabus_attempt execution=%d code=%s reason=%s retry=%s duration_ms=%d total_duration_ms=%d over_target=%s",
                    lease.execution, error.code, error.reason or "none", retry, duration_ms, total, total >= 20000)

    def run_once(self) -> bool:
        lease = self.claim()
        if lease is None:
            return False
        if lease.terminal:
            total = elapsed_ms(lease.created_at, utcnow())
            logger.info("syllabus_exhausted total_duration_ms=%d over_target=%s", total, total >= 20000)
            return True
        started = time.monotonic()
        try:
            pages = checked_pages(lease.approved_pages or [])
            if text_hash(pages) != lease.approved_hash:
                raise ProcessingError("pdf_invalido")
            if contains_personal_data(pages):
                raise ProcessingError("texto_com_dados_pessoais")
            cached = self._find_cached_extraction(lease, pages)
            from_cache = cached is not None
            if cached is not None:
                document, model_name = cached
            else:
                if self.pace and self.config.min_interval_seconds > 0 and self._last_provider_call_at is not None:
                    wait = self.config.min_interval_seconds - (self.clock() - self._last_provider_call_at)
                    if wait > 0:
                        self.sleep(wait)
                self._last_provider_call_at = self.clock()
                run_config = replace(self.config, reference_year=lease.year) if lease.year is not None else self.config
                document = self.runner(pages, None, self.provider, run_config)
                model_name = self.config.model
            result = document.extraction
            with self.sessions() as db:
                duration = round((time.monotonic() - started) * 1000)
                version = db.scalar(select(SyllabusVersion).where(
                    SyllabusVersion.id == lease.version_id,
                    SyllabusVersion.syllabus_id == lease.id,
                    SyllabusVersion.visibility == "privada",
                ).with_for_update())
                if version is None:
                    raise ProcessingError("erro_interno")
                active_job = db.scalar(select(Syllabus).where(
                    Syllabus.id == lease.id, Syllabus.status == "processando", Syllabus.processing_token == lease.token,
                ).with_for_update())
                if active_job is None:
                    db.rollback()  # Um worker com lease mais novo já assumiu.
                    return True
                values = dict(
                    status="concluido",
                    processing_token=None,
                    processado_em=utcnow(),
                    paginas=document.page_count,
                    extracted_events_count=len(result.candidates),
                    processing_duration_ms=duration,
                    modelo_ia=model_name,
                )
                if from_cache:
                    values["cost_reserved_usd"] = max(
                        Decimal("0"), active_job.cost_reserved_usd - self.config.attempt_reservation
                    )
                changed = db.execute(update(Syllabus).where(
                    Syllabus.id == lease.id, Syllabus.status == "processando", Syllabus.processing_token == lease.token,
                ).values(**values), execution_options={"synchronize_session": False}).rowcount
                if changed != 1:
                    db.rollback()  # Um worker com lease mais novo já assumiu.
                    return True
                for order, candidate in enumerate(result.candidates):
                    db.add(AssessmentCandidate(
                        plano_id=lease.id, version_id=lease.version_id, execucao=lease.execution, ordem=order,
                        **candidate.model_dump(), provedor_ia="google", modelo_ia=model_name,
                        versao_processamento=VERSION, status="pendente", ambiguous=bool(candidate.campos_ambiguos),
                    ))
                db.commit()  # Candidatos + estado final são uma única transação.
            total = elapsed_ms(lease.created_at, utcnow())
            event_name = "syllabus_completed_cached" if from_cache else "syllabus_completed"
            logger.info("%s candidates=%d unsupported_dates=%d duration_ms=%d total_duration_ms=%d over_target=%s",
                        event_name, len(result.candidates), result.unsupported_dates, duration, total, total >= 20000)
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
    parser.add_argument("--drain", action="store_true", help="Processa itens prontos até esvaziar a fila")
    parser.add_argument("--max-items", type=int, default=25, help="Limite de itens processados no modo --drain")
    args = parser.parse_args()
    if args.max_items < 1 or args.max_items > 100:
        parser.exit(2, "Informe --max-items entre 1 e 100.\n")
    if os.getenv("SYLLABUS_WORKER_ENABLED", "false").lower() != "true":
        parser.exit(2, "Worker desativado. Consulte docs/processamento-planos.md.\n")
    if os.getenv("SYLLABUS_PRIVACY_READY", "false").lower() != "true":
        parser.exit(2, "A integração aguarda implantação e validação das políticas S6-D02.\n")
    config = ProcessingConfig.from_env()
    if not config.api_key:
        parser.exit(2, "Configure GEMINI_API_KEY somente no servidor.\n")
    try:
        with SessionLocal() as db:
            checks = privacy_checks(db.connection())
    except Exception:
        parser.exit(2, "Não foi possível verificar a privacidade. Confira o banco e as migrações S6-D02.\n")
    missing = [name for name, passed in checks.items() if not passed]
    if missing:
        parser.exit(2, "Pré-requisitos de privacidade ausentes: " + ", ".join(missing) + ".\n")
    if not config.provider_terms_ready:
        parser.exit(2, "Gemini aguarda validação de termos e elegibilidade S7-B02.\n")
    worker = SyllabusWorker(SessionLocal, None, GeminiProvider(config), config, pace=True)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    processed = 0
    try:
        while True:
            worked = worker.run_once()
            if args.once:
                break
            if args.drain:
                if not worked:
                    break
                processed += 1
                if processed >= args.max_items:
                    break
                continue
            if not worked:
                time.sleep(1)
    except KeyboardInterrupt:
        pass  # Lease expira; outra execução recupera o item com orçamento preservado.


if __name__ == "__main__":
    main()
