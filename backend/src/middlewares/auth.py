import json
import os
from base64 import urlsafe_b64decode
from binascii import Error as Base64Error
from dataclasses import dataclass, field
from uuid import UUID

import httpx
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import Profile

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    role: str
    access_token: str | None = field(default=None, repr=False, compare=False)
    email: str | None = field(default=None, repr=False, compare=False)
    email_confirmed: bool = False
    google_sub: str | None = field(default=None, repr=False)


def _google_session_identity(token: str, auth_user: dict) -> str | None:
    # The exact bearer has already been validated by the project's Supabase Auth.
    try:
        payload = token.split(".")[1]
        claims = json.loads(urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        methods = claims.get("amr") or []
        if not any(isinstance(method, dict) and method.get("method") == "oauth" for method in methods):
            return None
    except (ValueError, TypeError, IndexError, AttributeError, Base64Error):
        return None
    # Google is the only social provider configured for the Agenda UnB project.
    return next((
        identity["identity_data"]["sub"] for identity in auth_user.get("identities") or []
        if identity.get("provider") == "google"
        and isinstance((identity.get("identity_data") or {}).get("sub"), str)
        and identity["identity_data"]["sub"]
    ), None)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")
    if not supabase_url or not supabase_anon_key:
        raise HTTPException(
            status_code=503,
            detail="Autenticação Supabase não configurada no backend",
        )

    try:
        response = httpx.get(
            f"{supabase_url}/auth/v1/user",
            headers={
                "apikey": supabase_anon_key,
                "Authorization": f"Bearer {credentials.credentials}",
            },
            timeout=5.0,
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail="Não foi possível validar a sessão com o Supabase",
        ) from exc

    if response.status_code in (401, 403):
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    if response.status_code != 200:
        raise HTTPException(status_code=503, detail="Falha ao validar a sessão")

    try:
        auth_user = response.json()
        user_id = UUID(auth_user["id"])
        email = auth_user.get("email")
        email_confirmed = bool(auth_user.get("email_confirmed_at"))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Resposta de autenticação inválida") from exc

    if not isinstance(email, str) or not email.strip() or not email_confirmed:
        raise HTTPException(status_code=403, detail="Confirme seu e-mail antes de usar este recurso")

    role = db.scalar(select(Profile.papel).where(Profile.id == user_id))
    if role is None:
        raise HTTPException(status_code=403, detail="Perfil da aplicação não encontrado")

    return CurrentUser(
        id=user_id,
        role=role,
        access_token=credentials.credentials,
        email=email,
        email_confirmed=email_confirmed,
        google_sub=_google_session_identity(credentials.credentials, auth_user),
    )


def require_event_manager(
    current_user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    if current_user.role not in {"professor", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="Apenas professores e administradores podem gerenciar eventos públicos",
        )
    return current_user
