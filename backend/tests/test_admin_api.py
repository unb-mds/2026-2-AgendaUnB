from uuid import uuid4
import pytest
from fastapi import HTTPException
from src.middlewares.auth import CurrentUser, require_admin

@pytest.mark.parametrize("role", ["student", "professor", "admin"])
def test_admin_guard(role):
    user = CurrentUser(id=uuid4(), role=role)
    if role == "admin":
        assert require_admin(user) == user
    else:
        with pytest.raises(HTTPException) as error:
            require_admin(user)
        assert error.value.status_code == 403

from datetime import datetime, timezone
from src.database.models import PublicEvent

def test_pending(api):
    client, sessions, user, _ = api
    assert client.get("/api/v1/admin/events/pending").status_code == 403
    user["value"] = CurrentUser(id=uuid4(), role="admin")
    with sessions() as db:
        for status in ("pendente", "aprovado", "rejeitado"):
            db.add(PublicEvent(author_id=user["value"].id, title="Evento", description="Texto", starts_at=datetime.now(timezone.utc), status=status))
        db.commit()
    response = client.get("/api/v1/admin/events/pending")
    assert response.status_code == 200
    assert [e["status"] for e in response.json()] == ["pendente"]
    assert client.get("/api/v1/admin/events/pending?limit=101").status_code == 422

@pytest.mark.parametrize("status", ["aprovado", "rejeitado"])
def test_review(api, status):
    client, sessions, user, _ = api
    user["value"] = CurrentUser(id=uuid4(), role="admin")
    event_id = uuid4()
    with sessions() as db:
        db.add(PublicEvent(id=event_id, author_id=user["value"].id, title="Evento", description="Texto", starts_at=datetime.now(timezone.utc), status="pendente"))
        db.commit()
    url = f"/api/v1/admin/events/{event_id}/review"
    for body in ({"status":"pendente"}, {"status":"rejeitado"}, {"status":"rejeitado", "justificativa_recusa":" "}, {"status":"aprovado", "title":"forjado"}):
        assert client.patch(url, json=body).status_code == 422
    body = {"status":status, "justificativa_recusa":"Motivo"}
    response = client.patch(url, json=body)
    assert response.status_code == 200
    assert response.json()["justificativa_recusa"] == ("Motivo" if status == "rejeitado" else None)
    assert client.patch(url, json=body).status_code == 409
    assert client.patch(f"/api/v1/admin/events/{uuid4()}/review", json=body).status_code == 404

from unittest.mock import MagicMock
from src.database.connection import get_db
from src.main import app

def test_users_schema_and_filters(api):
    client, _, user, _ = api
    assert client.get("/api/v1/admin/users").status_code == 403
    user["value"] = CurrentUser(id=uuid4(), role="admin")
    db = MagicMock()
    db.execute.return_value.scalar_one.return_value = {"items": [{"id":str(uuid4()), "email":"test@example.org", "nome_completo":"Teste", "papel":"student", "criado_em":"2026-01-01T00:00:00Z", "ultimo_login":None, "email_confirmado":False, "password":"secret"}], "total":1,"all":1,"unconfirmed":1}
    app.dependency_overrides[get_db] = lambda: db
    response = client.get("/api/v1/admin/users?busca=Teste")
    assert response.status_code == 200
    assert "password" not in response.text
    assert response.json()["total"] == 1
    assert client.get("/api/v1/admin/users?papel=owner").status_code == 422
    assert client.get("/api/v1/admin/users?offset=-1").status_code == 422

from src.database.models import Profile

def test_role_changes(api):
    client, sessions, user, _ = api
    actor, target = uuid4(), uuid4()
    user["value"] = CurrentUser(id=actor, role="admin")
    with sessions() as db:
        db.add_all([Profile(id=actor,papel="admin"), Profile(id=target,papel="student")])
        db.commit()
    url = f"/api/v1/admin/users/{target}/role"
    for body in ({"role":"owner"}, {"role":"admin", "email":"forged"}):
        assert client.patch(url,json=body).status_code == 422
    assert client.patch(f"/api/v1/admin/users/{actor}/role", json={"role":"student"}).status_code == 409
    assert client.patch(url,json={"role":"admin"}).status_code == 200
    assert client.patch(url,json={"role":"professor"}).status_code == 200
    assert client.patch(f"/api/v1/admin/users/{uuid4()}/role",json={"role":"admin"}).status_code == 404
    with sessions() as db:
        db.get(Profile,actor).papel = "student"
        db.commit()
    assert client.patch(url,json={"role":"admin"}).status_code == 403

@pytest.mark.parametrize("method,path,body", [("get","events/pending",None),("get","users",None),("patch",f"events/{uuid4()}/review",{"status":"aprovado"}),("patch",f"users/{uuid4()}/role",{"role":"admin"})])
def test_routes_require_authentication(api, monkeypatch, method, path, body):
    client, _, user, _ = api
    url = "/api/v1/admin/" + path
    for role in ("student", "professor"):
        user["value"] = CurrentUser(id=uuid4(),role=role)
        assert client.request(method,url,json=body).status_code == 403
    from src.middlewares.auth import get_current_user
    app.dependency_overrides.pop(get_current_user)
    assert client.request(method,url,json=body).status_code == 401
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test")
    import httpx
    monkeypatch.setattr("src.middlewares.auth.httpx.get", lambda *a, **kw: httpx.Response(401))
    assert client.request(method,url,json=body,headers={"Authorization":"Bearer invalid"}).status_code == 401

def test_same_token_loses_admin_access(api, monkeypatch):
    client, sessions, user, _ = api
    actor = uuid4()
    with sessions() as db:
        db.add(Profile(id=actor, papel="admin"))
        db.commit()
    from src.middlewares.auth import get_current_user
    import httpx
    app.dependency_overrides.pop(get_current_user)
    monkeypatch.setenv("SUPABASE_URL", "https://example.invalid")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "test")
    monkeypatch.setattr("src.middlewares.auth.httpx.get", lambda *a, **kw: httpx.Response(200,json={"id":str(actor)}))
    headers = {"Authorization":"Bearer same-token"}
    assert client.get("/api/v1/admin/events/pending",headers=headers).status_code == 200
    with sessions() as db:
        db.get(Profile,actor).papel = "student"
        db.commit()
    assert client.get("/api/v1/admin/events/pending",headers=headers).status_code == 403
