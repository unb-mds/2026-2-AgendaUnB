from datetime import datetime, timezone
from uuid import uuid4

from src.database.models import PublicEvent


def make_public_event(ids, **overrides):
    values = {
        "author_id": uuid4(),
        "title": "Mostra cultural da UnB",
        "description": "Evento aberto à comunidade",
        "starts_at": datetime(2026, 10, 2, 14, tzinfo=timezone.utc),
        "location": "Memorial Darcy Ribeiro",
        "campus_id": ids["campus"],
        "category_id": ids["category"],
        "status": "aprovado",
    }
    values.update(overrides)
    return PublicEvent(**values)


def test_list_public_events_filters_and_hides_pending(api):
    client, session_factory, _, ids = api
    with session_factory() as db:
        db.add_all([
            make_public_event(ids),
            make_public_event(ids, title="Evento pendente", status="pendente"),
            make_public_event(ids, title="Outro campus", campus_id=None),
        ])
        db.commit()

    response = client.get(
        "/api/v1/events",
        params={
            "campus": "Darcy Ribeiro (Plano Piloto)",
            "category": "Cultura",
            "q": "mostra",
            "startDate": "2026-10-01T00:00:00Z",
            "endDate": "2026-10-03T00:00:00Z",
        },
    )

    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["title"] == "Mostra cultural da UnB"
    assert events[0]["campus"] == "Darcy Ribeiro (Plano Piloto)"


def test_public_event_detail_returns_404_for_missing_id(api):
    client, session_factory, _, ids = api
    with session_factory() as db:
        event = make_public_event(ids)
        db.add(event)
        db.commit()
        event_id = event.id

    assert client.get(f"/api/v1/events/{event_id}").status_code == 200
    missing = client.get(f"/api/v1/events/{uuid4()}")
    assert missing.status_code == 404


def test_invalid_filter_range_returns_422(api):
    client, _, _, _ = api
    response = client.get(
        "/api/v1/events",
        params={
            "startDate": "2026-10-04T00:00:00Z",
            "endDate": "2026-10-01T00:00:00Z",
        },
    )
    assert response.status_code == 422


def test_public_create_and_delete_require_event_manager(api):
    client, session_factory, authenticated_user, ids = api
    payload = {
        "title": "Seminário sobre cultura",
        "description": "Descrição do seminário",
        "starts_at": "2026-10-08T15:00:00Z",
        "campus": "Darcy Ribeiro (Plano Piloto)",
        "category": "Cultura",
        "location": "Auditório",
        "external_url": "https://example.org/inscricao",
    }

    denied = client.post("/api/v1/events", json=payload)
    assert denied.status_code == 403

    authenticated_user["value"] = authenticated_user["value"].__class__(
        id=authenticated_user["value"].id,
        role="professor",
    )
    created = client.post("/api/v1/events", json=payload)
    assert created.status_code == 201
    event_id = created.json()["id"]

    deleted = client.delete(f"/api/v1/events/{event_id}")
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/events/{event_id}").status_code == 404


def test_personal_event_crud_is_limited_to_its_owner(api):
    client, _, authenticated_user, ids = api
    owner = authenticated_user["value"]
    payload = {
        "title": "Prova de arquitetura",
        "description": "Revisar o conteúdo",
        "starts_at": "2026-10-15T13:00:00Z",
        "campus": "Darcy Ribeiro (Plano Piloto)",
        "category": "Cultura",
    }

    created = client.post("/api/v1/me/events", json=payload)
    assert created.status_code == 201
    event_id = created.json()["id"]
    assert len(client.get("/api/v1/me/events").json()) == 1

    authenticated_user["value"] = authenticated_user["value"].__class__(
        id=uuid4(), role="student"
    )
    assert client.get(f"/api/v1/me/events/{event_id}").status_code == 404
    assert client.delete(f"/api/v1/me/events/{event_id}").status_code == 404

    authenticated_user["value"] = owner
    payload["title"] = "Prova de arquitetura revisada"
    updated = client.put(f"/api/v1/me/events/{event_id}", json=payload)
    assert updated.status_code == 200
    assert updated.json()["title"] == payload["title"]

    deleted = client.delete(f"/api/v1/me/events/{event_id}")
    assert deleted.status_code == 204
