from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from src.database.models import CourseEnrollment, CourseOffer, Profile, Syllabus


def _offer(**overrides):
    values = {
        "source": "sigaa",
        "course_code": "MDS001",
        "course_name": "Métodos de Desenvolvimento de Software",
        "class_number": "A",
        "period": "2026/2",
        "unit": "FCTE",
        "level": "graduação",
    }
    values.update(overrides)
    return CourseOffer(**values)


def test_same_course_offerings_are_separate_by_period(api):
    _, TestSession, authenticated_user, _ = api
    with TestSession() as session:
        first = _offer(source_offer_id="sigaa-100", period="2026/1")
        second = _offer(source_offer_id="sigaa-100", period="2026/2")
        session.add_all([first, second])
        session.commit()

        assert first.id != second.id


def test_duplicate_source_offer_and_period_is_rejected(api):
    _, TestSession, _, _ = api
    with TestSession() as session:
        session.add(_offer(source_offer_id="sigaa-100"))
        session.commit()
        session.add(_offer(source_offer_id="sigaa-100"))
        with pytest.raises(IntegrityError):
            session.commit()


def test_fallback_offer_key_deduplicates_but_keeps_semesters_distinct(api):
    _, TestSession, _, _ = api
    with TestSession() as session:
        session.add(_offer())
        session.commit()
        session.add(_offer(course_name="Outra descrição"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(_offer(period="2027/1"))
        session.commit()


def test_user_has_only_one_link_per_offer(api):
    _, TestSession, authenticated_user, _ = api
    user_id = authenticated_user["value"].id
    with TestSession() as session:
        session.add(Profile(id=user_id, papel="student", nome_completo="Aluno Teste"))
        offer = _offer()
        session.add(offer)
        session.flush()
        session.add(CourseEnrollment(user_id=user_id, offer_id=offer.id))
        session.commit()

        session.add(CourseEnrollment(user_id=user_id, offer_id=offer.id))
        with pytest.raises(IntegrityError):
            session.commit()


def test_syllabus_defaults_to_private_first_version_and_can_reference_offer(api):
    _, TestSession, authenticated_user, _ = api
    user_id = authenticated_user["value"].id
    with TestSession() as session:
        profile = Profile(id=user_id, papel="student", nome_completo="Aluno Teste")
        offer = _offer()
        session.add_all([profile, offer])
        session.flush()
        plan = Syllabus(
            user_id=user_id,
            author_id=user_id,
            offer_id=offer.id,
            file_name="plano.pdf",
            file_path=f"syllabus_files/{user_id}/{uuid4()}_plano.pdf",
        )
        session.add(plan)
        session.commit()

        assert plan.version == 1
        assert plan.visibility == "privado"
        assert plan.offer_id == offer.id
