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
from sqlalchemy.orm import Session

from src.database.models import GoogleCalendarConnection, GoogleCalendarOAuthState

AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"
REVOCATION_ENDPOINT = "https://oauth2.googleapis.com/revoke"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.app.created"
STATE_TTL = timedelta(minutes=10)
TOKEN_REFRESH_WINDOW = timedelta(seconds=60)


@dataclass(frozen=True)
class GoogleOAuthSettings:
    client_id: str
    client_secret: str
    redirect_uri: str
    frontend_redirect_uri: str
    encryption_key: bytes

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
            Fernet(key)
        except (UnicodeEncodeError, ValueError):
            raise HTTPException(status_code=503, detail="Chave de proteção Google inválida") from None
        return cls(
            client_id=values["client_id"],
            client_secret=values["client_secret"],
            redirect_uri=values["redirect_uri"],
            frontend_redirect_uri=values["frontend_redirect_uri"],
            encryption_key=key,
        )


def _safe_redirect(value: str) -> bool:
    from urllib.parse import urlsplit

    parsed = urlsplit(value)
    return bool(parsed.hostname and not parsed.username and not parsed.password and not parsed.fragment
                and (parsed.scheme == "https" or
                     (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"})))


def _fernet(settings: GoogleOAuthSettings) -> Fernet:
    return Fernet(settings.encryption_key)


def encrypt_secret(value: str, settings: GoogleOAuthSettings) -> str:
    return _fernet(settings).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str, settings: GoogleOAuthSettings) -> str:
    try:
        return _fernet(settings).decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeEncodeError, ValueError):
        raise HTTPException(status_code=503, detail="Credencial Google indisponível") from None


def create_authorization(db: Session, user_id: UUID, email: str, settings: GoogleOAuthSettings) -> str:
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    now = datetime.now(timezone.utc)
    db.query(GoogleCalendarOAuthState).filter(
        (GoogleCalendarOAuthState.expires_at < now)
        | (GoogleCalendarOAuthState.user_id == user_id)
    ).delete(synchronize_session=False)
    db.add(GoogleCalendarOAuthState(
        state_hash=hashlib.sha256(state.encode("ascii")).hexdigest(),
        user_id=user_id,
        agenda_email=email.strip().casefold(),
        encrypted_code_verifier=encrypt_secret(verifier, settings),
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
        "include_granted_scopes": "true",
        "prompt": "consent",
        "login_hint": email,
    })
    return f"{AUTHORIZATION_ENDPOINT}?{query}"


def _consume_state(db: Session, state: str, settings: GoogleOAuthSettings) -> tuple[UUID, str, str] | None:
    if len(state) < 32 or len(state) > 128:
        return None
    digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
    row = db.scalar(select(GoogleCalendarOAuthState).where(
        GoogleCalendarOAuthState.state_hash == digest
    ).with_for_update())
    if row is None:
        return None
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        db.delete(row)
        db.commit()
        return None
    try:
        verifier = decrypt_secret(row.encrypted_code_verifier, settings)
    except HTTPException:
        db.delete(row)
        db.commit()
        return None
    result = (row.user_id, row.agenda_email, verifier)
    db.delete(row)
    db.commit()
    return result


def cancel_authorization(db: Session, state: str, settings: GoogleOAuthSettings) -> None:
    _consume_state(db, state, settings)


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
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="O Google recusou a autorização")
    try:
        token = response.json()
        expires_in = int(token["expires_in"])
    except (ValueError, TypeError, KeyError):
        raise HTTPException(status_code=502, detail="Resposta de autorização Google inválida") from None
    scopes = set(str(token.get("scope", "")).split())
    if (not isinstance(token.get("access_token"), str) or not token["access_token"]
            or expires_in < 1 or expires_in > 86400 or CALENDAR_SCOPE not in scopes):
        raise HTTPException(status_code=502, detail="O Google não concedeu o acesso de calendário solicitado")
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
    return response.status_code == 200


def finish_authorization(db: Session, state: str, code: str | None,
                         settings: GoogleOAuthSettings) -> str:
    consumed = _consume_state(db, state, settings)
    if consumed is None:
        return "invalid_state"
    user_id, expected_email, verifier = consumed
    current_email = confirmed_agenda_email(db, user_id)
    if current_email is None or current_email != expected_email:
        return "agenda_email_unavailable"

    token = _exchange_code(code or "", verifier, settings)
    try:
        identity = _google_identity(token["access_token"])
    except HTTPException:
        revoke_token(token.get("refresh_token") or token["access_token"])
        raise
    google_email = identity["email"].strip().casefold()
    if google_email != expected_email:
        revoke_token(token.get("refresh_token") or token["access_token"])
        return "email_mismatch"

    existing = db.get(GoogleCalendarConnection, user_id)
    if existing and existing.google_sub != identity["sub"]:
        revoke_token(token.get("refresh_token") or token["access_token"])
        return "different_google_account"
    refresh_token = token.get("refresh_token")
    if not refresh_token and existing and existing.google_sub == identity["sub"]:
        refresh_token = decrypt_secret(existing.encrypted_refresh_token, settings)
    if not refresh_token:
        revoke_token(token["access_token"])
        return "offline_access_unavailable"

    now = datetime.now(timezone.utc)
    connection = existing or GoogleCalendarConnection(user_id=user_id)
    connection.google_sub = identity["sub"]
    connection.google_email = google_email
    connection.encrypted_access_token = encrypt_secret(token["access_token"], settings)
    connection.encrypted_refresh_token = encrypt_secret(refresh_token, settings)
    connection.access_token_expires_at = now + timedelta(seconds=token["expires_in"])
    connection.granted_scope = token["scope"]
    db.add(connection)
    db.commit()
    return "connected"


def get_access_token(db: Session, user_id: UUID, settings: GoogleOAuthSettings) -> str:
    connection = db.scalar(select(GoogleCalendarConnection).where(
        GoogleCalendarConnection.user_id == user_id
    ).with_for_update())
    if connection is None:
        raise HTTPException(status_code=409, detail="Conecte novamente sua conta Google")
    expires_at = connection.access_token_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at > datetime.now(timezone.utc) + TOKEN_REFRESH_WINDOW:
        return decrypt_secret(connection.encrypted_access_token, settings)
    refresh_token = decrypt_secret(connection.encrypted_refresh_token, settings)
    try:
        response = httpx.post(TOKEN_ENDPOINT, data={
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }, timeout=10.0)
    except httpx.RequestError:
        raise HTTPException(status_code=503, detail="Não foi possível renovar a conexão Google") from None
    if response.status_code != 200:
        try:
            provider_error = response.json().get("error")
        except (ValueError, AttributeError):
            provider_error = None
        if response.status_code == 400 and provider_error == "invalid_grant":
            db.delete(connection)
            db.commit()
            raise HTTPException(status_code=409, detail="Conecte novamente sua conta Google")
        raise HTTPException(status_code=503, detail="Não foi possível renovar a conexão Google")
    try:
        token = response.json()
        expires_in = int(token["expires_in"])
        access_token = token["access_token"]
    except (ValueError, TypeError, KeyError):
        raise HTTPException(status_code=502, detail="Resposta de renovação Google inválida") from None
    if not isinstance(access_token, str) or not access_token or not 1 <= expires_in <= 86400:
        raise HTTPException(status_code=502, detail="Resposta de renovação Google inválida")
    connection.encrypted_access_token = encrypt_secret(access_token, settings)
    if isinstance(token.get("refresh_token"), str) and token["refresh_token"]:
        connection.encrypted_refresh_token = encrypt_secret(token["refresh_token"], settings)
    connection.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    db.add(connection)
    db.commit()
    return access_token
