import base64
import hashlib
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from cryptography.fernet import Fernet
import httpx
import pytest

from src.database.models import GoogleCalendarConnection, GoogleCalendarOAuthState, PersonalEvent, Profile, PublicEvent, SavedPublicEvent
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
    response = api[0].post(f"{ROOT}/callback", data={"state": query["state"][0], **fields}, follow_redirects=False)
    assert response.status_code == 303
    redirect = urlsplit(response.headers["location"])
    assert redirect.netloc == "app.example.edu"
    assert set(parse_qs(redirect.query)) == {"aba", "google_calendar"}
    return parse_qs(redirect.query)["google_calendar"][0]


def _grant(api, actor, monkeypatch, *, scope=service.CALENDAR_SCOPE, email=None, verified=True):
    query = _start(api)

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
        db.get(GoogleCalendarConnection, actor.id).access_token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(400, json={"error": "invalid_grant"}))
    assert api[0].post(f"{ROOT}/exports", json={"events": [item]}).status_code == 409
    assert api[0].get(f"{ROOT}/connection").json()["connected"] is False
    assert _grant(api, actor, monkeypatch) == "connected"
    assert api[0].get(f"{ROOT}/connection").json()["connected"] is True


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
