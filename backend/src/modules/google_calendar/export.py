"""Exportação explícita para uma agenda secundária criada pelo Agenda UnB."""

from datetime import timedelta, timezone
from hashlib import sha256
from typing import Literal
from urllib.parse import quote
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import GoogleCalendarConnection, PersonalEvent, PublicEvent, SavedPublicEvent
from src.middlewares.auth import CurrentUser
from src.modules.google_calendar.service import (
    GoogleOAuthSettings, REAUTHORIZE, clear_credentials, get_access_token, get_connection, lock_account,
)

CALENDAR_API = "https://www.googleapis.com/calendar/v3"
SAO_PAULO = ZoneInfo("America/Sao_Paulo")
# The current event model stores a start time only.
DEFAULT_DURATION = timedelta(hours=1)
PENDING_CALENDAR = "creation-pending"
CALENDAR_NAME = "Agenda UnB"
RECOVER_DESTINATION = "Confirme o ID da agenda Agenda UnB antes de tentar exportar novamente."


class ExportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    kind: Literal["personal", "saved"]


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[ExportItem] = Field(min_length=1, max_length=20)


class ExportResult(ExportItem):
    status: Literal["exported", "already_exported", "failed"]


def _load_events(db: Session, user: CurrentUser, items: list[ExportItem]) -> dict[tuple[str, UUID], PersonalEvent | PublicEvent]:
    ids = {item.id for item in items}
    personal = db.scalars(select(PersonalEvent).where(
        PersonalEvent.user_id == user.id, PersonalEvent.id.in_(ids)
    )).all()
    saved = db.scalars(select(PublicEvent).join(SavedPublicEvent).where(
        SavedPublicEvent.user_id == user.id, PublicEvent.status == "aprovado", PublicEvent.id.in_(ids)
    )).all()
    by_key = {(kind, event.id): event for kind, events in (("personal", personal), ("saved", saved)) for event in events}
    if any((item.kind, item.id) not in by_key for item in items):
        raise HTTPException(404, "Um ou mais eventos selecionados não estão na sua agenda.")
    return by_key


def _event_payload(user: CurrentUser, item: ExportItem, event: PersonalEvent | PublicEvent) -> dict:
    start = event.starts_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    start = start.astimezone(SAO_PAULO)
    return {
        "id": sha256(f"{user.id}:{item.kind}:{item.id}".encode()).hexdigest(),
        "summary": event.title,
        "start": {"dateTime": start.isoformat(), "timeZone": SAO_PAULO.key},
        "end": {"dateTime": (start + DEFAULT_DURATION).isoformat(), "timeZone": SAO_PAULO.key},
    }


def _post(client: httpx.Client, path: str, token: str, payload: dict) -> httpx.Response:
    return client.post(f"{CALENDAR_API}/{path}", headers={"Authorization": f"Bearer {token}"}, json=payload)


def calendar_recovery_pending(connection: GoogleCalendarConnection | None) -> bool:
    return connection is not None and connection.calendar_id == PENDING_CALENDAR


def _access_token(db: Session, connection: GoogleCalendarConnection, settings: GoogleOAuthSettings) -> str:
    try:
        return get_access_token(connection, settings)
    except HTTPException as exc:
        if exc.status_code == 409:
            clear_credentials(connection)
            db.commit()
        raise


def recover_calendar(db: Session, user: CurrentUser, calendar_id: str | None) -> None:
    settings = GoogleOAuthSettings.from_env()
    lock_account(db, user.id)
    connection = get_connection(db, user)
    if connection is None:
        raise HTTPException(409, REAUTHORIZE)
    if not calendar_recovery_pending(connection):
        if connection.calendar_id == calendar_id:
            return
        raise HTTPException(409, "Nenhuma agenda precisa de recuperação.")
    if calendar_id is None:
        connection.calendar_id = None
        db.commit()
        return
    if calendar_id.casefold() == "primary":
        raise HTTPException(422, "Informe o ID da agenda secundária Agenda UnB.")

    token = _access_token(db, connection, settings)
    try:
        response = httpx.get(f"{CALENDAR_API}/calendars/{quote(calendar_id, safe='')}",
                             headers={"Authorization": f"Bearer {token}"}, timeout=8)
        if response.status_code == 401:
            clear_credentials(connection)
            db.commit()
            raise HTTPException(409, REAUTHORIZE)
        if response.status_code in (403, 404, 410):
            raise HTTPException(422, "O Google não encontrou uma agenda Agenda UnB acessível por esta conexão.")
        if not response.is_success:
            raise HTTPException(503, "Não foi possível consultar a agenda no Google.")
        data = response.json()
    except (httpx.RequestError, ValueError):
        raise HTTPException(503, "Não foi possível consultar a agenda no Google.") from None
    if not isinstance(data, dict) or data.get("id") != calendar_id or data.get("summary") != CALENDAR_NAME:
        raise HTTPException(422, "Informe o ID da agenda secundária Agenda UnB.")
    connection.calendar_id = calendar_id
    db.commit()


def _calendar_id(db: Session, client: httpx.Client, connection: GoogleCalendarConnection, token: str) -> str:
    if calendar_recovery_pending(connection):
        raise HTTPException(409, RECOVER_DESTINATION)
    if connection.calendar_id:
        return connection.calendar_id

    # Keep the profile lock until the result is known, including across a disconnect.
    try:
        response = _post(client, "calendars", token, {"summary": CALENDAR_NAME, "timeZone": SAO_PAULO.key})
        if 400 <= response.status_code < 500:
            if response.status_code == 401:
                clear_credentials(connection)
            db.commit()
            if response.status_code in (401, 403):
                raise HTTPException(409, REAUTHORIZE)
            if response.status_code == 429:
                raise HTTPException(429, "O Google Agenda atingiu o limite. Tente novamente em instantes.")
            raise HTTPException(502, "Não foi possível criar a agenda no Google.")
        calendar_id = response.json().get("id") if response.is_success else None
    except (httpx.RequestError, ValueError, AttributeError):
        calendar_id = None
    if not isinstance(calendar_id, str) or not calendar_id:
        connection.calendar_id = PENDING_CALENDAR
        db.commit()
        raise HTTPException(503, RECOVER_DESTINATION)
    connection.calendar_id = calendar_id
    return calendar_id


def export_events(db: Session, user: CurrentUser, items: list[ExportItem]) -> list[ExportResult]:
    if len({(item.kind, item.id) for item in items}) != len(items):
        raise HTTPException(422, "Selecione cada evento uma única vez.")
    events = _load_events(db, user, items)
    settings = GoogleOAuthSettings.from_env()
    lock_account(db, user.id)
    connection = get_connection(db, user)
    if connection is None:
        raise HTTPException(409, REAUTHORIZE)

    token = _access_token(db, connection, settings)

    with httpx.Client(timeout=8) as client:
        # Materialize the payloads before a commit expires the loaded ORM rows.
        payloads = [_event_payload(user, item, events[item.kind, item.id]) for item in items]
        destination = _calendar_id(db, client, connection, token)
        path = f"calendars/{quote(destination, safe='')}/events"
        encrypted_access_token = connection.encrypted_access_token
        db.commit()
        results = []
        for item, payload in zip(items, payloads, strict=True):
            try:
                response = _post(client, path, token, payload)
                if response.is_success:
                    status = "exported"
                elif response.status_code == 409:
                    status = "already_exported"
                elif response.status_code in (401, 404, 410):
                    lock_account(db, user.id)
                    current = get_connection(db, user)
                    if (current and current.encrypted_access_token == encrypted_access_token
                            and current.calendar_id == destination):
                        if response.status_code == 401:
                            clear_credentials(current)
                        else:
                            current.calendar_id = PENDING_CALENDAR
                    db.commit()
                    raise HTTPException(409, REAUTHORIZE if response.status_code == 401 else RECOVER_DESTINATION)
                else:
                    status = "failed"
            except httpx.RequestError:
                status = "failed"
            results.append(ExportResult(id=item.id, kind=item.kind, status=status))
    return results
