from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from src.database.models import GoogleCalendarConnection, Profile
from src.middlewares.auth import CurrentUser
from src.modules.google_calendar import router, service
from src.modules.google_calendar.service import decrypt_secret

GOOGLE_SCOPE = "https://www.googleapis.com/auth/calendar.app.created"


@pytest.fixture
def oauth_env(monkeypatch):
    values = {
        "GOOGLE_CALENDAR_CLIENT_ID": "google-client-id",
        "GOOGLE_CALENDAR_CLIENT_SECRET": "google-client-secret",
        "GOOGLE_CALENDAR_REDIRECT_URI": "http://localhost:8000/api/v1/me/google-calendar/callback",
        "GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI": "http://localhost:5173/configuracoes?tab=integracoes",
        "GOOGLE_TOKEN_ENCRYPTION_KEY": Fernet.generate_key().decode("ascii"),
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    return values


def _add_profile(session_factory, user):
    with session_factory() as db:
        db.add(Profile(id=user.id, papel="student", nome_completo="Conta de teste"))
        db.commit()


def _authenticated(api, email="ana@example.edu"):
    actor = CurrentUser(id=uuid4(), role="student", email=email, email_confirmed=True)
    api[2]["value"] = actor
    _add_profile(api[1], actor)
    return actor


def _authorization(client):
    response = client.post("/api/v1/me/google-calendar/authorization")
    assert response.status_code == 200
    url = urlsplit(response.json()["authorization_url"])
    query = parse_qs(url.query)
    return response, query


def test_authorization_uses_state_pkce_incremental_scope_and_no_store(api, oauth_env):
    _authenticated(api)

    response, query = _authorization(api[0])

    assert query["response_type"] == ["code"]
    assert query["response_mode"] == ["form_post"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["scope"] == [f"openid email {GOOGLE_SCOPE}"]
    assert query["access_type"] == ["offline"]
    assert query["include_granted_scopes"] == ["true"]
    assert response.headers["cache-control"] == "no-store"
    assert len(query["state"][0]) >= 32
    assert len(query["code_challenge"][0]) == 43
    with api[1]() as db:
        row = db.query(service.GoogleCalendarOAuthState).one()
        assert row.state_hash != query["state"][0]
        assert query["code_challenge"][0] not in row.encrypted_code_verifier


def test_callback_links_only_same_verified_google_email_and_keeps_tokens_encrypted(
    api, oauth_env, monkeypatch
):
    actor = _authenticated(api)
    _, query = _authorization(api[0])
    monkeypatch.setattr(service, "confirmed_agenda_email", lambda db, user_id: actor.email)

    def post(url, **kwargs):
        assert url == service.TOKEN_ENDPOINT
        assert kwargs["data"]["code_verifier"]
        return httpx.Response(200, json={
            "access_token": "google-access", "refresh_token": "google-refresh",
            "expires_in": 3600, "scope": f"openid email {GOOGLE_SCOPE}",
        })

    monkeypatch.setattr(httpx, "post", post)
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={
        "sub": "google-sub-1", "email": actor.email, "email_verified": True,
    }))

    response = api[0].post("/api/v1/me/google-calendar/callback", data={
        "state": query["state"][0], "code": "one-time-code",
    }, follow_redirects=False)

    assert response.status_code == 303
    assert "google_calendar=connected" in response.headers["location"]
    with api[1]() as db:
        connection = db.get(GoogleCalendarConnection, actor.id)
        assert connection.google_sub == "google-sub-1"
        assert connection.encrypted_access_token != "google-access"
        assert connection.encrypted_refresh_token != "google-refresh"
        assert decrypt_secret(connection.encrypted_refresh_token, service.GoogleOAuthSettings.from_env()) == "google-refresh"
        assert db.query(service.GoogleCalendarOAuthState).count() == 0

    status = api[0].get("/api/v1/me/google-calendar/connection")
    assert status.json() == {
        "connected": True, "google_email": actor.email, "calendar_id": None,
        "scope": f"openid email {GOOGLE_SCOPE}",
    }
    assert "google-access" not in status.text and "google-refresh" not in status.text


def test_callback_rejects_mismatched_or_unverified_google_identity(api, oauth_env, monkeypatch):
    actor = _authenticated(api)
    _, query = _authorization(api[0])
    monkeypatch.setattr(service, "confirmed_agenda_email", lambda db, user_id: actor.email)
    revoked = []
    monkeypatch.setattr(service, "revoke_token", lambda token: revoked.append(token) or True)
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, json={
        "access_token": "unmatched-access", "refresh_token": "unmatched-refresh",
        "expires_in": 3600, "scope": f"openid email {GOOGLE_SCOPE}",
    }))
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={
        "sub": "other-google-sub", "email": "other@example.edu", "email_verified": True,
    }))

    response = api[0].post("/api/v1/me/google-calendar/callback", data={
        "state": query["state"][0], "code": "one-time-code",
    }, follow_redirects=False)

    assert "google_calendar=email_mismatch" in response.headers["location"]
    assert revoked == ["unmatched-refresh"]
    with api[1]() as db:
        assert db.get(GoogleCalendarConnection, actor.id) is None


def test_callback_rejects_google_email_without_verified_claim(api, oauth_env, monkeypatch):
    actor = _authenticated(api)
    _, query = _authorization(api[0])
    monkeypatch.setattr(service, "confirmed_agenda_email", lambda db, user_id: actor.email)
    revoked = []
    monkeypatch.setattr(service, "revoke_token", lambda token: revoked.append(token) or True)
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, json={
        "access_token": "unverified-access", "refresh_token": "unverified-refresh",
        "expires_in": 3600, "scope": f"openid email {GOOGLE_SCOPE}",
    }))
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={
        "sub": "unverified-google-sub", "email": actor.email, "email_verified": False,
    }))

    response = api[0].post("/api/v1/me/google-calendar/callback", data={
        "state": query["state"][0], "code": "one-time-code",
    }, follow_redirects=False)

    assert "google_calendar=denied" in response.headers["location"]
    assert revoked == ["unverified-refresh"]
    with api[1]() as db:
        assert db.get(GoogleCalendarConnection, actor.id) is None


def test_oauth_state_is_one_time(api, oauth_env, monkeypatch):
    actor = _authenticated(api)
    _, query = _authorization(api[0])
    monkeypatch.setattr(service, "confirmed_agenda_email", lambda db, user_id: actor.email)
    calls = []
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: calls.append(args) or httpx.Response(400))

    first = api[0].post("/api/v1/me/google-calendar/callback", data={
        "state": query["state"][0], "error": "access_denied",
    }, follow_redirects=False)
    second = api[0].post("/api/v1/me/google-calendar/callback", data={
        "state": query["state"][0], "code": "replayed-code",
    }, follow_redirects=False)

    assert "google_calendar=denied" in first.headers["location"]
    assert "google_calendar=invalid_state" in second.headers["location"]
    assert calls == []


def test_refresh_helper_renews_token_without_returning_it_from_connection_route(api, oauth_env, monkeypatch):
    actor = _authenticated(api)
    settings = service.GoogleOAuthSettings.from_env()
    with api[1]() as db:
        db.add(GoogleCalendarConnection(
            user_id=actor.id, google_sub="google-sub", google_email=actor.email,
            encrypted_access_token=service.encrypt_secret("expired", settings),
            encrypted_refresh_token=service.encrypt_secret("refresh-secret", settings),
            access_token_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            granted_scope=f"openid email {GOOGLE_SCOPE}",
        ))
        db.commit()
        seen = {}

        def post(url, **kwargs):
            seen.update(kwargs["data"])
            return httpx.Response(200, json={"access_token": "renewed", "expires_in": 3600})

        monkeypatch.setattr(httpx, "post", post)
        assert service.get_access_token(db, actor.id, settings) == "renewed"
        assert seen["refresh_token"] == "refresh-secret"
        assert service.decrypt_secret(db.get(GoogleCalendarConnection, actor.id).encrypted_access_token, settings) == "renewed"


def test_refresh_configuration_error_does_not_delete_connection(api, oauth_env, monkeypatch):
    actor = _authenticated(api)
    settings = service.GoogleOAuthSettings.from_env()
    with api[1]() as db:
        db.add(GoogleCalendarConnection(
            user_id=actor.id, google_sub="google-sub", google_email=actor.email,
            encrypted_access_token=service.encrypt_secret("expired", settings),
            encrypted_refresh_token=service.encrypt_secret("refresh-secret", settings),
            access_token_expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
            granted_scope=f"openid email {GOOGLE_SCOPE}",
        ))
        db.commit()
        monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(400, json={"error": "invalid_client"}))

        with pytest.raises(HTTPException) as error:
            service.get_access_token(db, actor.id, settings)

        assert getattr(error.value, "status_code", None) == 503
        assert db.get(GoogleCalendarConnection, actor.id) is not None


def test_disconnect_revokes_and_deletes_server_credentials(api, oauth_env, monkeypatch):
    actor = _authenticated(api)
    settings = service.GoogleOAuthSettings.from_env()
    with api[1]() as db:
        db.add(GoogleCalendarConnection(
            user_id=actor.id, google_sub="google-sub", google_email=actor.email,
            encrypted_access_token=service.encrypt_secret("access-secret", settings),
            encrypted_refresh_token=service.encrypt_secret("refresh-secret", settings),
            access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            granted_scope=f"openid email {GOOGLE_SCOPE}",
        ))
        db.commit()
    revoked = []
    monkeypatch.setattr(router, "revoke_token", lambda token: revoked.append(token) or True)

    response = api[0].delete("/api/v1/me/google-calendar/connection")

    assert response.json() == {"disconnected": True, "revocation": "confirmed"}
    assert revoked == ["refresh-secret"]
    with api[1]() as db:
        assert db.get(GoogleCalendarConnection, actor.id) is None
