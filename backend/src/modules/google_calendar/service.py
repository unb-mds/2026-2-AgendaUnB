"""Credenciais do Google Agenda obtidas durante o login Supabase."""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import GoogleCalendarConnection, Profile
from src.middlewares.auth import CurrentUser

CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.app.created"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
REAUTHORIZE = "Entre novamente com Google e permita o acesso ao Google Agenda."


@dataclass(frozen=True)
class GoogleOAuthSettings:
    client_id: str
    client_secret: str
    cipher: Fernet

    @classmethod
    def from_env(cls):
        client_id = os.getenv("SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID", "").strip()
        client_secret = os.getenv("SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET", "").strip()
        try:
            cipher = Fernet(os.getenv("GOOGLE_TOKEN_ENCRYPTION_KEY", "").strip())
        except (TypeError, ValueError):
            cipher = None
        if not client_id or not client_secret or cipher is None:
            raise HTTPException(503, "Google Agenda indisponível no servidor.")
        return cls(client_id, client_secret, cipher)


def get_connection(db: Session, user: CurrentUser) -> GoogleCalendarConnection | None:
    connection = db.get(GoogleCalendarConnection, user.id)
    if (connection and user.google_sub and connection.google_sub == user.google_sub
            and connection.google_email == (user.email or "").strip().casefold()
            and CALENDAR_SCOPE in connection.granted_scope.split()):
        return connection
    return None


def lock_account(db: Session, user: CurrentUser) -> None:
    if db.scalar(select(Profile.id).where(Profile.id == user.id).with_for_update()) is None:
        raise HTTPException(403, "Perfil da aplicação não encontrado.")


def _refresh(refresh_token: str, settings: GoogleOAuthSettings) -> dict:
    try:
        response = httpx.post(TOKEN_ENDPOINT, data={
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }, timeout=8)
    except httpx.RequestError:
        raise HTTPException(503, "Não foi possível consultar o Google Agenda.") from None
    try:
        token = response.json()
        if response.status_code == 400 and token.get("error") == "invalid_grant":
            raise HTTPException(409, REAUTHORIZE)
        if response.status_code != 200:
            raise HTTPException(503, "Não foi possível consultar o Google Agenda.")
        if not isinstance(token["access_token"], str) or not token["access_token"]:
            raise ValueError
        token["expires_in"] = int(token["expires_in"])
        if not 1 <= token["expires_in"] <= 86400:
            raise ValueError
    except (AttributeError, KeyError, TypeError, ValueError):
        raise HTTPException(502, "Resposta inválida do Google Agenda.") from None
    return token


def _store_tokens(connection: GoogleCalendarConnection, token: dict, refresh_token: str,
                  settings: GoogleOAuthSettings) -> str:
    replacement = token.get("refresh_token")
    if isinstance(replacement, str) and replacement:
        refresh_token = replacement
    access_token = token["access_token"]
    connection.encrypted_access_token = settings.cipher.encrypt(access_token.encode()).decode()
    connection.encrypted_refresh_token = settings.cipher.encrypt(refresh_token.encode()).decode()
    connection.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=token["expires_in"])
    return access_token


def save_login_grant(db: Session, user: CurrentUser, refresh_token: str) -> None:
    settings = GoogleOAuthSettings.from_env()
    token = _refresh(refresh_token, settings)
    scope = token.get("scope")
    if not isinstance(scope, str) or CALENDAR_SCOPE not in scope.split():
        raise HTTPException(403, "A permissão do Google Agenda não foi concedida.")
    try:
        response = httpx.get(USERINFO_ENDPOINT, headers={"Authorization": f"Bearer {token['access_token']}"}, timeout=8)
        if response.status_code != 200:
            raise HTTPException(503, "Não foi possível validar a conta Google.")
        identity = response.json()
    except (httpx.RequestError, ValueError):
        raise HTTPException(503, "Não foi possível validar a conta Google.") from None
    if (not isinstance(identity, dict) or identity.get("sub") != user.google_sub
            or identity.get("email_verified") is not True or not isinstance(identity.get("email"), str)
            or identity["email"].strip().casefold() != user.email.strip().casefold()):
        raise HTTPException(403, "A conta Google precisa corresponder ao e-mail confirmado da Agenda UnB.")

    lock_account(db, user)
    connection = db.get(GoogleCalendarConnection, user.id)
    if connection is None:
        connection = GoogleCalendarConnection(user_id=user.id)
    elif connection.google_sub != user.google_sub:
        connection.calendar_id = None
    connection.google_sub = user.google_sub
    connection.google_email = user.email.strip().casefold()
    connection.granted_scope = scope
    _store_tokens(connection, token, refresh_token, settings)
    db.add(connection)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Esta conta Google já está associada a outro perfil.") from None


def get_access_token(connection: GoogleCalendarConnection, settings: GoogleOAuthSettings) -> str:
    expires = connection.access_token_expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    try:
        if expires > datetime.now(timezone.utc) + timedelta(seconds=60):
            return settings.cipher.decrypt(connection.encrypted_access_token.encode()).decode()
        refresh_token = settings.cipher.decrypt(connection.encrypted_refresh_token.encode()).decode()
    except InvalidToken:
        raise HTTPException(409, REAUTHORIZE) from None

    token = _refresh(refresh_token, settings)
    scope = token.get("scope")
    if isinstance(scope, str) and CALENDAR_SCOPE not in scope.split():
        raise HTTPException(409, REAUTHORIZE)
    return _store_tokens(connection, token, refresh_token, settings)
