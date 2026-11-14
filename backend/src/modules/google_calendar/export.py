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
    GoogleOAuthSettings, REAUTHORIZE, get_access_token, get_connection, lock_account,
)

CALENDAR_API = "https://www.googleapis.com/calendar/v3"
SAO_PAULO = ZoneInfo("America/Sao_Paulo")
# The current event model stores a start time only.
DEFAULT_DURATION = timedelta(hours=1)
PENDING_CALENDAR = "creation-pending"


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


def _calendar_id(db: Session, client: httpx.Client, connection: GoogleCalendarConnection, token: str) -> str:
    pending_message = "Não foi possível confirmar a criação da agenda Agenda UnB. Verifique o Google Agenda antes de continuar."
    if connection.calendar_id == PENDING_CALENDAR:
        raise HTTPException(409, pending_message)
    if connection.calendar_id:
        return connection.calendar_id

    # A second request can see this marker while Google is creating the calendar.
    connection.calendar_id = PENDING_CALENDAR
    db.commit()
    try:
        response = _post(client, "calendars", token, {"summary": "Agenda UnB", "timeZone": SAO_PAULO.key})
        if response.status_code < 500 and not response.is_success:
            connection.calendar_id = None
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
        raise HTTPException(503, pending_message)
    connection.calendar_id = calendar_id
    return calendar_id


def export_events(db: Session, user: CurrentUser, items: list[ExportItem]) -> list[ExportResult]:
    if len({(item.kind, item.id) for item in items}) != len(items):
        raise HTTPException(422, "Selecione cada evento uma única vez.")
    events = _load_events(db, user, items)
    settings = GoogleOAuthSettings.from_env()
    lock_account(db, user)
    connection = get_connection(db, user)
    if connection is None:
        raise HTTPException(409, REAUTHORIZE)

    try:
        token = get_access_token(connection, settings)
    except HTTPException as exc:
        if exc.status_code == 409:
            connection.granted_scope = ""
            db.commit()
        raise

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
                elif response.status_code == 401:
                    lock_account(db, user)
                    current = get_connection(db, user)
                    if current and current.encrypted_access_token == encrypted_access_token:
                        current.granted_scope = ""
                    db.commit()
                    raise HTTPException(409, REAUTHORIZE)
                else:
                    status = "failed"
            except httpx.RequestError:
                status = "failed"
            results.append(ExportResult(id=item.id, kind=item.kind, status=status))
    return results
