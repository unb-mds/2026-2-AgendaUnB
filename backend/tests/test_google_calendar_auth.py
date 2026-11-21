import base64
import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

from cryptography.fernet import Fernet
import httpx
import pytest

from src.database.models import (
    Consent,
    GoogleCalendarConnection,
    GoogleCalendarEventExport,
    GoogleCalendarOAuthState,
    PersonalEvent,
    Profile,
    PublicEvent,
    SavedPublicEvent,
)
from src.middlewares.auth import CurrentUser
from src.modules.google_calendar import export, service

ROOT = "/api/v1/me/google-calendar"


@pytest.fixture
def actor(api, monkeypatch):
    user = CurrentUser(id=uuid4(), role="student", email="ana@example.edu", email_confirmed=True)
    api[2]["value"] = user
    with api[1]() as db:
        db.add(Profile(id=user.id, papel="student", nome_completo="Ana"))
        db.commit()
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_SECRET", "google-secret")
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_CALENDAR_REDIRECT_URI", "https://api.example.edu/api/v1/me/google-calendar/callback")
    monkeypatch.setenv("GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI", "https://app.example.edu/eventos?aba=meus")
    monkeypatch.setattr(service, "confirmed_agenda_email", lambda db, user_id: user.email)
    return user


def _start(api):
    response = api[0].post(f"{ROOT}/authorization")
    assert response.status_code == 200
    return parse_qs(urlsplit(response.json()["authorization_url"]).query)


def _callback(api, query, **fields):
    response = api[0].get(f"{ROOT}/callback", params={"state": query["state"][0], **fields}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    redirect = urlsplit(response.headers["location"])
    assert redirect.netloc == "app.example.edu"
    assert set(parse_qs(redirect.query)) == {"aba", "google_calendar"}
    return parse_qs(redirect.query)["google_calendar"][0]


def _grant(api, actor, monkeypatch, *, scope=service.CALENDAR_SCOPE, email=None, verified=True):
    query = _start(api)
    assert "response_mode" not in query

    def exchange(url, **kwargs):
        assert url == service.TOKEN_ENDPOINT
        data = kwargs["data"]
        assert data["client_id"] == "google-client"
        assert data["grant_type"] == "authorization_code"
        assert query["code_challenge_method"] == ["S256"]
        challenge = base64.urlsafe_b64encode(hashlib.sha256(data["code_verifier"].encode()).digest())
        assert challenge.rstrip(b"=").decode() == query["code_challenge"][0]
        return httpx.Response(200, json={
            "access_token": "provider-access", "refresh_token": "provider-refresh", "expires_in": 3600, "scope": scope,
        })

    monkeypatch.setattr(httpx, "post", exchange)
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={
        "email": email or actor.email, "email_verified": verified, "sub": "google-ana",
    }))
    result = _callback(api, query, code="provider-code")
    assert _callback(api, query, code="provider-code") == "invalid_state"
    return result


@pytest.mark.parametrize("options,outcome", [
    ({"scope": "openid email"}, "denied"),
    ({"email": "outra@example.edu"}, "email_mismatch"),
    ({"verified": False}, "denied"),
])
def test_callback_rejects_scope_or_identity(api, actor, monkeypatch, options, outcome):
    assert _grant(api, actor, monkeypatch, **options) == outcome
    assert api[0].get(f"{ROOT}/connection").json()["connected"] is False


def test_expired_or_denied_state_cannot_be_replayed(api, actor, monkeypatch):
    denied = _start(api)
    expired = _start(api)
    assert _callback(api, denied, error="access_denied") == "invalid_state"
    with api[1]() as db:
        pending = db.query(GoogleCalendarOAuthState).one()
        pending.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    assert _callback(api, expired, code="provider-code") == "invalid_state"
    denied = _start(api)
    assert _callback(api, denied, error="access_denied") == "denied"
    assert _callback(api, denied, code="provider-code") == "invalid_state"


@pytest.mark.parametrize("revoked", [True, False])
def test_password_session_can_connect_and_disconnect(api, actor, monkeypatch, caplog, revoked):
    assert _grant(api, actor, monkeypatch) == "connected"
    response = api[0].get(f"{ROOT}/connection")
    assert response.json() == {"connected": True, "recovery_required": False}
    assert response.headers["cache-control"] == "no-store"
    with api[1]() as db:
        connection = db.get(GoogleCalendarConnection, actor.id)
        cipher = service.GoogleOAuthSettings.from_env().cipher
        assert connection.encrypted_refresh_token != "provider-refresh"
        assert cipher.decrypt(connection.encrypted_refresh_token).decode() == "provider-refresh"

    def revoke(url, **kwargs):
        assert url == service.REVOCATION_ENDPOINT
        assert kwargs["data"] == {"token": "provider-refresh"}
        return httpx.Response(200 if revoked else 503)

    monkeypatch.setattr(httpx, "post", revoke)
    pending = _start(api)
    result = api[0].delete(f"{ROOT}/connection")
    assert result.json()["revocation"] == ("confirmed" if revoked else "not_confirmed_remove_access_in_google")
    assert _callback(api, pending, code="provider-code") == "invalid_state"
    with api[1]() as db:
        connection = db.get(GoogleCalendarConnection, actor.id)
        assert connection.encrypted_access_token is None
        assert connection.encrypted_refresh_token is None
    assert "provider-refresh" not in caplog.text and "provider-access" not in caplog.text


def _personal(db, user_id):
    item = PersonalEvent(user_id=user_id, title="Prova", description="Texto privado do plano",
                         starts_at=datetime(2026, 11, 13, 17, tzinfo=timezone.utc))
    db.add(item)
    db.flush()
    return {"id": str(item.id), "kind": "personal"}


def test_export_only_sends_selected_owned_events_and_reuses_calendar(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        personal = _personal(db, actor.id)
        other = _personal(db, uuid4())
        public = PublicEvent(author_id=actor.id, title="Palestra", description="Detalhes",
                             starts_at=datetime(2026, 11, 13, 19, tzinfo=timezone.utc), status="aprovado")
        db.add(public)
        db.flush()
        db.add(SavedPublicEvent(user_id=actor.id, event_id=public.id))
        saved = {"id": str(public.id), "kind": "saved"}
        db.commit()

    created = set()
    destinations = []
    def post(client, path, token, payload):
        assert token == "provider-access"
        if path == "calendars":
            destinations.append(payload)
            return httpx.Response(200, json={"id": "agenda@example.com"})
        assert path == "calendars/agenda%40example.com/events"
        assert set(payload) == {"id", "summary", "start", "end"}
        assert payload["start"]["timeZone"] == "America/Sao_Paulo"
        if payload["summary"] == "Prova":
            assert payload["start"]["dateTime"] == "2026-11-13T14:00:00-03:00"
            assert payload["end"]["dateTime"] == "2026-11-13T15:00:00-03:00"
        if payload["id"] in created:
            return httpx.Response(409)
        created.add(payload["id"])
        return httpx.Response(200)

    monkeypatch.setattr(export, "_post", post)
    assert api[0].post(f"{ROOT}/exports", json={"events": [personal, other]}).status_code == 404
    assert not destinations
    for expected in ("exported", "already_exported"):
        result = api[0].post(f"{ROOT}/exports", json={"events": [personal, saved]})
        assert result.status_code == 200
        assert [item["status"] for item in result.json()] == [expected, expected]
    assert len(destinations) == 1 and len(created) == 2


def test_expired_grant_can_be_replaced_by_new_authorization(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        item = _personal(db, actor.id)
        consent = db.query(Consent).filter_by(user_id=actor.id, purpose="google_agenda").one()
        assert consent.revoked_at is None
        consent_id = consent.id
        db.get(GoogleCalendarConnection, actor.id).access_token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(400, json={"error": "invalid_grant"}))
    assert api[0].post(f"{ROOT}/exports", json={"events": [item]}).status_code == 409
    assert api[0].get(f"{ROOT}/connection").json()["connected"] is False
    with api[1]() as db:
        connection = db.get(GoogleCalendarConnection, actor.id)
        assert connection.encrypted_access_token is None
        assert connection.encrypted_refresh_token is None
        assert db.get(Consent, consent_id).revoked_at is not None

    assert _grant(api, actor, monkeypatch) == "connected"
    assert api[0].get(f"{ROOT}/connection").json()["connected"] is True
    with api[1]() as db:
        active_consent = db.query(Consent).filter_by(
            user_id=actor.id, purpose="google_agenda", revoked_at=None
        ).one()
        assert active_consent.id != consent_id


def test_expired_access_token_is_refreshed_on_server(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        item = _personal(db, actor.id)
        connection = db.get(GoogleCalendarConnection, actor.id)
        connection.calendar_id = "agenda@example.com"
        connection.access_token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()

    def refresh(url, **kwargs):
        assert url == service.TOKEN_ENDPOINT
        assert kwargs["data"]["grant_type"] == "refresh_token"
        assert kwargs["data"]["refresh_token"] == "provider-refresh"
        return httpx.Response(200, json={"access_token": "renewed-access", "expires_in": 3600})

    def post(client, path, token, payload):
        assert token == "renewed-access"
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "post", refresh)
    monkeypatch.setattr(export, "_post", post)
    assert api[0].post(f"{ROOT}/exports", json={"events": [item]}).status_code == 200
    with api[1]() as db:
        stored = db.get(GoogleCalendarConnection, actor.id)
        cipher = service.GoogleOAuthSettings.from_env().cipher
        assert cipher.decrypt(stored.encrypted_access_token).decode() == "renewed-access"


def test_lost_calendar_response_can_recover_the_existing_calendar(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        item = _personal(db, actor.id)
        db.commit()
    calls = []

    def post(client, path, token, payload):
        calls.append(path)
        if path == "calendars":
            raise httpx.ReadTimeout("upstream timeout")
        assert path == "calendars/agenda%40example.com/events"
        return httpx.Response(200)

    monkeypatch.setattr(export, "_post", post)
    for status in (503, 409):
        assert api[0].post(f"{ROOT}/exports", json={"events": [item]}).status_code == status
    assert calls == ["calendars"]
    assert api[0].get(f"{ROOT}/connection").json()["recovery_required"] is True
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(
        200, json={"id": "agenda@example.com", "summary": "Agenda UnB"},
    ))
    assert api[0].put(f"{ROOT}/destination", json={"calendar_id": "primary"}).status_code == 422
    assert api[0].put(f"{ROOT}/destination", json={"calendar_id": "agenda@example.com"}).status_code == 204
    assert api[0].post(f"{ROOT}/exports", json={"events": [item]}).status_code == 200
    assert calls == ["calendars", "calendars/agenda%40example.com/events"]


def test_deleted_destination_can_be_recreated(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        item = _personal(db, actor.id)
        db.get(GoogleCalendarConnection, actor.id).calendar_id = "deleted@example.com"
        db.commit()

    def post(client, path, token, payload):
        if path == "calendars/deleted%40example.com/events":
            return httpx.Response(404)
        if path == "calendars":
            return httpx.Response(200, json={"id": "new@example.com"})
        assert path == "calendars/new%40example.com/events"
        return httpx.Response(200)

    monkeypatch.setattr(export, "_post", post)
    assert api[0].post(f"{ROOT}/exports", json={"events": [item]}).status_code == 409
    assert api[0].get(f"{ROOT}/connection").json()["recovery_required"] is True
    assert api[0].put(f"{ROOT}/destination", json={"calendar_id": None}).status_code == 204
    assert api[0].post(f"{ROOT}/exports", json={"events": [item]}).json()[0]["status"] == "exported"


def test_partial_export_reports_which_item_to_retry(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        first = _personal(db, actor.id)
        second = _personal(db, actor.id)
        db.commit()
    attempts = []

    def post(client, path, token, payload):
        if path == "calendars":
            return httpx.Response(200, json={"id": "agenda@example.com"})
        attempts.append(payload["id"])
        return httpx.Response(503 if len(attempts) == 2 else 200)

    monkeypatch.setattr(export, "_post", post)
    result = api[0].post(f"{ROOT}/exports", json={"events": [first, second]})
    assert [item["status"] for item in result.json()] == ["exported", "failed"]
    assert api[0].post(f"{ROOT}/exports", json={"events": [second]}).json()[0]["status"] == "exported"
    assert attempts[0] != attempts[1] == attempts[2]


def test_export_persists_mapping_and_supports_all_day_intervals_location_and_description(
    api, actor, monkeypatch
):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        all_day_personal = PersonalEvent(
            user_id=actor.id,
            title="Entrega do Trabalho Final — Cálculo",
            description="Enviar relatório em PDF no aprender3",
            location=" Bloco B - FGA ",
            all_day=True,
            start_date=date(2026, 11, 18),
            end_date=date(2026, 11, 21),
            starts_at=datetime(2026, 11, 18, 3, tzinfo=timezone.utc),
            ends_at=datetime(2026, 11, 21, 3, tzinfo=timezone.utc),
        )
        timed_public = PublicEvent(
            author_id=actor.id,
            title="Simpósio de Extensão Universitária",
            description="Mesa-redonda com apresentação de projetos",
            location="Auditório Central",
            all_day=False,
            starts_at=datetime(2026, 11, 19, 17, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 11, 19, 19, 30, tzinfo=timezone.utc),
            status="aprovado",
        )
        db.add_all([all_day_personal, timed_public])
        db.flush()
        db.add(SavedPublicEvent(user_id=actor.id, event_id=timed_public.id))
        personal_ref = {"id": str(all_day_personal.id), "kind": "personal"}
        saved_ref = {"id": str(timed_public.id), "kind": "saved"}
        db.commit()

    sent_payloads = []

    def post(client, path, token, payload):
        if path == "calendars":
            return httpx.Response(200, json={"id": "agenda@example.com"})
        assert path == "calendars/agenda%40example.com/events"
        sent_payloads.append(payload)
        return httpx.Response(200, json={"id": payload["id"]})

    monkeypatch.setattr(export, "_post", post)
    response = api[0].post(
        f"{ROOT}/exports",
        json={
            "events": [personal_ref, saved_ref],
            "include_description": True,
            "start_date": "2026-11-18",
            "end_date": "2026-11-20",
        },
    )
    assert response.status_code == 200
    assert [item["status"] for item in response.json()] == ["exported", "exported"]
    assert len(sent_payloads) == 2

    first_payload, second_payload = sent_payloads
    assert re.fullmatch(r"[a-v0-9]{5,1024}", first_payload["id"])
    assert first_payload["summary"] == "Entrega do Trabalho Final — Cálculo"
    assert first_payload["location"] == "Bloco B - FGA"
    assert first_payload["description"] == "Enviar relatório em PDF no aprender3"
    assert first_payload["start"] == {"date": "2026-11-18"}
    assert first_payload["end"] == {"date": "2026-11-21"}

    assert re.fullmatch(r"[a-v0-9]{5,1024}", second_payload["id"])
    assert second_payload["summary"] == "Simpósio de Extensão Universitária"
    assert second_payload["location"] == "Auditório Central"
    assert second_payload["description"] == "Mesa-redonda com apresentação de projetos"
    assert second_payload["start"] == {
        "dateTime": "2026-11-19T14:00:00-03:00",
        "timeZone": "America/Sao_Paulo",
    }
    assert second_payload["end"] == {
        "dateTime": "2026-11-19T16:30:00-03:00",
        "timeZone": "America/Sao_Paulo",
    }

    with api[1]() as db:
        rows = db.query(GoogleCalendarEventExport).filter_by(user_id=actor.id).all()
        assert len(rows) == 2
        assert {row.status for row in rows} == {"exported"}
        assert {row.calendar_id for row in rows} == {"agenda@example.com"}
        for row in rows:
            assert re.fullmatch(r"[0-9a-f]{64}", row.exported_version)


def test_preview_and_explicit_reexport_overwrite_confirmation(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        item = _personal(db, actor.id)
        event_uuid = UUID(item["id"])
        db.commit()

    put_calls = []

    def post(client, path, token, payload):
        if path == "calendars":
            return httpx.Response(200, json={"id": "agenda@example.com"})
        return httpx.Response(409 if put_calls or db_has_export() else 200)

    def put(client, path, token, payload):
        put_calls.append((path, payload))
        return httpx.Response(200, json={"id": payload["id"]})

    def db_has_export():
        with api[1]() as db:
            row = db.get(GoogleCalendarEventExport, (actor.id, "personal", event_uuid))
            return row is not None and row.status in ("exported", "updated", "already_exported")

    monkeypatch.setattr(export, "_post", post)
    monkeypatch.setattr(export, "_put", put)

    preview_before = api[0].post(f"{ROOT}/exports/preview", json={"events": [item]})
    assert preview_before.status_code == 200
    assert preview_before.json() == {
        "requires_overwrite_confirmation": False,
        "items": [{"id": item["id"], "kind": "personal", "action": "create"}],
    }

    first_export = api[0].post(f"{ROOT}/exports", json={"events": [item]})
    assert first_export.status_code == 200
    assert first_export.json()[0]["status"] == "exported"

    preview_unchanged = api[0].post(f"{ROOT}/exports/preview", json={"events": [item]})
    assert preview_unchanged.json() == {
        "requires_overwrite_confirmation": False,
        "items": [{"id": item["id"], "kind": "personal", "action": "unchanged"}],
    }

    # Edit local event title and location
    with api[1]() as db:
        ev = db.get(PersonalEvent, event_uuid)
        ev.title = "Prova 1 (Sala Alterada)"
        ev.location = "Sala I1"
        db.commit()

    preview_modified = api[0].post(f"{ROOT}/exports/preview", json={"events": [item]})
    assert preview_modified.json() == {
        "requires_overwrite_confirmation": True,
        "items": [{"id": item["id"], "kind": "personal", "action": "update"}],
    }

    # Without allow_managed_field_updates=True, re-export does not overwrite remote event
    without_confirm = api[0].post(
        f"{ROOT}/exports",
        json={"events": [item], "allow_managed_field_updates": False},
    )
    assert without_confirm.status_code == 200
    assert without_confirm.json()[0]["status"] == "already_exported"
    assert put_calls == []

    # Preview still reports update required because remote copy was not overwritten yet
    assert api[0].post(f"{ROOT}/exports/preview", json={"events": [item]}).json()[
        "requires_overwrite_confirmation"
    ] is True

    # With explicit confirmation (allow_managed_field_updates=True), updates via PUT
    with_confirm = api[0].post(
        f"{ROOT}/exports",
        json={"events": [item], "allow_managed_field_updates": True},
    )
    assert with_confirm.status_code == 200
    assert with_confirm.json()[0]["status"] == "updated"
    assert len(put_calls) == 1
    assert put_calls[0][1]["summary"] == "Prova 1 (Sala Alterada)"
    assert put_calls[0][1]["location"] == "Sala I1"
    assert put_calls[0][1]["status"] == "confirmed"

    # Now preview shows unchanged
    preview_after_update = api[0].post(f"{ROOT}/exports/preview", json={"events": [item]})
    assert preview_after_update.json() == {
        "requires_overwrite_confirmation": False,
        "items": [{"id": item["id"], "kind": "personal", "action": "unchanged"}],
    }


def test_timeout_reconciliation_and_idempotency_key_prevent_duplicates(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        item = _personal(db, actor.id)
        db.commit()

    post_calls = []

    def post(client, path, token, payload):
        if path == "calendars":
            return httpx.Response(200, json={"id": "agenda@example.com"})
        post_calls.append(payload["id"])
        if len(post_calls) == 1:
            raise httpx.ReadTimeout("upstream timeout after event creation")
        return httpx.Response(409)

    monkeypatch.setattr(export, "_post", post)

    # First attempt times out -> status is failed
    first = api[0].post(
        f"{ROOT}/exports",
        headers={"Idempotency-Key": "batch-key-1"},
        json={"events": [item]},
    )
    assert first.status_code == 200
    assert first.json()[0]["status"] == "failed"

    # Retry with same Idempotency-Key reconciles 409 from Google into already_exported
    second = api[0].post(
        f"{ROOT}/exports",
        headers={"Idempotency-Key": "batch-key-1"},
        json={"events": [item]},
    )
    assert second.status_code == 200
    assert second.json()[0]["status"] == "already_exported"
    assert len(post_calls) == 2

    # Repeating the already-completed Idempotency-Key returns without calling Google again
    third = api[0].post(
        f"{ROOT}/exports",
        headers={"Idempotency-Key": "batch-key-1"},
        json={"events": [item]},
    )
    assert third.status_code == 200
    assert third.json()[0]["status"] == "already_exported"
    assert len(post_calls) == 2


def test_rate_limit_429_uses_bounded_backoff_and_403_revocation_clears_credentials(
    api, actor, monkeypatch
):
    assert _grant(api, actor, monkeypatch) == "connected"
    with api[1]() as db:
        item = _personal(db, actor.id)
        db.get(GoogleCalendarConnection, actor.id).calendar_id = "agenda@example.com"
        db.commit()

    slept = []
    monkeypatch.setattr(export.time_module, "sleep", lambda seconds: slept.append(seconds))

    attempts = 0

    def post_rate_limited(client, path, token, payload):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "10"})
        return httpx.Response(200, json={"id": payload["id"]})

    monkeypatch.setattr(export, "_post", post_rate_limited)
    res = api[0].post(f"{ROOT}/exports", json={"events": [item]})
    assert res.status_code == 200
    assert res.json()[0]["status"] == "exported"
    assert slept == [export.MAX_BACKOFF_SECONDS]

    # Non-rate-limit 403 revokes credentials and requires reauthorization (409)
    with api[1]() as db:
        second = _personal(db, actor.id)
        db.commit()

    monkeypatch.setattr(
        export,
        "_post",
        lambda client, path, token, payload: httpx.Response(
            403, json={"error": {"errors": [{"reason": "insufficientPermissions"}]}}
        ),
    )
    revoked_res = api[0].post(f"{ROOT}/exports", json={"events": [second]})
    assert revoked_res.status_code == 409
    assert api[0].get(f"{ROOT}/connection").json()["connected"] is False
