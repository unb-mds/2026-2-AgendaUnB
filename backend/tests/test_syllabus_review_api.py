from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.database.models import PersonalEvent, Profile, Syllabus, SyllabusCandidate, SyllabusVersion
from src.middlewares.auth import CurrentUser


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


def _confirm(client, syllabus_id, payload, key="test-confirm-0001"):
    return client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json=payload,
        headers={"Idempotency-Key": key},
    )


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


def test_syllabus_detail_hides_another_users_private_plan(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, _, _ = _create_syllabus(TestSession, authenticated_user["value"].id)
    authenticated_user["value"] = CurrentUser(id=uuid4(), role="student")

    response = client.get(f"/api/v1/syllabus/{syllabus_id}")

    assert response.status_code == 404


def test_confirmation_hides_processing_state_of_another_users_private_plan(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, _, _ = _create_syllabus(TestSession, authenticated_user["value"].id, status="processing")
    authenticated_user["value"] = CurrentUser(id=uuid4(), role="student")

    response = _confirm(client, syllabus_id, {"candidates": [{
        "candidateId": str(uuid4()), "startsAt": "2026-11-10T10:00:00Z",
    }]}, "private-processing-01")

    assert response.status_code == 404


def test_confirmation_creates_only_selected_events_and_is_idempotent(api):
    client, TestSession, authenticated_user, _ = api
    syllabus_id, candidate_id, unselected_id = _create_syllabus(TestSession, authenticated_user["value"].id)
    before = client.get("/api/v1/me/events")
    assert before.status_code == 200
    assert before.json() == []
    payload = {
        "candidates": [
            {
                "candidateId": str(candidate_id),
                "title": "Prova 1 revisada",
                "type": "prova escrita",
                "startsAt": "2026-11-10T10:00:00-03:00",
            }
        ]
    }

    first = _confirm(client, syllabus_id, payload, "selected-action-001")
    second = _confirm(client, syllabus_id, payload, "selected-action-001")
    agenda = client.get("/api/v1/me/events")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["repeated"] is False
    assert second.json()["repeated"] is True
    assert first.json()["items"][0]["candidateId"] == str(candidate_id)
    assert first.json()["items"][0]["type"] == "prova escrita"
    assert agenda.status_code == 200
    assert len(agenda.json()) == 1
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
        assert session.get(SyllabusCandidate, candidate_id).kind == "prova escrita"
        assert session.get(SyllabusCandidate, unselected_id).status == "pendente"


def test_new_confirmation_action_revises_event_and_preserves_origin(api):
    client, sessions, authenticated_user, _ = api
    syllabus_id, candidate_id, _ = _create_syllabus(sessions, authenticated_user["value"].id)
    initial = _confirm(client, syllabus_id, {"candidates": [{
        "candidateId": str(candidate_id), "startsAt": "2026-11-10T09:00:00Z",
    }]}, "revision-initial-001")
    original = initial.json()["events"][0]

    revised = _confirm(client, syllabus_id, {"candidates": [{
        "candidateId": str(candidate_id),
        "title": "Prova revisada",
        "type": "avaliação escrita",
        "startsAt": "2026-11-12T12:00:00-03:00",
    }]}, "revision-explicit-001")

    assert revised.status_code == 200
    assert revised.json()["items"][0]["result"] == "ja_importado"
    event = revised.json()["events"][0]
    assert event["id"] == original["id"]
    assert event["title"] == "Prova revisada"
    assert event["starts_at"] != original["starts_at"]
    assert event["origin"]["candidateId"] == str(candidate_id)
    assert event["origin"]["excerpt"] == "A primeira prova será em 10/11."
    assert revised.json()["items"][0]["type"] == "avaliação escrita"


def test_confirmation_rejects_processing_plan_and_cross_plan_candidate(api):
    client, TestSession, authenticated_user, _ = api
    user_id = authenticated_user["value"].id
    processing_id, _, _ = _create_syllabus(TestSession, user_id, status="processing")
    failed_id, _, _ = _create_syllabus(TestSession, user_id, status="falha")
    completed_id, _, _ = _create_syllabus(TestSession, user_id)
    other_user_id = uuid4()
    _, foreign_candidate_id, _ = _create_syllabus(TestSession, other_user_id)

    pending = _confirm(client, processing_id, {"candidates": [{"candidateId": str(uuid4()), "startsAt": "2026-11-10T10:00:00Z"}]}, "processing-action-01")
    failed = _confirm(client, failed_id, {"candidates": [{"candidateId": str(uuid4()), "startsAt": "2026-11-10T10:00:00Z"}]}, "failed-action-001")
    crossed = _confirm(client, completed_id, {"candidates": [{"candidateId": str(foreign_candidate_id), "startsAt": "2026-11-10T10:00:00Z"}]}, "foreign-action-001")

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

    response = _confirm(
        client,
        syllabus_id,
        {
            "candidates": [
                {"candidateId": str(valid_candidate_id), "startsAt": "2026-11-10T10:00:00-03:00"},
                {"candidateId": str(undated_candidate_id)},
            ]
        },
        "partial-invalid-001",
    )

    assert response.status_code == 422
    with TestSession() as session:
        assert session.scalars(select(PersonalEvent)).all() == []
        assert session.get(SyllabusCandidate, valid_candidate_id).status == "pendente"


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



def test_retry_does_not_recreate_deleted_confirmed_event(api):
    client, sessions, auth, _ = api
    sid, cid, _ = _create_syllabus(sessions, auth["value"].id)
    payload = {"candidates": [{"candidateId": str(cid), "startsAt": "2026-11-10T09:00:00Z"}]}
    result = _confirm(client, sid, payload, "delete-retry-001")
    assert result.status_code == 200 and len(result.json()["events"]) == 1
    with sessions() as db:
        event = db.scalar(select(PersonalEvent).where(PersonalEvent.origin_candidate_id == cid))
        db.delete(event)
        db.commit()
    retry = _confirm(client, sid, payload, "delete-retry-001")
    assert retry.status_code == 200 and retry.json()["events"] == []
    assert retry.json()["items"][0]["removed"] is True
    detail = client.get(f"/api/v1/syllabus/{sid}")
    assert detail.status_code == 200
    reopened = next(row for row in detail.json()["candidates"] if row["id"] == str(cid))
    assert reopened["status"] == "pendente"
    explicit_reimport = _confirm(client, sid, payload, "delete-reimport-001")
    assert explicit_reimport.status_code == 200
    assert explicit_reimport.json()["items"][0]["removed"] is False
    assert len(explicit_reimport.json()["events"]) == 1


def test_idempotency_key_cannot_be_reused_with_different_content(api):
    client, sessions, auth, _ = api
    syllabus_id, candidate_id, _ = _create_syllabus(sessions, auth["value"].id)
    key = "same-action-key-001"
    first = _confirm(client, syllabus_id, {"candidates": [{
        "candidateId": str(candidate_id), "title": "Prova revisada", "startsAt": "2026-11-10T09:00:00Z",
    }]}, key)
    changed = _confirm(client, syllabus_id, {"candidates": [{
        "candidateId": str(candidate_id), "title": "Outro título", "startsAt": "2026-11-11T09:00:00Z",
    }]}, key)

    assert first.status_code == 200
    assert changed.status_code == 409
    with sessions() as db:
        events = db.scalars(select(PersonalEvent)).all()
        assert len(events) == 1
        assert events[0].title == "Prova revisada"


def test_discard_candidate_is_soft_and_blocks_confirmation(api):
    client, sessions, auth, _ = api
    syllabus_id, candidate_id, _ = _create_syllabus(sessions, auth["value"].id)

    discarded = client.delete(f"/api/v1/syllabus/{syllabus_id}/candidates/{candidate_id}")
    confirm = _confirm(client, syllabus_id, {"candidates": [{
        "candidateId": str(candidate_id), "startsAt": "2026-11-10T09:00:00Z",
    }]}, "discarded-item-001")
    detail = client.get(f"/api/v1/syllabus/{syllabus_id}")

    assert discarded.status_code == 204
    assert confirm.status_code == 422
    candidate = next(row for row in detail.json()["candidates"] if row["id"] == str(candidate_id))
    assert candidate["status"] == "descartado"
    with sessions() as db:
        assert db.scalar(select(PersonalEvent)) is None


def test_idempotency_key_is_required(api):
    client, sessions, auth, _ = api
    syllabus_id, candidate_id, _ = _create_syllabus(sessions, auth["value"].id)

    response = client.post(
        f"/api/v1/syllabus/{syllabus_id}/confirm",
        json={"candidates": [{"candidateId": str(candidate_id), "startsAt": "2026-11-10T09:00:00Z"}]},
    )

    assert response.status_code == 422


def test_confirmation_accepts_all_day_assignment_without_time(api):
    client, sessions, auth, _ = api
    syllabus_id, _, assignment_id = _create_syllabus(sessions, auth["value"].id)

    response = _confirm(client, syllabus_id, {"candidates": [{
        "candidateId": str(assignment_id),
        "title": "Trabalho final",
        "type": "trabalho",
        "all_day": True,
        "start_date": "2026-12-01",
        "end_date": "2026-12-02",
    }]}, "all-day-assignment-001")

    assert response.status_code == 200, response.text
    with sessions() as db:
        event = db.scalar(select(PersonalEvent).where(PersonalEvent.origin_candidate_id == assignment_id))
        assert event is not None
        assert event.all_day is True
        assert event.start_date.isoformat() == "2026-12-01"
        assert event.end_date.isoformat() == "2026-12-02"


def test_delete_syllabus_removes_private_plan_and_preserves_imported_event(api):
    client, sessions, auth, _ = api
    owner_id = auth["value"].id
    syllabus_id, candidate_id, _ = _create_syllabus(sessions, owner_id)
    with sessions() as db:
        version = SyllabusVersion(
            syllabus_id=syllabus_id,
            number=1,
            author_id=owner_id,
            author_role="student",
            visibility="privada",
        )
        db.add(version)
        db.flush()
        syllabus = db.get(Syllabus, syllabus_id)
        syllabus.approved_version_id = version.id
        for candidate in db.scalars(select(SyllabusCandidate).where(SyllabusCandidate.syllabus_id == syllabus_id)).all():
            candidate.version_id = version.id
        db.commit()

    confirmed = _confirm(client, syllabus_id, {"candidates": [{
        "candidateId": str(candidate_id),
        "startsAt": "2026-11-10T09:00:00Z",
    }]}, "delete-preserves-event-001")
    assert confirmed.status_code == 200

    response = client.delete(f"/api/v1/syllabus/{syllabus_id}")
    assert response.status_code == 204
    with sessions() as db:
        assert db.get(Syllabus, syllabus_id) is None
        assert db.scalars(select(SyllabusVersion).where(SyllabusVersion.syllabus_id == syllabus_id)).all() == []
        assert db.scalars(select(SyllabusCandidate).where(SyllabusCandidate.syllabus_id == syllabus_id)).all() == []
        event = db.scalar(select(PersonalEvent).where(PersonalEvent.origin_candidate_id == candidate_id))
        assert event is not None
        assert event.origin_version_id is None


def test_delete_syllabus_rejects_other_owner_processing_shared_and_third_party_revision(api):
    client, sessions, auth, _ = api
    owner_id = auth["value"].id
    other_id = uuid4()

    foreign_id, _, _ = _create_syllabus(sessions, other_id)
    assert client.delete(f"/api/v1/syllabus/{foreign_id}").status_code == 404

    processing_id, _, _ = _create_syllabus(sessions, owner_id, status="processando")
    assert client.delete(f"/api/v1/syllabus/{processing_id}").status_code == 409

    shared_id, _, _ = _create_syllabus(sessions, owner_id)
    with sessions() as db:
        db.add(SyllabusVersion(
            syllabus_id=shared_id,
            number=1,
            author_id=owner_id,
            author_role="student",
            visibility="compartilhada",
        ))
        db.commit()
    assert client.delete(f"/api/v1/syllabus/{shared_id}").status_code == 409

    derived_id, _, _ = _create_syllabus(sessions, owner_id)
    with sessions() as db:
        if db.get(Profile, other_id) is None:
            db.add(Profile(id=other_id, papel="professor", nome_completo="Docente Revisora"))
            db.flush()
        v1 = SyllabusVersion(
            syllabus_id=derived_id,
            number=1,
            author_id=owner_id,
            author_role="student",
            visibility="privada",
        )
        db.add(v1)
        db.flush()
        v2 = SyllabusVersion(
            syllabus_id=derived_id,
            number=2,
            author_id=other_id,
            author_role="professor",
            visibility="privada",
            source_version_id=v1.id,
        )
        db.add(v2)
        db.commit()
        v2_id = v2.id

    blocked = client.delete(f"/api/v1/syllabus/{derived_id}")
    assert blocked.status_code == 409
    with sessions() as db:
        assert db.get(Syllabus, derived_id) is not None
        assert db.get(SyllabusVersion, v2_id) is not None
