"""Inspectores sintéticos importáveis por spawn sem carregar a aplicação HTTP."""
import time


class StalledInspector:
    def __init__(self, reached):
        self.reached = reached

    def __call__(self, content, max_pages):
        self.reached.set()
        time.sleep(60)


def failing_inspector(content, max_pages):
    raise ValueError("PRIVATE_PDF_CONTENT_NEVER_LOG")


def invalid_inspector(content, max_pages):
    return "PRIVATE_PDF_CONTENT_NEVER_LOG"
