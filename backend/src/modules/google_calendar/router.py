from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import GoogleCalendarConnection
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.google_calendar.service import (
    GoogleOAuthSettings,
    cancel_authorization,
    create_authorization,
    decrypt_secret,
    finish_authorization,
    revoke_token,
)

router = APIRouter(prefix="/me/google-calendar", tags=["google-calendar"])


class AuthorizationResponse(BaseModel):
    authorization_url: str
    expires_in_seconds: int = 600


class ConnectionResponse(BaseModel):
    connected: bool
    google_email: str | None = None
    calendar_id: str | None = None
    scope: str | None = None


class DisconnectResponse(BaseModel):
    disconnected: bool
    revocation: str


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _return_to_frontend(settings: GoogleOAuthSettings, result: str) -> RedirectResponse:
    parsed = urlsplit(settings.frontend_redirect_uri)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["google_calendar"] = result
    location = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))
    return RedirectResponse(location, status_code=303, headers={"Cache-Control": "no-store"})


@router.post("/authorization", response_model=AuthorizationResponse)
def begin_authorization(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AuthorizationResponse:
    _no_store(response)
    if not user.email or not user.email_confirmed:
        raise HTTPException(status_code=403, detail="Confirme seu e-mail antes de conectar o Google Calendar")
    settings = GoogleOAuthSettings.from_env()
    authorization_url = create_authorization(db, user.id, user.email, settings)
    return AuthorizationResponse(authorization_url=authorization_url)


@router.post("/callback", include_in_schema=True)
def authorization_callback(
    response: Response,
    state: str = Form(..., min_length=32, max_length=128),
    code: str | None = Form(None, min_length=1, max_length=4096),
    error: str | None = Form(None, max_length=100),
    db: Session = Depends(get_db),
):
    settings = GoogleOAuthSettings.from_env()
    _no_store(response)
    if error:
        cancel_authorization(db, state, settings)
        return _return_to_frontend(settings, "denied")
    if not code:
        cancel_authorization(db, state, settings)
        return _return_to_frontend(settings, "failed")
    try:
        result = finish_authorization(db, state, code, settings)
    except HTTPException as exc:
        # Do not reflect provider diagnostics, tokens or authorization codes to the browser.
        result = "failed" if exc.status_code >= 500 else "denied"
    return _return_to_frontend(settings, result)


@router.get("/connection", response_model=ConnectionResponse)
def get_connection(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConnectionResponse:
    _no_store(response)
    connection = db.get(GoogleCalendarConnection, user.id)
    if connection is None:
        return ConnectionResponse(connected=False)
    return ConnectionResponse(
        connected=True,
        google_email=connection.google_email,
        calendar_id=connection.calendar_id,
        scope=connection.granted_scope,
    )


@router.delete("/connection", response_model=DisconnectResponse)
def disconnect(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DisconnectResponse:
    _no_store(response)
    connection = db.get(GoogleCalendarConnection, user.id)
    if connection is None:
        return DisconnectResponse(disconnected=True, revocation="already_disconnected")
    revoked = False
    try:
        settings = GoogleOAuthSettings.from_env()
        refresh_token = decrypt_secret(connection.encrypted_refresh_token, settings)
        revoked = revoke_token(refresh_token)
    except HTTPException:
        # Remove local credentials even if the provider cannot be reached or
        # the deployment key is unavailable; report that remote revocation
        # could not be confirmed so the user can revoke access in Google.
        pass
    db.delete(connection)
    db.commit()
    return DisconnectResponse(
        disconnected=True,
        revocation="confirmed" if revoked else "not_confirmed_remove_access_in_google",
    )
