"""Exercise the real multipart path and parser at the hosting boundary."""
from uuid import UUID

import pytest
from sqlalchemy import select
from src.database.models import Profile, Syllabus
from syllabus_samples import make_pdf, pad_pdf

pytestmark = pytest.mark.usefixtures('published_offering')
LIMIT = 10 * 1024 * 1024
OFFERING = '70000000-0000-4000-8000-000000000071'


def pdf_at_limit():
    return pad_pdf(make_pdf(['Prova sintetica - 12/11/2026.']), LIMIT)


def test_authorized_10_mib_upload_is_private_and_discards_original(api):
    client, sessions, auth, _ = api
    with sessions() as db:
        db.add(Profile(id=auth['value'].id, papel='student'))
        db.commit()
    content = pdf_at_limit()
    assert len(content) == LIMIT
    response = client.post('/api/v1/syllabus/upload', data={'offering_id': OFFERING}, files={'file': ('synthetic.pdf', content, 'application/pdf')})
    assert response.status_code == 202, response.text
    assert response.json()['filePath'] is None
    with sessions() as db:
        plan = db.get(Syllabus, UUID(response.json()['id']))
        assert plan.file_path is None
        assert plan.authorized_at is None
        assert plan.approved_pages is None
        assert 'Prova sintetica' in plan.prepared_pages[0]['texto']


def test_upload_above_10_mib_does_not_create_a_plan(api):
    response = api[0].post('/api/v1/syllabus/upload', data={'offering_id': OFFERING}, files={'file': ('synthetic.pdf', pdf_at_limit() + b'0', 'application/pdf')})
    assert response.status_code == 413
    with api[1]() as db:
        assert db.scalar(select(Syllabus)) is None
