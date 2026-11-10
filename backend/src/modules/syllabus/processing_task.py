"""Limite de tempo real para Storage, parser e IA, sem matar o worker da fila."""
import json
import logging
import multiprocessing
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.modules.syllabus.extraction import ExtractionData, ExtractionResult, TextPage, extract_pages, validate_candidates
from src.modules.syllabus.processing_config import ERROR_MESSAGES, ProcessingConfig, ProcessingError


@dataclass
class DocumentResult:
    page_count: int | None
    extraction: ExtractionResult


class TaskOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_count: int | None = Field(default=None, ge=1, le=10, strict=True)
    extraction: ExtractionData
    unsupported_dates: int = Field(ge=0, le=100, strict=True)


def process_document(path, storage, provider, config: ProcessingConfig) -> DocumentResult:
    """Execução direta injetável nos testes unitários; não é o padrão do worker."""
    if isinstance(path, list):
        pages = [TextPage(**page) for page in path]
    else:
        # Adaptador apenas para benchmarks/testes legados. O worker S7 passa
        # exclusivamente um snapshot de texto aprovado, nunca um caminho de PDF.
        content = storage.download_file(path)
        pages = extract_pages(content, config)
    result = validate_candidates(provider.extract(pages), pages)
    return DocumentResult(len(pages) if pages[0].pagina is not None else None, result)


def _child(send, path, storage, provider, config):
    # Bibliotecas que tratam entrada não confiável também não escrevem dados no
    # stderr do processo. Só JSON sanitizado cruza o pipe; nunca pickle na volta.
    logging.disable(logging.CRITICAL)
    try:
        result = process_document(path, storage, provider, config)
        output = dict(page_count=result.page_count,
                      extraction={"candidatos": [candidate.model_dump(mode="json")
                                                  for candidate in result.extraction.candidates]},
                      unsupported_dates=result.extraction.unsupported_dates)
    except ProcessingError as error:
        output = {"error": error.code, "retryable": error.retryable}
    except Exception:
        output = {"error": "erro_interno", "retryable": True}
    try:
        send.send_bytes(json.dumps(output, ensure_ascii=False).encode("utf-8"))
    finally:
        send.close()


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
            if code not in ERROR_MESSAGES or type(output.get("retryable")) is not bool:
                raise ProcessingError("erro_interno", retryable=True)
            raise ProcessingError(code, retryable=output["retryable"])
        validated = TaskOutput.model_validate(output)
        return DocumentResult(validated.page_count,
                              ExtractionResult(validated.extraction.candidatos, validated.unsupported_dates))
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
