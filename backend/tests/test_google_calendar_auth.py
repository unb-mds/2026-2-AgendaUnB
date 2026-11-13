import base64
from datetime import datetime, timedelta, timezone
import json
from uuid import uuid4

from cryptography.fernet import Fernet
import httpx
import pytest

from src.database.models import GoogleCalendarConnection, PersonalEvent, Profile, PublicEvent, SavedPublicEvent
from src.middlewares.auth import CurrentUser, _google_session_identity
from src.modules.google_calendar import export, service

ROOT = "/api/v1/me/google-calendar"


@pytest.fixture
def actor(api, monkeypatch):
    user = CurrentUser(id=uuid4(), role="student", email="ana@example.edu", email_confirmed=True, google_sub="google-ana")
    api[2]["value"] = user
    with api[1]() as db:
        db.add(Profile(id=user.id, papel="student", nome_completo="Ana"))
        db.commit()
    monkeypatch.setenv("SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID", "google-client")
    monkeypatch.setenv("SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET", "google-secret")
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    return user


def test_google_identity_is_available_only_in_oauth_sessions():
    auth_user = {"identities": [{"provider": "google", "identity_data": {"sub": "google-ana"}}]}
    for method, expected in (("password", None), ("oauth", "google-ana"), ("recovery", None)):
        payload = base64.urlsafe_b64encode(json.dumps({"amr": [{"method": method}]}).encode()).decode().rstrip("=")
        assert _google_session_identity(f"header.{payload}.signature", auth_user) == expected


def _grant(api, actor, monkeypatch, *, scope=service.CALENDAR_SCOPE, subject=None):
    def refresh(url, **kwargs):
        assert url == service.TOKEN_ENDPOINT
        assert kwargs["data"]["client_id"] == "google-client"
        assert kwargs["data"]["refresh_token"] == "provider-refresh"
        return httpx.Response(200, json={"access_token": "provider-access", "expires_in": 3600, "scope": scope})

    monkeypatch.setattr(httpx, "post", refresh)
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={
        "email": actor.email, "email_verified": True, "sub": subject or actor.google_sub,
    }))
    return api[0].post(f"{ROOT}/connection", json={"refresh_token": "provider-refresh"})


@pytest.mark.parametrize("scope,subject", [("openid email", None), (service.CALENDAR_SCOPE, "different-user")])
def test_callback_cannot_store_ungranted_scope_or_different_google_identity(api, actor, monkeypatch, scope, subject):
    assert _grant(api, actor, monkeypatch, scope=scope, subject=subject).status_code == 403
    assert api[0].get(f"{ROOT}/connection").json() == {"connected": False}


def test_callback_stores_valid_grant_encrypted_and_password_sessions_are_rejected(api, actor, monkeypatch, caplog):
    assert _grant(api, actor, monkeypatch).status_code == 204
    response = api[0].get(f"{ROOT}/connection")
    assert response.json() == {"connected": True}
    assert response.headers["cache-control"] == "no-store"
    with api[1]() as db:
        connection = db.get(GoogleCalendarConnection, actor.id)
        assert connection.encrypted_refresh_token != "provider-refresh"
        cipher = service.GoogleOAuthSettings.from_env().cipher
        assert cipher.decrypt(connection.encrypted_refresh_token).decode() == "provider-refresh"
    api[2]["value"] = CurrentUser(id=actor.id, role=actor.role, email=actor.email, email_confirmed=True)
    assert api[0].get(f"{ROOT}/connection").status_code == 403
    assert api[0].post(f"{ROOT}/connection", json={"refresh_token": "provider-refresh"}).status_code == 403
    assert api[0].post(f"{ROOT}/exports", json={"events": [{"id": str(uuid4()), "kind": "personal"}]}).status_code == 403
    assert api[0].post(f"{ROOT}/authorization").status_code == 404
    assert "provider-refresh" not in caplog.text and "provider-access" not in caplog.text


def _personal(db, user_id):
    item = PersonalEvent(user_id=user_id, title="Prova", description="Texto privado do plano",
                         starts_at=datetime(2026, 11, 13, 17, tzinfo=timezone.utc))
    db.add(item)
    db.flush()
    return {"id": str(item.id), "kind": "personal"}


def test_export_only_sends_selected_owned_events_and_reuses_calendar(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch).status_code == 204
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


def test_expired_grant_can_be_replaced_by_new_login(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch).status_code == 204
    with api[1]() as db:
        item = _personal(db, actor.id)
        db.get(GoogleCalendarConnection, actor.id).access_token_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(400, json={"error": "invalid_grant"}))
    assert api[0].post(f"{ROOT}/exports", json={"events": [item]}).status_code == 409
    assert api[0].get(f"{ROOT}/connection").json() == {"connected": False}
    assert _grant(api, actor, monkeypatch).status_code == 204
    assert api[0].get(f"{ROOT}/connection").json() == {"connected": True}


def test_lost_calendar_response_does_not_create_another_calendar(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch).status_code == 204
    with api[1]() as db:
        item = _personal(db, actor.id)
        db.commit()
    calls = []

    def post(client, path, token, payload):
        calls.append(path)
        raise httpx.ReadTimeout("upstream timeout")

    monkeypatch.setattr(export, "_post", post)
    for status in (503, 409):
        assert api[0].post(f"{ROOT}/exports", json={"events": [item]}).status_code == status
    assert calls == ["calendars"]


def test_partial_export_reports_which_item_to_retry(api, actor, monkeypatch):
    assert _grant(api, actor, monkeypatch).status_code == 204
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
