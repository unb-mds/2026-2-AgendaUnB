from datetime import datetime, timezone
from uuid import uuid4

from src.database.models import PublicEvent


def test_admin_operations_are_not_exposed_by_fastapi(api):
    client, _, _, _ = api
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(path.startswith("/api/v1/admin") for path in paths)


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
    assert "stale-while-revalidate" in response.headers.get("cache-control", "")
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

    detail = client.get(f"/api/v1/events/{event_id}")
    assert detail.status_code == 200
    assert "stale-while-revalidate" in detail.headers.get("cache-control", "")
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


def test_professor_cannot_delete_another_authors_public_event_but_admin_can(api):
    client, session_factory, authenticated_user, ids = api
    with session_factory() as db:
        event = make_public_event(ids)
        db.add(event)
        db.commit()
        event_id = event.id

    actor = authenticated_user["value"]
    authenticated_user["value"] = actor.__class__(id=actor.id, role="professor")
    assert client.delete(f"/api/v1/events/{event_id}").status_code == 403
    assert client.get(f"/api/v1/events/{event_id}").status_code == 200

    authenticated_user["value"] = actor.__class__(id=actor.id, role="admin")
    assert client.delete(f"/api/v1/events/{event_id}").status_code == 204
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


def test_personal_event_with_empty_strings_normalizes_to_none(api):
    client, _, _, _ = api
    payload = {
        "title": "Estudo em grupo",
        "starts_at": "2026-10-20T10:00:00Z",
        "campus": "  ",
        "category": "",
        "description": "   ",
        "location": "",
    }
    response = client.post("/api/v1/me/events", json=payload)
    assert response.status_code == 201
    event = response.json()
    assert event["title"] == "Estudo em grupo"
    assert event["campus"] is None
    assert event["category"] is None
    assert event["description"] is None


def test_personal_event_validation_error_returns_clean_message(api):
    client, _, _, _ = api
    payload = {
        "title": "AB",
        "starts_at": "2026-10-20T10:00:00Z",
    }
    response = client.post("/api/v1/me/events", json=payload)
    assert response.status_code == 422
    data = response.json()
    assert "Título: deve ter pelo menos 3 caracteres" in data["detail"]


def test_public_event_exposes_provenance_without_internal_metadata(api):
    client, session_factory, _, ids = api
    with session_factory() as db:
        event = make_public_event(
            ids,
            title="Evento Coletado da Notícias",
            source="agenda_unb_noticias",
            source_url="https://noticias.unb.br/component/agenda/agenda/999",
            source_hash="sha256-secreto-interno-123456",
        )
        db.add(event)
        db.commit()
        event_id = event.id

    detail = client.get(f"/api/v1/events/{event_id}")
    assert detail.status_code == 200
    data = detail.json()
    assert data["source"] == "agenda_unb_noticias"
    assert data["source_url"] == "https://noticias.unb.br/component/agenda/agenda/999"
    # Campos internos não devem ser vazados pela API pública
    assert "source_hash" not in data
    assert "fonte_hash" not in data
    assert "coletado_em" not in data
    assert "motivo_revisao" not in data
    assert "campos_editados" not in data


def test_all_day_and_multi_day_interval_events_and_filter_intersection(api):
    client, _, authenticated_user, _ = api
    actor = authenticated_user["value"]
    authenticated_user["value"] = actor.__class__(id=actor.id, role="professor")

    created = client.post(
        "/api/v1/events",
        json={
            "title": "Semana Universitária UnB",
            "description": "Programação em todos os campi",
            "all_day": True,
            "start_date": "2026-11-18",
            "end_date": "2026-11-21",
            "campus": "Darcy Ribeiro (Plano Piloto)",
            "category": "Cultura",
            "location": "ICC Centro",
        },
    )
    assert created.status_code == 201
    event_data = created.json()
    assert event_data["all_day"] is True
    assert event_data["start_date"] == "2026-11-18"
    assert event_data["end_date"] == "2026-11-21"

    # Dia intermediário intersecta o intervalo [18, 21)
    middle = client.get(
        "/api/v1/events",
        params={
            "startDate": "2026-11-19T00:00:00-03:00",
            "endDate": "2026-11-19T23:59:59-03:00",
        },
    )
    assert middle.status_code == 200
    assert any(item["id"] == event_data["id"] for item in middle.json())

    # A partir do dia exclusivo 21, o evento não deve aparecer
    after = client.get(
        "/api/v1/events",
        params={"startDate": "2026-11-21T00:00:00-03:00"},
    )
    assert after.status_code == 200
    assert all(item["id"] != event_data["id"] for item in after.json())

    # Misturar all_day com starts_at ou intervalo inválido retorna 422
    assert (
        client.post(
            "/api/v1/events",
            json={
                "title": "Inválido misto",
                "all_day": True,
                "start_date": "2026-11-18",
                "starts_at": "2026-11-18T10:00:00-03:00",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "title": "Fim menor que início",
                "all_day": True,
                "start_date": "2026-11-18",
                "end_date": "2026-11-18",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/events",
            json={
                "title": "Horário invertido",
                "all_day": False,
                "starts_at": "2026-11-18T14:00:00-03:00",
                "ends_at": "2026-11-18T13:00:00-03:00",
            },
        ).status_code
        == 422
    )


def test_personal_event_preserves_location_and_all_day_interval(api):
    client, _, _, _ = api
    created = client.post(
        "/api/v1/me/events",
        json={
            "title": "Monitoria de Cálculo",
            "description": "Revisão P2",
            "starts_at": "2026-11-20T14:00:00-03:00",
            "ends_at": "2026-11-20T16:00:00-03:00",
            "campus": "Darcy Ribeiro (Plano Piloto)",
            "category": "Cultura",
            "location": "ICC Sul - Sala 12",
        },
    )
    assert created.status_code == 201
    event_id = created.json()["id"]
    assert created.json()["location"] == "ICC Sul - Sala 12"
    assert created.json()["ends_at"] is not None

    updated = client.put(
        f"/api/v1/me/events/{event_id}",
        json={
            "title": "Viagem de Campo",
            "all_day": True,
            "start_date": "2026-11-22",
            "end_date": "2026-11-25",
            "location": "FAL - Área Experimental",
        },
    )
    assert updated.status_code == 200
    body = client.get(f"/api/v1/me/events/{event_id}").json()
    assert body["all_day"] is True
    assert body["start_date"] == "2026-11-22"
    assert body["end_date"] == "2026-11-25"
    assert body["location"] == "FAL - Área Experimental"


def test_outbound_clicks_are_deduplicated_and_independent_of_saved_events(api):
    client, session_factory, _, ids = api
    with session_factory() as db:
        with_url = make_public_event(
            ids,
            title="Evento com link oficial",
            external_url="https://noticias.unb.br/evento/1",
        )
        without_url = make_public_event(ids, title="Evento sem link", external_url=None)
        pending = make_public_event(
            ids,
            title="Evento pendente",
            status="pendente",
            external_url="https://noticias.unb.br/evento/2",
        )
        db.add_all([with_url, without_url, pending])
        db.commit()
        with_url_id = with_url.id
        without_url_id = without_url.id
        pending_id = pending.id

    click_1 = str(uuid4())
    click_2 = str(uuid4())

    first = client.post(
        f"/api/v1/events/{with_url_id}/outbound-clicks",
        json={"click_id": click_1},
    )
    assert first.status_code == 200
    assert first.json() == {
        "external_url": "https://noticias.unb.br/evento/1",
        "outbound_clicks_count": 1,
        "incremented": True,
    }

    # Mesmo click_id não duplica contador
    repeated = client.post(
        f"/api/v1/events/{with_url_id}/outbound-clicks",
        json={"click_id": click_1},
    )
    assert repeated.status_code == 200
    assert repeated.json()["outbound_clicks_count"] == 1
    assert repeated.json()["incremented"] is False

    # Novo click_id incrementa
    second = client.post(
        f"/api/v1/events/{with_url_id}/outbound-clicks",
        json={"click_id": click_2},
    )
    assert second.status_code == 200
    assert second.json()["outbound_clicks_count"] == 2
    assert second.json()["incremented"] is True

    # Conferir evento não salva o evento na agenda do usuário
    assert client.get("/api/v1/me/saved-events").json() == []

    # Evento sem URL retorna 422; pendente/inexistente retorna 404
    assert (
        client.post(
            f"/api/v1/events/{without_url_id}/outbound-clicks",
            json={"click_id": str(uuid4())},
        ).status_code
        == 422
    )
    assert (
        client.post(
            f"/api/v1/events/{pending_id}/outbound-clicks",
            json={"click_id": str(uuid4())},
        ).status_code
        == 404
    )


def test_categories_management_is_restricted_to_admin(api):
    client, session_factory, authenticated_user, ids = api
    with session_factory() as db:
        db.add(make_public_event(ids))
        db.commit()

    # Leitura pública
    listing = client.get("/api/v1/categories")
    assert listing.status_code == 200
    assert any(cat["id"] == str(ids["category"]) for cat in listing.json())

    # Student e professor recebem 403 ao criar ou excluir categorias
    actor = authenticated_user["value"]
    for role in ("student", "professor"):
        authenticated_user["value"] = actor.__class__(id=actor.id, role=role)
        assert (
            client.post("/api/v1/categories", json={"name": "Seminário"}).status_code
            == 403
        )
        assert (
            client.delete(f"/api/v1/categories/{ids['category']}").status_code == 403
        )

    # Admin gerencia categorias
    authenticated_user["value"] = actor.__class__(id=actor.id, role="admin")
    created = client.post(
        "/api/v1/categories",
        json={"name": "Seminário", "color": "#008BFF"},
    )
    assert created.status_code == 201
    new_id = created.json()["id"]
    assert created.json()["color"] == "#008bff"

    # Nome duplicado retorna 409
    assert (
        client.post("/api/v1/categories", json={"name": "seminário"}).status_code == 409
    )

    # Categoria vinculada a evento retorna 409 ao tentar excluir
    assert client.delete(f"/api/v1/categories/{ids['category']}").status_code == 409

    # Categoria sem vínculos é excluída com 204
    assert client.delete(f"/api/v1/categories/{new_id}").status_code == 204


