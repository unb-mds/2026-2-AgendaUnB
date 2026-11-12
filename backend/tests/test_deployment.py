import pytest
from fastapi.testclient import TestClient
from src.deployment import cors_origins, require_database_tls
from src.main import app


@pytest.mark.parametrize('value', ['', '*', 'https://*.vercel.app', 'http://agendaunb.com.br', 'https://agendaunb.com.br/', 'https://agendaunb.com.br/path', 'https://agendaunb.com.br?token=private'])
def test_hosted_cors_refuses_implicit_or_unsafe_origins(value):
    with pytest.raises(ValueError):
        cors_origins({'APP_ENV': 'production', 'CORS_ORIGINS': value})


def test_cors_uses_only_configured_origins_even_on_vercel():
    assert cors_origins({'APP_ENV': 'production', 'CORS_ORIGINS': 'https://agendaunb.com.br', 'VERCEL_URL': 'other.vercel.app'}) == ['https://agendaunb.com.br']


def test_cors_preflight_blocks_an_unlisted_preview():
    with TestClient(app) as client:
        response = client.options('/api/v1/events', headers={'Origin': 'https://untrusted-preview.vercel.app', 'Access-Control-Request-Method': 'GET'})
    assert response.status_code == 400
    assert 'access-control-allow-origin' not in response.headers


def test_upload_limit_response_keeps_cors_headers():
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/syllabus/upload",
            headers={"Origin": "http://localhost:5173", "Content-Length": str(11 * 1024 * 1024)},
        )
    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_hosted_database_requires_tls_without_exposing_credentials():
    url = "postgresql+psycopg://user:private-value@db.example.test/postgres"
    with pytest.raises(ValueError, match="sslmode") as error:
        require_database_tls(url, "production")
    assert "private-value" not in str(error.value)
    require_database_tls(f"{url}?sslmode=verify-full", "production")
    require_database_tls("sqlite+pysqlite:///:memory:", "local")
