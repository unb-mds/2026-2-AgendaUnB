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
        supabase_key="service-role-key",
    )


def test_storage_uses_server_key_for_upload_and_compensation(storage, monkeypatch):
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
        assert options["headers"]["Authorization"] == "Bearer service-role-key"
        assert options["headers"]["apikey"] == "service-role-key"
    assert calls[0][1]["headers"]["x-upsert"] == "false"


def test_dependency_uses_only_server_key(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://storage.example.test")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "server-key")
    user = CurrentUser(id=uuid4(), role="student", access_token="user-token")
    assert "user-token" not in repr(user)
    assert get_storage_service(user)._headers()["Authorization"] == "Bearer server-key"


@pytest.mark.parametrize("url,key,expected", [
    ("", "key", 503),
    ("https://storage.example.test", "", 503),
])
def test_storage_requires_configuration(url, key, expected):
    service = SupabaseStorageService(supabase_url=url, supabase_key=key)
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
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={
        "id": str(user_id), "email": "aluna@example.edu", "email_confirmed_at": "2026-11-01T00:00:00Z",
    }))
    database = Mock()
    database.scalar.return_value = "student"
    user = get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="user-token"), database)
    assert user.access_token == "user-token"
    assert user.id == user_id
    assert user.email == "aluna@example.edu"
    assert user.email_confirmed is True


def test_auth_rejects_unconfirmed_email_before_loading_role(monkeypatch):
    from unittest.mock import Mock

    from fastapi import HTTPException

    user_id = uuid4()
    monkeypatch.setenv("SUPABASE_URL", "https://auth.example.test")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "public-key")
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: httpx.Response(200, json={
        "id": str(user_id), "email": "aluna@example.edu", "email_confirmed_at": None,
        "confirmed_at": "2026-11-01T00:00:00Z",
    }))
    database = Mock()
    with pytest.raises(HTTPException) as error:
        get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials="user-token"), database)
    assert error.value.status_code == 403
    database.scalar.assert_not_called()


def test_storage_normalize_and_delete_if_present(storage, monkeypatch):
    assert storage.normalize_path("syllabus_files/owner/plano.pdf") == "owner/plano.pdf"
    assert storage.normalize_path("/syllabus_files/owner/plano.pdf") == "owner/plano.pdf"
    assert storage.normalize_path("owner/plano.pdf") == "owner/plano.pdf"
    assert storage.normalize_path("https://example.com/outro.pdf") == ""
    assert storage.normalize_path("  ") == ""

    called_urls = []

    def fake_delete(url, **kwargs):
        called_urls.append(url)
        if url.endswith("missing.pdf"):
            return httpx.Response(404)
        if url.endswith("wrapped404.pdf"):
            return httpx.Response(400, json={"statusCode": "404"})
        if url.endswith("fail.pdf"):
            return httpx.Response(503)
        return httpx.Response(204)

    monkeypatch.setattr(httpx, "delete", fake_delete)
    assert storage.delete_file_if_present("syllabus_files/owner/ok.pdf") is True
    assert storage.delete_file_if_present("syllabus_files/owner/missing.pdf") is True
    assert storage.delete_file_if_present("owner/wrapped404.pdf") is True
    assert storage.delete_file_if_present("owner/fail.pdf") is False
    assert called_urls[0].endswith("/storage/v1/object/syllabus_files/owner/ok.pdf")


def test_storage_list_prefix_and_strict_delete(storage, monkeypatch):
    pages = [
        [{"name": "folder", "id": None}, {"name": "a.pdf", "id": "1"}, {"name": "b.pdf", "id": "2"}],
        [{"name": "c.pdf", "id": "3"}],
    ]

    def fake_post(url, **kwargs):
        assert url.endswith("/storage/v1/object/list/syllabus_files")
        offset = kwargs["json"]["offset"]
        return httpx.Response(200, json=pages[0] if offset == 0 else pages[1])

    deleted = []

    def fake_delete(url, **kwargs):
        deleted.append(url)
        if url.endswith("/b.pdf"):
            return httpx.Response(404)
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "delete", fake_delete)

    listed = storage.list_prefix("uid-1/", page_size=3)
    assert listed == ["uid-1/a.pdf", "uid-1/b.pdf", "uid-1/c.pdf"]

    removed = storage.delete_objects_strict(["syllabus_files/uid-1/a.pdf", *listed])
    assert removed == 2
    assert len(deleted) == 3

    monkeypatch.setattr(httpx, "delete", lambda *args, **kwargs: httpx.Response(503))
    with pytest.raises(HTTPException) as exc:
        storage.delete_objects_strict(["uid-1/a.pdf"])
    assert exc.value.status_code == 503
