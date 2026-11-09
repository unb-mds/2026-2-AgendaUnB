"""Pré-validação de PDF em processo descartável, com prazo e saída restrita."""
import io
import logging
import multiprocessing
import time

import pypdf


DOCUMENT_ERRORS = {"malformed", "encrypted", "empty", "pages", "no_text"}


class PdfValidationError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def inspect_pdf(content: bytes, max_pages: int) -> str:
    try:
        reader = pypdf.PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            return "encrypted"
        page_count = len(reader.pages)
        if not page_count:
            return "empty"
        if page_count > max_pages:
            return "pages"
        for page in reader.pages:
            text = page.extract_text()
            if text and text.strip():
                return "valid"
        return "no_text"
    except Exception:
        return "malformed"


def _validation_child(send, content, max_pages, inspector):
    # Não encaminhar mensagens do parser, exceções ou conteúdo não confiável.
    logging.disable(logging.CRITICAL)
    try:
        result = inspector(content, max_pages)
        if result not in DOCUMENT_ERRORS | {"valid"}:
            result = "unavailable"
    except Exception:
        result = "unavailable"
    try:
        send.send_bytes(result.encode("ascii"))
    finally:
        send.close()


def validate_pdf_structure(content: bytes, max_pages: int, timeout: float, *, _inspector=None) -> None:
    """Chamada bloqueante: executar em thread; matar o parser ao vencer o prazo.

    Não são enviados sessão de banco ou objetos de Storage ao processo filho.
    O inspector injetável permite testar travamentos reais sem PDFs maliciosos.
    """
    context = multiprocessing.get_context("spawn")
    receive, send = context.Pipe(duplex=False)
    process = context.Process(
        target=_validation_child,
        args=(send, content, max_pages, _inspector or inspect_pdf),
        daemon=True,
    )
    try:
        deadline = time.monotonic() + timeout
        process.start()
        send.close()
        if not receive.poll(max(0, deadline - time.monotonic())):
            raise PdfValidationError("timeout")
        result = receive.recv_bytes(maxlength=32).decode("ascii")
        if result == "valid":
            return
        if result not in DOCUMENT_ERRORS:
            result = "unavailable"
        raise PdfValidationError(result)
    except (EOFError, OSError, ValueError, UnicodeError):
        raise PdfValidationError("unavailable") from None
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
