from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, Depends, Form, HTTPException, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.google_calendar.export import (
    ExportRequest, ExportResult, calendar_recovery_pending, export_events, recover_calendar,
)
from src.modules.google_calendar.service import (
    GoogleOAuthSettings, create_authorization, disconnect, finish_authorization, get_connection,
)

router = APIRouter(prefix="/me/google-calendar", tags=["google-calendar"])


class AuthorizationResponse(BaseModel):
    authorization_url: str
    expires_in_seconds: int = 600


class ConnectionResponse(BaseModel):
    connected: bool
    recovery_required: bool = False


class DisconnectResponse(BaseModel):
    disconnected: bool
    revocation: str


class CalendarRecovery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    calendar_id: str | None = Field(min_length=3, max_length=512, pattern=r"^[a-zA-Z0-9_.+@-]+$")


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _return_to_frontend(settings: GoogleOAuthSettings, result: str) -> RedirectResponse:
    parsed = urlsplit(settings.frontend_redirect_uri)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["google_calendar"] = result
    location = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))
    return RedirectResponse(location, status_code=303, headers={"Cache-Control": "no-store", "Referrer-Policy": "no-referrer"})


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
    authorization_url = create_authorization(db, user, settings)
    return AuthorizationResponse(authorization_url=authorization_url)


@router.post("/callback", response_class=RedirectResponse)
def authorization_callback(
    state: str = Form(..., min_length=32, max_length=128),
    code: str | None = Form(None, min_length=1, max_length=4096),
    error: str | None = Form(None, max_length=100),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    settings = GoogleOAuthSettings.from_env()
    try:
        result = finish_authorization(db, state, None if error else code, settings)
    except HTTPException as exc:
        result = {403: "denied", 409: "invalid_state"}.get(exc.status_code, "failed")
    db.commit()
    return _return_to_frontend(settings, result)


@router.get("/connection", response_model=ConnectionResponse)
def connection_status(response: Response, user: CurrentUser = Depends(get_current_user),
                      db: Session = Depends(get_db)) -> ConnectionResponse:
    _no_store(response)
    connection = get_connection(db, user)
    return ConnectionResponse(connected=connection is not None, recovery_required=calendar_recovery_pending(connection))


@router.delete("/connection", response_model=DisconnectResponse)
def disconnect_calendar(response: Response, user: CurrentUser = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> DisconnectResponse:
    _no_store(response)
    return DisconnectResponse(disconnected=True, revocation=disconnect(db, user))


@router.put("/destination", status_code=204)
def recover_destination(payload: CalendarRecovery, user: CurrentUser = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> Response:
    recover_calendar(db, user, payload.calendar_id)
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.post("/exports", response_model=list[ExportResult])
def export_selected(payload: ExportRequest, response: Response, user: CurrentUser = Depends(get_current_user),
                    db: Session = Depends(get_db)) -> list[ExportResult]:
    _no_store(response)
    return export_events(db, user, payload.events)
