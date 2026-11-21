"""Exportação explícita para uma agenda secundária criada pelo Agenda UnB."""

from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
import json
import time as time_module
from typing import Callable, Literal
from urllib.parse import quote
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from src.database.models import (
    GoogleCalendarConnection,
    GoogleCalendarEventExport,
    PersonalEvent,
    PublicEvent,
    SavedPublicEvent,
)
from src.middlewares.auth import CurrentUser
from src.modules.google_calendar.service import (
    GoogleOAuthSettings,
    REAUTHORIZE,
    clear_credentials,
    get_access_token,
    get_connection,
    lock_account,
)

CALENDAR_API = "https://www.googleapis.com/calendar/v3"
SAO_PAULO = ZoneInfo("America/Sao_Paulo")
DEFAULT_DURATION = timedelta(hours=1)
PENDING_CALENDAR = "creation-pending"
CALENDAR_NAME = "Agenda UnB"
RECOVER_DESTINATION = "Confirme o ID da agenda Agenda UnB antes de tentar exportar novamente."
MAX_BACKOFF_SECONDS = 2.0
DEFAULT_BACKOFF_SECONDS = 0.5
RATE_LIMIT_REASONS = {"rateLimitExceeded", "userRateLimitExceeded", "quotaExceeded"}


class ExportItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    kind: Literal["personal", "saved"]


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    events: list[ExportItem] = Field(min_length=1, max_length=20)
    allow_managed_field_updates: bool = False
    include_description: bool = False
    start_date: date | None = None
    end_date: date | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "ExportRequest":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("A data final do período deve ser igual ou posterior à data inicial.")
        return self


class ExportResult(ExportItem):
    status: Literal["exported", "updated", "already_exported", "failed"]


class ExportPreviewItem(ExportItem):
    action: Literal["create", "update", "unchanged"]


class ExportPreviewResponse(BaseModel):
    requires_overwrite_confirmation: bool
    items: list[ExportPreviewItem]


def _load_events(
    db: Session, user: CurrentUser, items: list[ExportItem]
) -> dict[tuple[str, UUID], PersonalEvent | PublicEvent]:
    ids = {item.id for item in items}
    personal = db.scalars(
        select(PersonalEvent).where(PersonalEvent.user_id == user.id, PersonalEvent.id.in_(ids))
    ).all()
    saved = db.scalars(
        select(PublicEvent)
        .join(SavedPublicEvent)
        .where(
            SavedPublicEvent.user_id == user.id,
            PublicEvent.status == "aprovado",
            PublicEvent.id.in_(ids),
        )
    ).all()
    by_key = {
        (kind, event.id): event
        for kind, events in (("personal", personal), ("saved", saved))
        for event in events
    }
    if any((item.kind, item.id) not in by_key for item in items):
        raise HTTPException(404, "Um ou mais eventos selecionados não estão na sua agenda.")
    return by_key


def _event_intersects_period(
    event: PersonalEvent | PublicEvent, start_date: date | None, end_date: date | None
) -> bool:
    if start_date is None and end_date is None:
        return True
    if getattr(event, "all_day", False) and event.start_date is not None:
        ev_start = event.start_date
        ev_end_exclusive = (
            event.end_date
            if (event.end_date is not None and event.end_date > event.start_date)
            else (event.start_date + timedelta(days=1))
        )
        if start_date is not None and ev_end_exclusive <= start_date:
            return False
        if end_date is not None and ev_start > end_date:
            return False
        return True

    start = event.starts_at
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    start_sp = start.astimezone(SAO_PAULO)
    end = getattr(event, "ends_at", None)
    if end is not None:
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        end_sp = end.astimezone(SAO_PAULO) if end > start else (start_sp + DEFAULT_DURATION)
    else:
        end_sp = start_sp + DEFAULT_DURATION

    if start_date is not None:
        window_start = datetime.combine(start_date, time.min, tzinfo=SAO_PAULO)
        if end_sp <= window_start:
            return False
    if end_date is not None:
        window_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=SAO_PAULO)
        if start_sp >= window_end:
            return False
    return True


def _event_payload(
    user: CurrentUser,
    item: ExportItem,
    event: PersonalEvent | PublicEvent,
    *,
    include_description: bool = False,
) -> dict:
    event_id = sha256(f"{user.id}:{item.kind}:{item.id}".encode()).hexdigest()
    if getattr(event, "all_day", False) and event.start_date is not None:
        end_civil = (
            event.end_date
            if (event.end_date is not None and event.end_date > event.start_date)
            else (event.start_date + timedelta(days=1))
        )
        start_block = {"date": event.start_date.isoformat()}
        end_block = {"date": end_civil.isoformat()}
    else:
        start = event.starts_at
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        start_sp = start.astimezone(SAO_PAULO)
        end = getattr(event, "ends_at", None)
        if end is not None:
            if end.tzinfo is None:
                end = end.replace(tzinfo=timezone.utc)
            end_sp = end.astimezone(SAO_PAULO) if end > start else (start_sp + DEFAULT_DURATION)
        else:
            end_sp = start_sp + DEFAULT_DURATION
        start_block = {"dateTime": start_sp.isoformat(), "timeZone": SAO_PAULO.key}
        end_block = {"dateTime": end_sp.isoformat(), "timeZone": SAO_PAULO.key}

    payload: dict = {
        "id": event_id,
        "summary": event.title,
        "start": start_block,
        "end": end_block,
    }
    location = getattr(event, "location", None)
    if isinstance(location, str) and location.strip():
        payload["location"] = location.strip()
    description = getattr(event, "description", None)
    if include_description and isinstance(description, str) and description.strip():
        payload["description"] = description.strip()
    return payload


def _payload_version(payload: dict) -> str:
    managed = {
        "summary": payload.get("summary"),
        "description": payload.get("description"),
        "location": payload.get("location"),
        "start": payload.get("start"),
        "end": payload.get("end"),
    }
    canonical = json.dumps(managed, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(canonical.encode("utf-8")).hexdigest()


def _post(client: httpx.Client, path: str, token: str, payload: dict) -> httpx.Response:
    return client.post(
        f"{CALENDAR_API}/{path}", headers={"Authorization": f"Bearer {token}"}, json=payload
    )


def _put(client: httpx.Client, path: str, token: str, payload: dict) -> httpx.Response:
    return client.put(
        f"{CALENDAR_API}/{path}", headers={"Authorization": f"Bearer {token}"}, json=payload
    )


def _is_rate_limited(response: httpx.Response) -> bool:
    if response.status_code == 429:
        return True
    if response.status_code != 403:
        return False
    try:
        body = response.json()
        errors = ((body.get("error") or {}).get("errors")) or []
        return any(
            isinstance(entry, dict) and entry.get("reason") in RATE_LIMIT_REASONS
            for entry in errors
        )
    except (ValueError, AttributeError, TypeError):
        return False


def _retry_delay_seconds(response: httpx.Response) -> float:
    raw = response.headers.get("Retry-After")
    if raw:
        try:
            parsed = float(raw.strip())
            if parsed >= 0:
                return min(parsed, MAX_BACKOFF_SECONDS)
        except ValueError:
            pass
    return DEFAULT_BACKOFF_SECONDS


def _call_with_backoff(
    fn: Callable[[httpx.Client, str, str, dict], httpx.Response],
    client: httpx.Client,
    path: str,
    token: str,
    payload: dict,
) -> httpx.Response:
    response = fn(client, path, token, payload)
    if _is_rate_limited(response):
        time_module.sleep(_retry_delay_seconds(response))
        response = fn(client, path, token, payload)
    return response


def calendar_recovery_pending(connection: GoogleCalendarConnection | None) -> bool:
    return connection is not None and connection.calendar_id == PENDING_CALENDAR


def _access_token(db: Session, connection: GoogleCalendarConnection, settings: GoogleOAuthSettings) -> str:
    try:
        return get_access_token(connection, settings)
    except HTTPException as exc:
        if exc.status_code == 409:
            clear_credentials(db, connection)
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
        db.execute(
            delete(GoogleCalendarEventExport).where(GoogleCalendarEventExport.user_id == user.id)
        )
        db.commit()
        return
    if calendar_id.casefold() == "primary":
        raise HTTPException(422, "Informe o ID da agenda secundária Agenda UnB.")

    token = _access_token(db, connection, settings)
    try:
        response = httpx.get(
            f"{CALENDAR_API}/calendars/{quote(calendar_id, safe='')}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8,
        )
        if response.status_code == 401:
            clear_credentials(db, connection)
            db.commit()
            raise HTTPException(409, REAUTHORIZE)
        if response.status_code in (403, 404, 410):
            raise HTTPException(
                422, "O Google não encontrou uma agenda Agenda UnB acessível por esta conexão."
            )
        if not response.is_success:
            raise HTTPException(503, "Não foi possível consultar a agenda no Google.")
        data = response.json()
    except (httpx.RequestError, ValueError):
        raise HTTPException(503, "Não foi possível consultar a agenda no Google.") from None
    if (
        not isinstance(data, dict)
        or data.get("id") != calendar_id
        or data.get("summary") != CALENDAR_NAME
    ):
        raise HTTPException(422, "Informe o ID da agenda secundária Agenda UnB.")
    connection.calendar_id = calendar_id
    db.commit()


def _calendar_id(
    db: Session, client: httpx.Client, connection: GoogleCalendarConnection, token: str
) -> str:
    if calendar_recovery_pending(connection):
        raise HTTPException(409, RECOVER_DESTINATION)
    if connection.calendar_id:
        return connection.calendar_id

    # Keep the profile lock until the result is known, including across a disconnect.
    try:
        response = _call_with_backoff(
            _post, client, "calendars", token, {"summary": CALENDAR_NAME, "timeZone": SAO_PAULO.key}
        )
        if 400 <= response.status_code < 500:
            is_rate_limit = _is_rate_limited(response)
            if response.status_code == 401 or (response.status_code == 403 and not is_rate_limit):
                clear_credentials(db, connection)
            db.commit()
            if is_rate_limit:
                raise HTTPException(
                    429, "O Google Agenda atingiu o limite. Tente novamente em instantes."
                )
            if response.status_code in (401, 403):
                raise HTTPException(409, REAUTHORIZE)
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


def _validate_selection_and_load(
    db: Session,
    user: CurrentUser,
    items: list[ExportItem],
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[tuple[str, UUID], PersonalEvent | PublicEvent]:
    if len({(item.kind, item.id) for item in items}) != len(items):
        raise HTTPException(422, "Selecione cada evento uma única vez.")
    events = _load_events(db, user, items)
    if start_date is not None or end_date is not None:
        for item in items:
            if not _event_intersects_period(events[item.kind, item.id], start_date, end_date):
                raise HTTPException(
                    422, "Um ou mais eventos selecionados estão fora do período informado."
                )
    return events


def preview_export(
    db: Session,
    user: CurrentUser,
    items: list[ExportItem],
    *,
    include_description: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
) -> ExportPreviewResponse:
    events = _validate_selection_and_load(db, user, items, start_date, end_date)
    connection = get_connection(db, user)
    if connection is None:
        raise HTTPException(409, REAUTHORIZE)
    if calendar_recovery_pending(connection):
        raise HTTPException(409, RECOVER_DESTINATION)

    destination = connection.calendar_id
    existing_rows = (
        db.scalars(
            select(GoogleCalendarEventExport).where(GoogleCalendarEventExport.user_id == user.id)
        ).all()
        if destination
        else []
    )
    by_key = {(row.event_kind, row.local_event_id): row for row in existing_rows}

    preview_items: list[ExportPreviewItem] = []
    for item in items:
        payload = _event_payload(
            user, item, events[item.kind, item.id], include_description=include_description
        )
        version = _payload_version(payload)
        mapping = by_key.get((item.kind, item.id))
        if (
            not destination
            or mapping is None
            or mapping.calendar_id != destination
            or mapping.status in ("pending", "failed")
        ):
            action: Literal["create", "update", "unchanged"] = "create"
        elif mapping.exported_version != version:
            action = "update"
        else:
            action = "unchanged"
        preview_items.append(ExportPreviewItem(id=item.id, kind=item.kind, action=action))

    return ExportPreviewResponse(
        requires_overwrite_confirmation=any(i.action == "update" for i in preview_items),
        items=preview_items,
    )


def _upsert_mapping(
    db: Session,
    user_id: UUID,
    item: ExportItem,
    destination: str,
    google_event_id: str,
    version: str,
    status: str,
    idempotency_key: str | None = None,
    *,
    preserve_existing_version: bool = False,
) -> GoogleCalendarEventExport:
    mapping = db.get(GoogleCalendarEventExport, (user_id, item.kind, item.id))
    if mapping is None:
        mapping = GoogleCalendarEventExport(
            user_id=user_id,
            event_kind=item.kind,
            local_event_id=item.id,
            calendar_id=destination,
            google_event_id=google_event_id,
            exported_version=version,
            status=status,
            last_idempotency_key=idempotency_key,
        )
        db.add(mapping)
    else:
        same_calendar = mapping.calendar_id == destination
        mapping.calendar_id = destination
        mapping.google_event_id = google_event_id
        if not (preserve_existing_version and same_calendar and mapping.exported_version):
            mapping.exported_version = version
        mapping.status = status
        mapping.last_idempotency_key = idempotency_key
    db.commit()
    return mapping


def export_events(
    db: Session,
    user: CurrentUser,
    items: list[ExportItem],
    *,
    allow_managed_field_updates: bool = False,
    include_description: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
    idempotency_key: str | None = None,
) -> list[ExportResult]:
    events = _validate_selection_and_load(db, user, items, start_date, end_date)
    settings = GoogleOAuthSettings.from_env()
    lock_account(db, user.id)
    connection = get_connection(db, user)
    if connection is None:
        raise HTTPException(409, REAUTHORIZE)

    token = _access_token(db, connection, settings)

    with httpx.Client(timeout=8) as client:
        # Materialize the payloads before a commit expires the loaded ORM rows.
        payloads = [
            _event_payload(
                user, item, events[item.kind, item.id], include_description=include_description
            )
            for item in items
        ]
        versions = [_payload_version(payload) for payload in payloads]
        destination = _calendar_id(db, client, connection, token)
        path = f"calendars/{quote(destination, safe='')}/events"
        encrypted_access_token = connection.encrypted_access_token
        db.commit()

        results: list[ExportResult] = []
        for item, payload, version in zip(items, payloads, versions, strict=True):
            existing = db.get(GoogleCalendarEventExport, (user.id, item.kind, item.id))
            already_on_destination = (
                existing is not None
                and existing.calendar_id == destination
                and existing.status in ("exported", "updated", "already_exported")
            )

            if (
                idempotency_key
                and already_on_destination
                and existing.last_idempotency_key == idempotency_key
                and (existing.exported_version == version or not allow_managed_field_updates)
            ):
                results.append(
                    ExportResult(id=item.id, kind=item.kind, status=existing.status)  # type: ignore[arg-type]
                )
                continue

            if not already_on_destination:
                _upsert_mapping(
                    db,
                    user.id,
                    item,
                    destination,
                    payload["id"],
                    version,
                    "pending",
                    idempotency_key,
                )

            try:
                if already_on_destination and allow_managed_field_updates:
                    event_path = f"{path}/{quote(payload['id'], safe='')}"
                    response = _call_with_backoff(
                        _put, client, event_path, token, {**payload, "status": "confirmed"}
                    )
                    if response.is_success:
                        status: Literal["exported", "updated", "already_exported", "failed"] = "updated"
                        _upsert_mapping(
                            db,
                            user.id,
                            item,
                            destination,
                            payload["id"],
                            version,
                            status,
                            idempotency_key,
                        )
                    else:
                        status = _handle_error_response(
                            db,
                            user,
                            item,
                            destination,
                            encrypted_access_token,
                            payload["id"],
                            version,
                            idempotency_key,
                            response,
                        )
                else:
                    response = _call_with_backoff(_post, client, path, token, payload)
                    if response.is_success:
                        status = "exported"
                        _upsert_mapping(
                            db,
                            user.id,
                            item,
                            destination,
                            payload["id"],
                            version,
                            status,
                            idempotency_key,
                        )
                    elif response.status_code == 409:
                        if allow_managed_field_updates:
                            event_path = f"{path}/{quote(payload['id'], safe='')}"
                            put_resp = _call_with_backoff(
                                _put, client, event_path, token, {**payload, "status": "confirmed"}
                            )
                            if put_resp.is_success:
                                status = "updated"
                                _upsert_mapping(
                                    db,
                                    user.id,
                                    item,
                                    destination,
                                    payload["id"],
                                    version,
                                    status,
                                    idempotency_key,
                                )
                            else:
                                status = _handle_error_response(
                                    db,
                                    user,
                                    item,
                                    destination,
                                    encrypted_access_token,
                                    payload["id"],
                                    version,
                                    idempotency_key,
                                    put_resp,
                                )
                        else:
                            status = "already_exported"
                            _upsert_mapping(
                                db,
                                user.id,
                                item,
                                destination,
                                payload["id"],
                                version,
                                status,
                                idempotency_key,
                                preserve_existing_version=already_on_destination,
                            )
                    else:
                        status = _handle_error_response(
                            db,
                            user,
                            item,
                            destination,
                            encrypted_access_token,
                            payload["id"],
                            version,
                            idempotency_key,
                            response,
                        )
            except httpx.RequestError:
                status = "failed"
                if not already_on_destination:
                    _upsert_mapping(
                        db,
                        user.id,
                        item,
                        destination,
                        payload["id"],
                        version,
                        status,
                        idempotency_key,
                    )
            results.append(ExportResult(id=item.id, kind=item.kind, status=status))
    return results


def _handle_error_response(
    db: Session,
    user: CurrentUser,
    item: ExportItem,
    destination: str,
    encrypted_access_token: str | None,
    google_event_id: str,
    version: str,
    idempotency_key: str | None,
    response: httpx.Response,
) -> Literal["failed"]:
    is_rate_limit = _is_rate_limited(response)
    is_auth_revoked = response.status_code == 401 or (
        response.status_code == 403 and not is_rate_limit
    )
    if is_auth_revoked or response.status_code in (404, 410):
        lock_account(db, user.id)
        current = get_connection(db, user)
        if (
            current
            and current.encrypted_access_token == encrypted_access_token
            and current.calendar_id == destination
        ):
            if is_auth_revoked:
                clear_credentials(db, current)
            else:
                current.calendar_id = PENDING_CALENDAR
        db.commit()
        raise HTTPException(409, REAUTHORIZE if is_auth_revoked else RECOVER_DESTINATION)

    existing = db.get(GoogleCalendarEventExport, (user.id, item.kind, item.id))
    if existing is None or existing.status in ("pending", "failed") or existing.calendar_id != destination:
        _upsert_mapping(
            db, user.id, item, destination, google_event_id, version, "failed", idempotency_key
        )
    return "failed"
