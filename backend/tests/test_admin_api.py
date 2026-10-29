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
