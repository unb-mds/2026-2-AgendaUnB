from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, SecretStr
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.google_calendar.export import ExportRequest, ExportResult, export_events
from src.modules.google_calendar.service import get_connection, save_login_grant

router = APIRouter(prefix="/me/google-calendar", tags=["google-calendar"])


class LoginGrant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: SecretStr = Field(min_length=1, max_length=4096)


class ConnectionResponse(BaseModel):
    connected: bool


def google_user(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.google_sub or not user.email or not user.email_confirmed:
        raise HTTPException(403, "A exportação requer login com Google.")
    return user


@router.post("/connection", status_code=204)
def store_login_grant(payload: LoginGrant, user: CurrentUser = Depends(google_user),
                      db: Session = Depends(get_db)) -> Response:
    save_login_grant(db, user, payload.refresh_token.get_secret_value())
    return Response(status_code=204, headers={"Cache-Control": "no-store"})


@router.get("/connection", response_model=ConnectionResponse)
def connection_status(response: Response, user: CurrentUser = Depends(google_user),
                      db: Session = Depends(get_db)) -> ConnectionResponse:
    response.headers["Cache-Control"] = "no-store"
    return ConnectionResponse(connected=get_connection(db, user) is not None)


@router.post("/exports", response_model=list[ExportResult])
def export_selected(payload: ExportRequest, response: Response, user: CurrentUser = Depends(google_user),
                    db: Session = Depends(get_db)) -> list[ExportResult]:
    response.headers["Cache-Control"] = "no-store"
    return export_events(db, user, payload.events)
