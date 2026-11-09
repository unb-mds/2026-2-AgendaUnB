"""Proteções transversais da API (S8-D02, #84).

Tudo aqui é ASGI puro, sem dependência nova. Os valores vêm do ambiente
para que homologação e produção sejam configuradas sem alterar código:

    API_DOCS_ENABLED            true|false  (padrão: true; usar false em produção)
    CORS_ORIGINS                origens exatas da SPA, separadas por vírgula
    RATE_LIMIT_PER_MINUTE       requisições por cliente/minuto (padrão: 240; 0 desliga)
    RATE_LIMIT_WRITE_PER_MINUTE escritas por cliente/minuto   (padrão: 60;  0 desliga)
    TRUSTED_PROXY_HOPS          proxies confiáveis à frente da API (padrão: 0)
    MAX_JSON_BODY_BYTES         corpo máximo fora do upload     (padrão: 262144)
"""
import os
import threading
import time
from collections import deque
from urllib.parse import urlsplit

from starlette.responses import JSONResponse

UPLOAD_PATH = "/api/v1/syllabus/upload"
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")
# Respostas com dados da conta nunca ficam em cache de navegador ou proxy.
PRIVATE_PREFIXES = ("/api/v1/me", "/api/v1/syllabus", "/api/v1/suggestions")


def env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "sim"}


def env_int(name: str, default: int, *, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.getenv(name, "").strip() or default))
    except ValueError:
        return default


def parse_cors_origins(raw: str) -> list[str]:
    """Aceita somente origens exatas (esquema + host [+ porta]).

    Curinga, caminho ou esquema diferente de http(s) derrubam a inicialização:
    é melhor a API não subir do que subir aberta para qualquer site.
    """
    origins: list[str] = []
    for item in raw.split(","):
        origin = item.strip().rstrip("/")
        if not origin:
            continue
        parts = urlsplit(origin)
        if "*" in origin or parts.scheme not in {"http", "https"} or not parts.netloc or parts.path or parts.query:
            raise RuntimeError(
                f"CORS_ORIGINS inválido: '{item.strip()}'. Use origens exatas, como https://app.exemplo.br."
            )
        if origin not in origins:
            origins.append(origin)
    return origins


def escape_like(term: str, escape: str = "\\") -> str:
    """Trata % e _ digitados pelo usuário como texto, não como curingas do LIKE."""
    return (
        term.replace(escape, escape + escape)
        .replace("%", escape + "%")
        .replace("_", escape + "_")
    )


def client_address(scope, trusted_proxy_hops: int) -> str:
    """Endereço do cliente para limitar abuso.

    X-Forwarded-For é escrito pelo cliente e só o trecho acrescentado pelos
    proxies da hospedagem é confiável. Com N proxies confiáveis, o cliente é
    o N-ésimo endereço contado a partir do fim. Com 0, usa a conexão direta.
    """
    if trusted_proxy_hops > 0:
        for name, value in scope.get("headers", []):
            if name == b"x-forwarded-for":
                chain = [part.strip() for part in value.decode("latin-1").split(",") if part.strip()]
                if len(chain) >= trusted_proxy_hops:
                    return chain[-trusted_proxy_hops]
    client = scope.get("client")
    return client[0] if client else "desconhecido"


class SecurityHeadersMiddleware:
    """Cabeçalhos de proteção em toda resposta HTTP, inclusive erros."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        request_headers = dict(scope.get("headers", []))
        is_https = scope.get("scheme") == "https" or request_headers.get(b"x-forwarded-proto", b"").startswith(b"https")
        is_private = path.startswith(PRIVATE_PREFIXES) or b"authorization" in request_headers

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = [(k, v) for k, v in message.get("headers", [])]
                present = {k.lower() for k, _ in headers}

                def add(name: bytes, value: bytes):
                    if name not in present:
                        headers.append((name, value))

                add(b"x-content-type-options", b"nosniff")
                add(b"x-frame-options", b"DENY")
                add(b"referrer-policy", b"no-referrer")
                add(b"permissions-policy", b"geolocation=(), microphone=(), camera=(), payment=()")
                # A API só devolve JSON. A documentação interativa carrega scripts de CDN
                # e por isso fica fora desta política (e desligada em produção).
                if not path.startswith(DOCS_PATHS):
                    add(b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
                if is_https:
                    add(b"strict-transport-security", b"max-age=31536000; includeSubDomains")
                if is_private:
                    add(b"cache-control", b"no-store")
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodyLimitMiddleware:
    """Recusa corpos grandes fora do upload antes de o FastAPI lê-los.

    O upload de planos tem limite próprio (UploadLimitsMiddleware). As demais
    rotas recebem JSON pequeno; sem este teto, um cliente poderia ocupar a
    memória do processo enviando megabytes para qualquer POST.
    """

    def __init__(self, app, max_body_bytes: int | None = None):
        self.app = app
        self.max_body_bytes = max_body_bytes if max_body_bytes is not None else env_int(
            "MAX_JSON_BODY_BYTES", 256 * 1024, minimum=1024
        )

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] != "http"
            or scope["method"] in {"GET", "HEAD", "OPTIONS"}
            or scope.get("path") == UPLOAD_PATH
        ):
            await self.app(scope, receive, send)
            return

        async def reject():
            response = JSONResponse({"detail": "O conteúdo enviado excede o tamanho máximo permitido."}, status_code=413)
            await response(scope, receive, send)

        headers = dict(scope.get("headers", []))
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = 0
        if declared > self.max_body_bytes:
            await reject()
            return

        chunks: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            if message["type"] != "http.request":
                continue
            chunk = message.get("body", b"")
            total += len(chunk)
            if total > self.max_body_bytes:
                await reject()
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


class RateLimitMiddleware:
    """Janela deslizante em memória, por cliente.

    Protege contra rajadas (varredura, força bruta de IDs, inundação de
    sugestões e do contador de cliques). O estado vive no processo: com mais
    de uma instância da API o limite efetivo é multiplicado, e reiniciar a
    API zera as contagens. Login, cadastro e reenvio de e-mail são limitados
    pelo Supabase Auth, não por aqui.
    """

    WINDOW_SECONDS = 60.0
    MAX_TRACKED_CLIENTS = 20_000

    def __init__(
        self,
        app,
        per_minute: int | None = None,
        write_per_minute: int | None = None,
        trusted_proxy_hops: int | None = None,
        clock=time.monotonic,
    ):
        self.app = app
        self.per_minute = per_minute if per_minute is not None else env_int("RATE_LIMIT_PER_MINUTE", 240)
        self.write_per_minute = (
            write_per_minute if write_per_minute is not None else env_int("RATE_LIMIT_WRITE_PER_MINUTE", 60)
        )
        self.trusted_proxy_hops = (
            trusted_proxy_hops if trusted_proxy_hops is not None else env_int("TRUSTED_PROXY_HOPS", 0)
        )
        self.clock = clock
        self._hits: dict[tuple[str, str], deque[float]] = {}
        self._lock = threading.Lock()

    def _retry_after(self, key: tuple[str, str], limit: int) -> int | None:
        """Registra a requisição; devolve os segundos de espera se o limite estourou."""
        now = self.clock()
        cutoff = now - self.WINDOW_SECONDS
        with self._lock:
            if len(self._hits) > self.MAX_TRACKED_CLIENTS:
                for stale in [k for k, hits in self._hits.items() if not hits or hits[-1] <= cutoff]:
                    del self._hits[stale]
                if len(self._hits) > self.MAX_TRACKED_CLIENTS:
                    self._hits.clear()  # sob inundação de endereços, recomeçar é mais seguro que crescer
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= limit:
                return max(1, int(hits[0] + self.WINDOW_SECONDS - now) + 1)
            hits.append(now)
            return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] == "OPTIONS" or scope.get("path") == "/health":
            await self.app(scope, receive, send)
            return

        client = client_address(scope, self.trusted_proxy_hops)
        is_write = scope["method"] not in {"GET", "HEAD"}
        checks = [("all", self.per_minute)]
        if is_write:
            checks.append(("write", self.write_per_minute))

        for bucket, limit in checks:
            if limit <= 0:
                continue
            retry_after = self._retry_after((client, bucket), limit)
            if retry_after is not None:
                response = JSONResponse(
                    {"detail": "Muitas requisições em pouco tempo. Aguarde um instante e tente novamente."},
                    status_code=429,
                    headers={"Retry-After": str(retry_after)},
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)
