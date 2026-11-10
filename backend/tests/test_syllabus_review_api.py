from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.database.models import PersonalEvent, Profile, Syllabus, SyllabusCandidate


def _create_syllabus(TestSession, user_id, *, status="completed"):
    syllabus_id = uuid4()
    with TestSession() as session:
        if session.get(Profile, user_id) is None:
            session.add(Profile(id=user_id, papel="student", nome_completo="Aluno Teste"))
        syllabus = Syllabus(
            id=syllabus_id,
            user_id=user_id,
            professor_id=user_id,
            file_name="plano.pdf",
            file_path=f"syllabus_files/{user_id}/plano.pdf",
            arquivo_url=f"syllabus_files/{user_id}/plano.pdf",
            file_size=100,
            file_type="pdf",
            status=status,
            extracted_events_count=2,
        )
        session.add(syllabus)
        session.flush()
        first = SyllabusCandidate(
            syllabus_id=syllabus_id,
            title="Prova 1",
            starts_at=datetime(2026, 11, 10, 9, tzinfo=timezone.utc),
            kind="prova",
            source_page=2,
            source_excerpt="A primeira prova será em 10/11.",
        )
        second = SyllabusCandidate(
            syllabus_id=syllabus_id,
            title="Trabalho final",
            starts_at=None,
            kind="trabalho",
            ambiguous=True,
            source_page=4,
            source_excerpt="Entrega do trabalho final em data a combinar.",
        )
        session.add_all([first, second])
        session.commit()
        return syllabus_id, first.id, second.id


def test_list_syllabi_is_paginated_and_scoped_to_owner(api):
    client, TestSession, authenticated_user, _ = api
    owner_id = authenticated_user["value"].id
    _create_syllabus(TestSession, owner_id)
    other_id = uuid4()
    _create_syllabus(TestSession, other_id)

    response = client.get("/api/v1/syllabus?limit=1&offset=0")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["fileName"] == "plano.pdf"


def test_syllabus_detail_includes_candidates_and_provenance(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, candidate_id, _ = _create_syllabus(TestSession, authenticated_user["value"].id)

    response = client.get(f"/api/v1/syllabus/{syllabus_id}")

    assert response.status_code == 200
    candidates = response.json()["candidates"]
    assert len(candidates) == 2
    first = next(candidate for candidate in candidates if candidate["id"] == str(candidate_id))
    assert first["sourcePage"] == 2
    assert first["sourceExcerpt"] == "A primeira prova será em 10/11."


def test_confirmation_creates_only_selected_events_and_is_idempotent(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, candidate_id, unselected_id = _create_syllabus(TestSession, authenticated_user["value"].id)
    payload = {
        "candidates": [
            {
                "candidateId": str(candidate_id),
                "title": "Prova 1 revisada",
                "startsAt": "2026-11-10T10:00:00-03:00",
            }
        ]
    }

    first = client.post(f"/api/v1/syllabus/{syllabus_id}/confirm", json=payload)
    second = client.post(f"/api/v1/syllabus/{syllabus_id}/confirm", json=payload)
    agenda = client.get("/api/v1/me/events")

    assert first.status_code == 200
    assert second.status_code == 200
    assert agenda.status_code == 200
    assert agenda.json()[0]["origin"]["candidateId"] == str(candidate_id)
    assert first.json()["events"][0]["id"] == second.json()["events"][0]["id"]
    event = first.json()["events"][0]
    assert event["title"] == "Prova 1 revisada"
    assert event["origin"] == {
        "syllabusId": str(syllabus_id),
        "candidateId": str(candidate_id),
        "page": 2,
        "excerpt": "A primeira prova será em 10/11.",
    }
    with TestSession() as session:
        saved = session.scalars(select(PersonalEvent)).all()
        assert len(saved) == 1
        assert saved[0].origin_candidate_id == candidate_id
        assert session.get(SyllabusCandidate, unselected_id).status == "pendente"


def test_confirmation_can_edit_title_date_and_type_without_losing_provenance(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, candidate_id, _ = _create_syllabus(TestSession, authenticated_user["value"].id)
    initial = client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json={
            "candidates": [{
                "candidateId": str(candidate_id),
                "title": "Prova revisada",
                "type": "prova escrita",
                "startsAt": "2026-11-11T10:00:00-03:00",
                "category": "Cultura",
            }],
        },
    )
    assert initial.status_code == 200
    initial_event = initial.json()["events"][0]

    revised = client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json={
            "candidates": [{
                "candidateId": str(candidate_id),
                "title": "Prova revisada novamente",
                "type": "avaliação escrita",
                "startsAt": "2026-11-12T12:00:00-03:00",
            }],
        },
    )

    assert revised.status_code == 200
    event = revised.json()["events"][0]
    assert event["id"] == initial_event["id"]
    assert event["title"] == "Prova revisada novamente"
    assert event["starts_at"] != initial_event["starts_at"]
    assert event["category"] == "Cultura"
    assert event["origin"]["candidateId"] == str(candidate_id)
    assert event["origin"]["excerpt"] == "A primeira prova será em 10/11."
    with TestSession() as session:
        assert session.get(SyllabusCandidate, candidate_id).kind == "avaliação escrita"


def test_deleted_import_requires_explicit_reimport(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, candidate_id, _ = _create_syllabus(TestSession, authenticated_user["value"].id)
    payload = {
        "candidates": [{
            "candidateId": str(candidate_id),
            "startsAt": "2026-11-10T10:00:00-03:00",
        }],
    }
    first = client.post(f"/api/v1/syllabus/{syllabus_id}/confirm", json=payload)
    event_id = first.json()["events"][0]["id"]
    deleted = client.delete(f"/api/v1/me/events/{event_id}")

    stale_retry = client.post(f"/api/v1/syllabus/{syllabus_id}/confirm", json=payload)
    explicit_reimport = client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json={"candidates": [{**payload["candidates"][0], "reimport": True}]},
    )

    assert first.status_code == 200
    assert deleted.status_code == 204
    assert stale_retry.status_code == 409
    assert explicit_reimport.status_code == 200
    assert explicit_reimport.json()["events"][0]["id"] != event_id
    assert explicit_reimport.json()["events"][0]["origin"]["candidateId"] == str(candidate_id)


def test_discarded_candidate_cannot_be_confirmed(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, candidate_id, _ = _create_syllabus(TestSession, authenticated_user["value"].id)

    discarded = client.delete(f"/api/v1/syllabus/{syllabus_id}/candidates/{candidate_id}")
    confirmed = client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json={"candidates": [{
            "candidateId": str(candidate_id),
            "startsAt": "2026-11-10T10:00:00-03:00",
        }]},
    )
    detail = client.get(f"/api/v1/syllabus/{syllabus_id}")

    assert discarded.status_code == 204
    assert confirmed.status_code == 409
    assert next(item for item in detail.json()["candidates"] if item["id"] == str(candidate_id))["status"] == "descartado"


def test_shared_syllabus_decisions_are_rejected_until_user_scoped_storage_exists(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, candidate_id, _ = _create_syllabus(TestSession, authenticated_user["value"].id)
    with TestSession() as session:
        session.get(Syllabus, syllabus_id).visibility = "compartilhado"
        session.commit()

    response = client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json={"candidates": [{
            "candidateId": str(candidate_id),
            "startsAt": "2026-11-10T10:00:00-03:00",
        }]},
    )

    assert response.status_code == 409
    with TestSession() as session:
        assert session.scalars(select(PersonalEvent)).all() == []
        assert session.get(SyllabusCandidate, candidate_id).status == "pendente"


def test_confirmation_rejects_processing_plan_and_cross_plan_candidate(api):
    client, TestSession, authenticated_user, _ = api
    user_id = authenticated_user["value"].id
    processing_id, _, _ = _create_syllabus(TestSession, user_id, status="processing")
    failed_id, _, _ = _create_syllabus(TestSession, user_id, status="falha")
    completed_id, _, _ = _create_syllabus(TestSession, user_id)
    other_user_id = uuid4()
    _, foreign_candidate_id, _ = _create_syllabus(TestSession, other_user_id)

    pending = client.post(
        f"/api/v1/syllabus/{processing_id}/confirm",
        json={"candidates": [{"candidateId": str(uuid4()), "startsAt": "2026-11-10T10:00:00Z"}]},
    )
    failed = client.post(
        f"/api/v1/syllabus/{failed_id}/confirm",
        json={"candidates": [{"candidateId": str(uuid4()), "startsAt": "2026-11-10T10:00:00Z"}]},
    )
    crossed = client.post(
        f"/api/v1/syllabus/{completed_id}/confirm",
        json={"candidates": [{"candidateId": str(foreign_candidate_id), "startsAt": "2026-11-10T10:00:00Z"}]},
    )

    assert pending.status_code == 409
    assert failed.status_code == 409
    assert crossed.status_code == 422
    with TestSession() as session:
        assert session.scalars(select(PersonalEvent)).all() == []


def test_confirmation_validation_failure_does_not_write_partial_events(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, valid_candidate_id, undated_candidate_id = _create_syllabus(
        TestSession, authenticated_user["value"].id
    )

    response = client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json={
            "candidates": [
                {"candidateId": str(valid_candidate_id), "startsAt": "2026-11-10T10:00:00-03:00"},
                {"candidateId": str(undated_candidate_id)},
            ]
        },
    )

    assert response.status_code == 422
    with TestSession() as session:
        assert session.scalars(select(PersonalEvent)).all() == []
        assert session.get(SyllabusCandidate, valid_candidate_id).status == "pendente"


def test_ambiguous_date_requires_explicit_correction(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, _, ambiguous_candidate_id = _create_syllabus(
        TestSession, authenticated_user["value"].id
    )
    base = {
        "candidateId": str(ambiguous_candidate_id),
        "title": "Trabalho final revisado",
    }

    missing_correction = client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json={"candidates": [base]},
    )
    corrected = client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json={"candidates": [{**base, "startsAt": "2026-12-01T23:59:00-03:00"}]},
    )

    assert missing_correction.status_code == 422
    assert "Corrija a data ambígua" in missing_correction.json()["detail"]
    assert corrected.status_code == 200


def test_personal_event_origin_candidate_is_unique(api):
    _, TestSession, authenticated_user, _ = api
    user_id = authenticated_user["value"].id
    syllabus_id, candidate_id, _ = _create_syllabus(TestSession, user_id)
    when = datetime(2026, 11, 10, 10, tzinfo=timezone.utc)

    with TestSession() as session:
        session.add_all(
            [
                PersonalEvent(
                    user_id=user_id,
                    title="Prova A",
                    starts_at=when,
                    origin_syllabus_id=syllabus_id,
                    origin_candidate_id=candidate_id,
                ),
                PersonalEvent(
                    user_id=user_id,
                    title="Prova B",
                    starts_at=when,
                    origin_syllabus_id=syllabus_id,
                    origin_candidate_id=candidate_id,
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            session.commit()

