"""S8-D02 (#84): proteções transversais da API.

Cobre cabeçalhos, CORS, limites de corpo e de taxa, busca literal, teto de
sugestões e a exigência de e-mail confirmado. Não usa rede nem Supabase.
"""
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient

from src.middlewares.auth import get_current_user
from src.middlewares.security import (
    BodyLimitMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    client_address,
    escape_like,
    parse_cors_origins,
)
from tests.test_events_api import make_public_event

ALLOWED_ORIGIN = "http://localhost:5173"


# ---------------------------------------------------------------------------
# Cabeçalhos
# ---------------------------------------------------------------------------

def test_every_response_carries_protection_headers(api):
    client, _, _, _ = api
    for response in (client.get("/health"), client.get("/api/v1/events"), client.get("/api/v1/events/nao-e-uuid")):
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "no-referrer"
        assert "default-src 'none'" in response.headers["content-security-policy"]
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


def test_private_responses_are_never_cached_and_hsts_follows_https(api):
    client, _, _, _ = api
    assert client.get("/api/v1/me/events").headers["cache-control"] == "no-store"
    assert client.get("/api/v1/events", headers={"Authorization": "Bearer x"}).headers["cache-control"] == "no-store"
    assert "cache-control" not in client.get("/api/v1/events").headers

    assert "strict-transport-security" not in client.get("/health").headers
    behind_tls_proxy = client.get("/health", headers={"X-Forwarded-Proto": "https"})
    assert behind_tls_proxy.headers["strict-transport-security"].startswith("max-age=31536000")


def test_interactive_docs_are_not_broken_by_the_content_policy(api):
    client, _, _, _ = api
    assert "content-security-policy" not in client.get("/docs").headers


def test_docs_can_be_switched_off_for_hosted_environments():
    backend = Path(__file__).resolve().parents[1]
    script = "from src.main import app; print(app.docs_url, app.redoc_url, app.openapi_url)"
    env = {**os.environ, "API_DOCS_ENABLED": "false", "DATABASE_URL": "sqlite+pysqlite:///:memory:"}
    result = subprocess.run([sys.executable, "-c", script], cwd=backend, env=env, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["None", "None", "None"]


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

def test_cors_answers_only_the_configured_origin(api):
    client, _, _, _ = api
    allowed = client.get("/api/v1/events", headers={"Origin": ALLOWED_ORIGIN})
    assert allowed.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    # A sessão vai no Authorization; nenhum cookie é aceito entre origens.
    assert "access-control-allow-credentials" not in allowed.headers

    foreign = client.get("/api/v1/events", headers={"Origin": "https://site-malicioso.example"})
    assert "access-control-allow-origin" not in foreign.headers


def test_cors_preflight_accepts_only_known_headers(api):
    client, _, _, _ = api
    base = {"Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "POST"}
    ok = client.options("/api/v1/me/events", headers={**base, "Access-Control-Request-Headers": "authorization,content-type,idempotency-key"})
    assert ok.status_code == 200
    refused = client.options("/api/v1/me/events", headers={**base, "Access-Control-Request-Headers": "x-qualquer-coisa"})
    assert refused.status_code == 400
    foreign = client.options("/api/v1/me/events", headers={**base, "Origin": "https://site-malicioso.example"})
    assert foreign.status_code == 400


@pytest.mark.parametrize("raw", ["*", "https://*.vercel.app", "https://app.exemplo.br/caminho", "app.exemplo.br", "ftp://app.exemplo.br"])
def test_cors_configuration_refuses_wildcards_and_malformed_origins(raw):
    with pytest.raises(RuntimeError):
        parse_cors_origins(raw)


def test_cors_configuration_normalizes_exact_origins():
    assert parse_cors_origins(" https://app.exemplo.br/ , http://localhost:5173,, https://app.exemplo.br") == [
        "https://app.exemplo.br", "http://localhost:5173"]


# ---------------------------------------------------------------------------
# Limites de corpo e de taxa
# ---------------------------------------------------------------------------

def test_oversized_json_is_refused_before_reaching_the_routes(api):
    client, _, _, _ = api
    huge = {"title": "Compromisso", "starts_at": "2026-11-20T14:00:00-03:00", "description": "a" * 300_000}
    assert client.post("/api/v1/me/events", json=huge).status_code == 413
    normal = {"title": "Compromisso", "starts_at": "2026-11-20T14:00:00-03:00", "description": "a" * 9_000}
    assert client.post("/api/v1/me/events", json=normal).status_code == 201


def test_body_limit_also_counts_bodies_sent_without_content_length():
    app = FastAPI()
    app.add_middleware(BodyLimitMiddleware, max_body_bytes=1024)

    @app.post("/eco")
    async def eco(payload: dict):
        return {"n": len(payload["v"])}

    def chunks():
        yield b'{"v":"'
        yield b"a" * 4096
        yield b'"}'

    client = TestClient(app)
    assert client.post("/eco", content=chunks(), headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post("/eco", json={"v": "ok"}).json() == {"n": 2}


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def limited_app(**options):
    app = FastAPI()
    clock = FakeClock()
    app.add_middleware(RateLimitMiddleware, clock=clock, **options)

    @app.get("/x")
    def read():
        return {"ok": True}

    @app.post("/x")
    def write():
        return {"ok": True}

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return TestClient(app), clock


def test_rate_limit_blocks_bursts_and_recovers_after_the_window():
    client, clock = limited_app(per_minute=3, write_per_minute=0, trusted_proxy_hops=0)
    assert [client.get("/x").status_code for _ in range(4)] == [200, 200, 200, 429]
    blocked = client.get("/x")
    assert blocked.status_code == 429
    assert 1 <= int(blocked.headers["retry-after"]) <= 61
    assert "Muitas requisições" in blocked.json()["detail"]
    # Verificação de saúde e preflight nunca são limitados.
    assert client.get("/health").status_code == 200
    assert client.options("/x").status_code in (200, 405)

    clock.now += 61
    assert client.get("/x").status_code == 200


def test_rate_limit_is_stricter_for_writes_and_separated_by_client():
    client, _ = limited_app(per_minute=100, write_per_minute=2, trusted_proxy_hops=1)
    ana = {"X-Forwarded-For": "203.0.113.7"}
    assert [client.post("/x", headers=ana).status_code for _ in range(3)] == [200, 200, 429]
    assert client.get("/x", headers=ana).status_code == 200  # leitura segue liberada
    assert client.post("/x", headers={"X-Forwarded-For": "203.0.113.8"}).status_code == 200  # outro cliente


def test_client_address_ignores_forwarded_values_written_by_the_client():
    scope = {"client": ("10.0.0.9", 1234), "headers": [(b"x-forwarded-for", b"1.1.1.1, 203.0.113.7, 10.0.0.2")]}
    assert client_address(scope, 0) == "10.0.0.9"       # sem proxy confiável, vale a conexão
    assert client_address(scope, 1) == "10.0.0.2"       # o último trecho é do proxy da hospedagem
    assert client_address(scope, 2) == "203.0.113.7"
    assert client_address({"client": ("10.0.0.9", 1), "headers": []}, 2) == "10.0.0.9"


# ---------------------------------------------------------------------------
# Regras de negócio com impacto em abuso
# ---------------------------------------------------------------------------

def test_search_treats_wildcards_as_plain_text(api):
    client, sessions, _, ids = api
    with sessions() as db:
        db.add_all([make_public_event(ids, title="Curso 100% online"),
                    make_public_event(ids, title="Semana Universitária"),
                    make_public_event(ids, title="Mostra_de_extensão")])
        db.commit()

    def titles(term):
        return sorted(event["title"] for event in client.get("/api/v1/events", params={"q": term}).json())

    assert titles("%") == ["Curso 100% online"]
    assert titles("_") == ["Mostra_de_extensão"]
    assert titles("semana") == ["Semana Universitária"]
    assert escape_like(r"50%_\x") == r"50\%\_\\x"


def test_pending_suggestions_are_capped_per_account(api):
    client, _, _, _ = api
    payload = {"title": "Encontro de estudantes", "description": "Conversa", "starts_at": "2026-11-20T14:00:00-03:00"}
    statuses = [client.post("/api/v1/suggestions", json=payload).status_code for _ in range(11)]
    assert statuses == [201] * 10 + [429]


def auth_with(monkeypatch, account):
    monkeypatch.setenv("SUPABASE_URL", "https://auth.example.test")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json=account))
    database = Mock()
    database.scalar.return_value = "student"
    return get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="token"), database)


def test_api_refuses_accounts_with_unconfirmed_email(monkeypatch):
    uid = str(uuid4())
    for account in ({"id": uid}, {"id": uid, "email_confirmed_at": None}, {"id": uid, "email_confirmed_at": ""}):
        with pytest.raises(HTTPException) as error:
            auth_with(monkeypatch, account)
        assert error.value.status_code == 403
    assert str(auth_with(monkeypatch, {"id": uid, "email_confirmed_at": "2026-11-01T12:00:00Z"}).id) == uid


def test_security_headers_survive_unhandled_errors():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/falha")
    def fail():
        raise HTTPException(status_code=500, detail="erro")

    response = TestClient(app).get("/falha")
    assert response.status_code == 500
    assert response.headers["x-content-type-options"] == "nosniff"
