import asyncio

from starlette.responses import JSONResponse

from src.modules.syllabus.services import MAX_FILE_SIZE_BYTES


class UploadLimitsMiddleware:
    """Bound multipart uploads before FastAPI parses and spools their bodies."""

    def __init__(self, app):
        self.app = app
        self.slots = asyncio.Semaphore(4)
        self.max_body_bytes = MAX_FILE_SIZE_BYTES + 64 * 1024

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        is_upload = path == "/api/v1/syllabus/upload"
        is_text = path == "/api/v1/syllabus/text" or (path.startswith("/api/v1/syllabus/") and path.endswith("/extractions"))
        if scope["type"] != "http" or scope["method"] != "POST" or not (is_upload or is_text):
            await self.app(scope, receive, send)
            return

        max_body_bytes = self.max_body_bytes if is_upload else 256000

        async def reject(status, detail):
            await JSONResponse({"detail": detail}, status_code=status)(scope, receive, send)

        try:
            await asyncio.wait_for(self.slots.acquire(), timeout=1)
        except TimeoutError:
            await reject(429, "Muitos envios simultâneos. Tente novamente mais tarde.")
            return

        try:
            headers = dict(scope["headers"])
            try:
                declared_size = int(headers.get(b"content-length", b"0"))
            except ValueError:
                declared_size = 0
            if declared_size > max_body_bytes:
                await reject(413, "O arquivo excede o tamanho máximo permitido.")
                return

            chunks = []
            total = 0
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                if message["type"] != "http.request":
                    continue
                chunk = message.get("body", b"")
                total += len(chunk)
                if total > max_body_bytes:
                    await reject(413, "O arquivo excede o tamanho máximo permitido.")
                    return
                chunks.append(chunk)
                if not message.get("more_body", False):
                    break

            body = b"".join(chunks)
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": body, "more_body": False}
                return await receive()

            await self.app(scope, bounded_receive, send)
        finally:
            self.slots.release()
