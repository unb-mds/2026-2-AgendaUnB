"""Deployment configuration without logging credential values."""
from urllib.parse import urlsplit
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


def cors_origins(env):
    hosted = env.get("APP_ENV", "local") != "local"
    default = "" if hosted else "http://localhost:5173,http://127.0.0.1:5173"
    origins = list(dict.fromkeys(value.strip() for value in env.get("CORS_ORIGINS", default).split(",") if value.strip()))
    if hosted and not origins:
        raise ValueError("Configure CORS_ORIGINS explicitamente no ambiente hospedado.")
    for origin in origins:
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.path
            or (hosted and parsed.scheme != "https")
            or any(char in origin for char in "*?#")
        ):
            raise ValueError("CORS_ORIGINS exige origens exatas, sem caminhos nem curingas.")
    return origins


def require_database_tls(database_url: str, app_env: str) -> None:
    if app_env == "local":
        return
    message = "DATABASE_URL hospedada exige PostgreSQL com sslmode=require, verify-ca ou verify-full."
    try:
        url = make_url(database_url)
    except (ArgumentError, ValueError):
        raise ValueError(message) from None
    if url.get_backend_name() != "postgresql" or url.query.get("sslmode") not in ("require", "verify-ca", "verify-full"):
        raise ValueError(message)
