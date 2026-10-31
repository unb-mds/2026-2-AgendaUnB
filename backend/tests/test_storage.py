from uuid import uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.middlewares.auth import CurrentUser, get_current_user
from src.services.storage import SupabaseStorageService, get_storage_service


@pytest.fixture
def storage():
    return SupabaseStorageService(
        supabase_url="https://storage.example.test",
        supabase_key="public-key",
        auth_token="validated-user-token",
    )


def test_storage_uses_user_session_for_upload_and_compensation(storage, monkeypatch):
    calls = []

    def record(url, **kwargs):
        calls.append((url, kwargs))
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "post", record)
    monkeypatch.setattr(httpx, "delete", record)
    assert storage.upload_file("owner/plano.pdf", b"pdf") == "syllabus_files/owner/plano.pdf"
    assert storage.delete_file("owner/plano.pdf")
    for url, options in calls:
        assert url.endswith("/storage/v1/object/syllabus_files/owner/plano.pdf")
        assert options["headers"]["Authorization"] == "Bearer validated-user-token"
        assert options["headers"]["apikey"] == "public-key"
    assert calls[0][1]["headers"]["x-upsert"] == "false"


def test_dependency_forwards_only_validated_session(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://storage.example.test")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "must-not-use-service-role")
    user = CurrentUser(id=uuid4(), role="student", access_token="user-token")
    assert "user-token" not in repr(user)
    assert get_storage_service(user)._headers()["Authorization"] == "Bearer user-token"


@pytest.mark.parametrize("url,key,token,expected", [
    ("", "key", "token", 503),
    ("https://storage.example.test", "", "token", 503),
    ("https://storage.example.test", "key", None, 401),
])
def test_storage_requires_configuration_and_session(url, key, token, expected):
    service = SupabaseStorageService(supabase_url=url, supabase_key=key, auth_token=token)
    with pytest.raises(HTTPException) as error:
        service.upload_file("owner/file.pdf", b"pdf")
    assert error.value.status_code == expected


@pytest.mark.parametrize("http_status,body,expected", [
    (400, {"statusCode": "403", "message": "private diagnostics"}, 403),
    (401, {"message": "private diagnostics"}, 401),
    (500, {"message": "private diagnostics"}, 502),
])
def test_storage_sanitizes_errors(storage, monkeypatch, http_status, body, expected):
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(http_status, json=body))
    with pytest.raises(HTTPException) as error:
        storage.upload_file("owner/file.pdf", b"pdf")
    assert error.value.status_code == expected
    assert "private diagnostics" not in error.value.detail


def test_auth_retains_validated_token(monkeypatch):
    from unittest.mock import Mock

    user_id = uuid4()
    monkeypatch.setenv("SUPABASE_URL", "https://auth.example.test")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={"id": str(user_id)}))
    database = Mock()
    database.scalar.return_value = "student"
    user = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="user-token"), database)
    assert user.access_token == "user-token"
    assert user.id == user_id
