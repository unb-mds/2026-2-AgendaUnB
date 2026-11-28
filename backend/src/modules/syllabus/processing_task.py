"""Limite de tempo real para Storage, parser e IA, sem matar o worker da fila."""
import json
import logging
import multiprocessing
import queue
import re
import threading
import time
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.modules.syllabus.extraction import ExtractionData, ExtractionResult, TextPage, extract_pages, validate_candidates
from src.modules.syllabus.processing_config import ERROR_MESSAGES, ProcessingConfig, ProcessingError


@dataclass
class DocumentResult:
    page_count: int | None
    extraction: ExtractionResult
    provider_name: str = "google"
    model_name: str | None = None
    fallback_used: bool = False
    primary_error_reason: str = ""


class TaskOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_count: int | None = Field(default=None, ge=1, le=10, strict=True)
    extraction: ExtractionData
    unsupported_dates: int = Field(ge=0, le=100, strict=True)
    provider_name: str = Field(default="google", pattern="^(google|groq|openrouter|mistral)$")
    model_name: str | None = Field(default=None, max_length=100)
    fallback_used: bool = Field(default=False, strict=True)
    primary_error_reason: str = Field(default="", pattern="^$|^[a-z0-9_]{1,40}$")


def process_document(path, storage, provider, config: ProcessingConfig) -> DocumentResult:
    """Execução direta injetável nos testes unitários; não é o padrão do worker."""
    if isinstance(path, list):
        pages = [TextPage(**page) for page in path]
    else:
        # Adaptador apenas para benchmarks/testes legados. O worker S7 passa
        # exclusivamente um snapshot de texto aprovado, nunca um caminho de PDF.
        content = storage.download_file(path)
        pages = extract_pages(content, config)
    if hasattr(provider, "set_validation_context"):
        provider.set_validation_context(
            default_year=config.reference_year,
            reference_subject=config.reference_subject,
            reference_schedule=config.reference_schedule,
        )
    result = validate_candidates(
        provider.extract(pages),
        pages,
        default_year=config.reference_year,
        reference_subject=config.reference_subject,
        reference_schedule=config.reference_schedule,
    )
    return DocumentResult(len(pages) if pages[0].pagina is not None else None, result,
                          getattr(provider, "provider_name", "google"),
                          getattr(provider, "model_name", config.model),
                          getattr(provider, "fallback_used", False),
                          getattr(provider, "primary_error_reason", ""))


def _child(send, path, storage, provider, config):
    # Bibliotecas que tratam entrada não confiável também não escrevem dados no
    # stderr do processo. Só JSON sanitizado cruza o pipe; nunca pickle na volta.
    logging.disable(logging.CRITICAL)
    if hasattr(provider, "set_deadline"):
        provider.set_deadline(time.monotonic() + config.attempt_timeout_seconds - 1)
    try:
        result = process_document(path, storage, provider, config)
        output = dict(page_count=result.page_count,
                      extraction={"candidatos": [candidate.model_dump(mode="json")
                                                  for candidate in result.extraction.candidates]},
                      unsupported_dates=result.extraction.unsupported_dates,
                      provider_name=result.provider_name, model_name=result.model_name,
                      fallback_used=result.fallback_used, primary_error_reason=result.primary_error_reason)
    except ProcessingError as error:
        reason = error.reason if re.fullmatch(r"[a-z0-9_]{1,40}", error.reason or "") else ""
        output = {"error": error.code, "retryable": error.retryable, "rate_limited": error.rate_limited, "reason": reason}
    except Exception:
        output = {"error": "erro_interno", "retryable": True}
    try:
        send.send_bytes(json.dumps(output, ensure_ascii=False).encode("utf-8"))
    finally:
        send.close()


def run_in_worker(path, storage, provider, config: ProcessingConfig) -> DocumentResult:
    """Executa a tentativa no próprio processo do worker com deadline real, evitando duplo spawn."""
    outcome: queue.Queue = queue.Queue(maxsize=1)

    def _target():
        try:
            if hasattr(provider, "set_deadline"):
                provider.set_deadline(time.monotonic() + config.attempt_timeout_seconds - 1)
            result = process_document(path, storage, provider, config)
            payload = dict(
                page_count=result.page_count,
                extraction={"candidatos": [candidate.model_dump(mode="json")
                                            for candidate in result.extraction.candidates]},
                unsupported_dates=result.extraction.unsupported_dates,
                provider_name=result.provider_name, model_name=result.model_name,
                fallback_used=result.fallback_used, primary_error_reason=result.primary_error_reason,
            )
            validated = TaskOutput.model_validate(payload)
            outcome.put(("ok", DocumentResult(
                validated.page_count,
                ExtractionResult(validated.extraction.candidatos, validated.unsupported_dates),
                validated.provider_name, validated.model_name, validated.fallback_used,
                validated.primary_error_reason,
            )))
        except ProcessingError as error:
            reason = error.reason if re.fullmatch(r"[a-z0-9_]{1,40}", error.reason or "") else ""
            outcome.put(("err", ProcessingError(
                error.code, retryable=error.retryable, rate_limited=error.rate_limited, reason=reason,
            )))
        except Exception:
            outcome.put(("err", ProcessingError("erro_interno", retryable=True)))

    thread = threading.Thread(target=_target, daemon=True)
    thread.start()
    try:
        kind, value = outcome.get(timeout=config.attempt_timeout_seconds)
    except queue.Empty:
        raise ProcessingError("tempo_esgotado", retryable=True, reason="attempt_timeout") from None
    if kind == "err":
        raise value
    return value


def run_isolated(path, storage, provider, config: ProcessingConfig) -> DocumentResult:
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(target=_child, args=(send, path, storage, provider, config), daemon=True)
    try:
        process.start()
        send.close()
        if not receive.poll(config.attempt_timeout_seconds):
            raise ProcessingError("tempo_esgotado", retryable=True)
        output = json.loads(receive.recv_bytes(maxlength=1024 * 1024))
        if not isinstance(output, dict):
            raise ProcessingError("erro_interno", retryable=True)
        if "error" in output:
            code = output.get("error")
            rate_limited = output.get("rate_limited", False)
            reason = output.get("reason", "")
            if (code not in ERROR_MESSAGES or type(output.get("retryable")) is not bool
                    or type(rate_limited) is not bool or not isinstance(reason, str)
                    or (reason and not re.fullmatch(r"[a-z0-9_]{1,40}", reason))):
                raise ProcessingError("erro_interno", retryable=True)
            raise ProcessingError(code, retryable=output["retryable"], rate_limited=rate_limited, reason=reason)
        validated = TaskOutput.model_validate(output)
        return DocumentResult(validated.page_count,
                              ExtractionResult(validated.extraction.candidatos, validated.unsupported_dates),
                              validated.provider_name, validated.model_name, validated.fallback_used,
                              validated.primary_error_reason)
    except ProcessingError:
        raise
    except (EOFError, OSError, ValueError, TypeError, ValidationError):
        raise ProcessingError("erro_interno", retryable=True) from None
    finally:
        receive.close()
        send.close()
        if process.pid is not None:
            process.join(timeout=0.2)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            if not process.is_alive():
                process.close()
