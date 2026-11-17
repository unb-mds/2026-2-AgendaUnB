"""OAuth e ciclo de vida de credenciais Google para o backend."""

from __future__ import annotations

import base64
import hashlib
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from uuid import UUID

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import GoogleCalendarConnection, GoogleCalendarOAuthState, Profile
from src.middlewares.auth import CurrentUser

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
REVOCATION_ENDPOINT = "https://oauth2.googleapis.com/revoke"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.app.created"
STATE_TTL = timedelta(minutes=10)
TOKEN_REFRESH_WINDOW = timedelta(seconds=60)
REAUTHORIZE = "Conecte novamente sua conta ao Google Agenda."


@dataclass(frozen=True, repr=False)
class GoogleOAuthSettings:
    client_id: str
    client_secret: str
    redirect_uri: str
    frontend_redirect_uri: str
    cipher: Fernet

    @classmethod
    def from_env(cls) -> "GoogleOAuthSettings":
        names = {
            "client_id": "GOOGLE_CALENDAR_CLIENT_ID",
            "client_secret": "GOOGLE_CALENDAR_CLIENT_SECRET",
            "redirect_uri": "GOOGLE_CALENDAR_REDIRECT_URI",
            "frontend_redirect_uri": "GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI",
            "encryption_key": "GOOGLE_TOKEN_ENCRYPTION_KEY",
        }
        values = {key: os.getenv(name, "").strip() for key, name in names.items()}
        if any(not values[key] for key in names):
            raise HTTPException(status_code=503, detail="Conexão Google não configurada no servidor")
        if not _safe_redirect(values["redirect_uri"]) or not _safe_redirect(values["frontend_redirect_uri"]):
            raise HTTPException(status_code=503, detail="URLs de retorno Google inválidas")
        try:
            key = values["encryption_key"].encode("ascii")
            cipher = Fernet(key)
        except (UnicodeEncodeError, ValueError):
            raise HTTPException(status_code=503, detail="Chave de proteção Google inválida") from None
        return cls(
            client_id=values["client_id"],
            client_secret=values["client_secret"],
            redirect_uri=values["redirect_uri"],
            frontend_redirect_uri=values["frontend_redirect_uri"],
            cipher=cipher,
        )


def _safe_redirect(value: str) -> bool:
    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(value)
    except ValueError:
        return False
    return bool(parsed.hostname and not parsed.username and not parsed.password and not parsed.fragment
                and (parsed.scheme == "https" or
                     (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"})))


def lock_account(db: Session, user_id: UUID) -> None:
    if db.scalar(select(Profile.id).where(Profile.id == user_id).with_for_update()) is None:
        raise HTTPException(403, "Perfil da aplicação não encontrado.")


def get_connection(db: Session, user: CurrentUser) -> GoogleCalendarConnection | None:
    connection = db.get(GoogleCalendarConnection, user.id)
    if (connection and connection.google_email == (user.email or "").strip().casefold()
            and CALENDAR_SCOPE in connection.granted_scope.split()
            and connection.encrypted_refresh_token and connection.encrypted_access_token
            and connection.access_token_expires_at):
        return connection
    return None


def clear_credentials(connection: GoogleCalendarConnection) -> None:
    connection.encrypted_access_token = None
    connection.encrypted_refresh_token = None
    connection.access_token_expires_at = None
    connection.granted_scope = ""


def disconnect(db: Session, user: CurrentUser) -> str:
    lock_account(db, user.id)
    db.query(GoogleCalendarOAuthState).filter_by(user_id=user.id).delete()
    connection = db.get(GoogleCalendarConnection, user.id)
    if connection is None or not connection.encrypted_refresh_token:
        db.commit()
        return "already_disconnected"
    try:
        settings = GoogleOAuthSettings.from_env()
        refresh_token = settings.cipher.decrypt(connection.encrypted_refresh_token.encode()).decode()
        revoked = revoke_token(refresh_token)
    except (HTTPException, InvalidToken):
        revoked = False
    clear_credentials(connection)
    db.commit()
    return "confirmed" if revoked else "not_confirmed_remove_access_in_google"


def finish_authorization(db: Session, state: str, code: str | None, settings: GoogleOAuthSettings) -> str:
    digest = hashlib.sha256(state.encode()).hexdigest()
    user_id = db.scalar(select(GoogleCalendarOAuthState.user_id).where(
        GoogleCalendarOAuthState.state_hash == digest
    ))
    if user_id is None:
        return "invalid_state"

    # Serialize callback, restart and disconnect for this profile.
    lock_account(db, user_id)
    pending = db.get(GoogleCalendarOAuthState, digest)
    if pending is None:
        return "invalid_state"
    db.delete(pending)
    expires = pending.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        return "invalid_state"
    if not code:
        return "denied"
    try:
        verifier = settings.cipher.decrypt(pending.encrypted_code_verifier.encode()).decode()
    except InvalidToken:
        return "invalid_state"

    token = _exchange_code(code, verifier, settings)
    scope = token.get("scope")
    if not isinstance(scope, str) or CALENDAR_SCOPE not in scope.split():
        return "denied"
    identity = _google_identity(token["access_token"])
    google_email = identity["email"].strip().casefold()
    if google_email != pending.agenda_email or google_email != confirmed_agenda_email(db, user_id):
        return "email_mismatch"

    connection = db.get(GoogleCalendarConnection, user_id)
    refresh_token = token.get("refresh_token")
    if not isinstance(refresh_token, str) or not refresh_token:
        return "offline_access_unavailable"

    try:
        # Keep state consumption when the Google identity is already linked.
        with db.begin_nested():
            if connection is None:
                connection = GoogleCalendarConnection(user_id=user_id)
            elif connection.google_sub != identity["sub"]:
                if connection.encrypted_refresh_token:
                    return "different_google_account"
                connection.calendar_id = None
            connection.google_sub = identity["sub"]
            connection.google_email = google_email
            connection.granted_scope = scope
            _store_tokens(connection, token, refresh_token, settings)
            db.add(connection)
            db.flush()
    except IntegrityError:
        return "different_google_account"
    return "connected"


def create_authorization(db: Session, user: CurrentUser, settings: GoogleOAuthSettings) -> str:
    lock_account(db, user.id)
    user_id = user.id
    email = user.email.strip().casefold()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    now = datetime.now(timezone.utc)
    db.query(GoogleCalendarOAuthState).filter_by(user_id=user_id).delete(synchronize_session=False)
    db.add(GoogleCalendarOAuthState(
        state_hash=hashlib.sha256(state.encode("ascii")).hexdigest(),
        user_id=user_id,
        agenda_email=email.strip().casefold(),
        encrypted_code_verifier=settings.cipher.encrypt(verifier.encode()).decode(),
        expires_at=now + STATE_TTL,
    ))
    db.commit()
    query = urlencode({
        "client_id": settings.client_id,
        "redirect_uri": settings.redirect_uri,
        "response_type": "code",
        "response_mode": "form_post",
        "scope": f"openid email {CALENDAR_SCOPE}",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
        "login_hint": email,
    })
    return f"{AUTHORIZATION_ENDPOINT}?{query}"


def confirmed_agenda_email(db: Session, user_id: UUID) -> str | None:
    row = db.execute(text("""
        select email::text, email_confirmed_at
          from auth.users
         where id=:user_id
    """), {"user_id": user_id}).first()
    if row is None or row.email_confirmed_at is None or not row.email:
        return None
    return row.email.strip().casefold()


def _exchange_code(code: str, verifier: str, settings: GoogleOAuthSettings) -> dict:
    try:
        response = httpx.post(TOKEN_ENDPOINT, data={
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "code": code,
            "code_verifier": verifier,
            "redirect_uri": settings.redirect_uri,
            "grant_type": "authorization_code",
        }, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Não foi possível concluir a conexão Google") from None
    if response.status_code == 400:
        raise HTTPException(409, REAUTHORIZE)
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="O Google recusou a autorização")
    try:
        token = response.json()
        expires_in = int(token["expires_in"])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(status_code=502, detail="Resposta de autorização Google inválida") from None
    if (not isinstance(token.get("access_token"), str) or not token["access_token"]
            or expires_in < 1 or expires_in > 86400):
        raise HTTPException(status_code=502, detail="Resposta de autorização Google inválida")
    token["expires_in"] = expires_in
    return token


def _google_identity(access_token: str) -> dict:
    try:
        response = httpx.get(USERINFO_ENDPOINT, headers={"Authorization": f"Bearer {access_token}"}, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Não foi possível validar a conta Google") from None
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Não foi possível validar a conta Google")
    try:
        identity = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Resposta de identidade Google inválida") from None
    if (not isinstance(identity, dict) or not isinstance(identity.get("sub"), str)
            or not identity["sub"] or len(identity["sub"]) > 255
            or not isinstance(identity.get("email"), str)
            or identity.get("email_verified") is not True):
        raise HTTPException(status_code=403, detail="A conta Google precisa ter um e-mail verificado")
    return identity


def revoke_token(token: str) -> bool:
    try:
        response = httpx.post(REVOCATION_ENDPOINT, data={"token": token}, timeout=8.0)
    except httpx.RequestError:
        return False
    if response.status_code == 200:
        return True
    try:
        return response.status_code == 400 and response.json().get("error") == "invalid_token"
    except (ValueError, AttributeError):
        return False


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


def get_access_token(connection: GoogleCalendarConnection, settings: GoogleOAuthSettings) -> str:
    expires = connection.access_token_expires_at
    if not (expires and connection.encrypted_access_token and connection.encrypted_refresh_token):
        raise HTTPException(409, REAUTHORIZE)
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    try:
        if expires > datetime.now(timezone.utc) + TOKEN_REFRESH_WINDOW:
            return settings.cipher.decrypt(connection.encrypted_access_token.encode()).decode()
        refresh_token = settings.cipher.decrypt(connection.encrypted_refresh_token.encode()).decode()
    except InvalidToken:
        raise HTTPException(409, REAUTHORIZE) from None

    token = _refresh(refresh_token, settings)
    scope = token.get("scope")
    if isinstance(scope, str) and CALENDAR_SCOPE not in scope.split():
        raise HTTPException(409, REAUTHORIZE)
    return _store_tokens(connection, token, refresh_token, settings)
