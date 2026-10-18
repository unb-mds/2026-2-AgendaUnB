from uuid import uuid4

from sqlalchemy import select

from src.database.models import PublicEvent
from src.middlewares.auth import CurrentUser, get_current_user
from src.main import app


def payload():
    return {"title": "Encontro de estudantes", "description": "Conversa no campus",
            "starts_at": "2026-11-20T14:00:00-03:00"}


def test_student_suggestion_is_pending_and_not_public(api):
    client, sessions, user, _ = api
    response = client.post('/api/v1/suggestions', json=payload())
    assert response.status_code == 201
    with sessions() as db:
        event = db.scalar(select(PublicEvent))
        assert event.status == 'pendente'
        assert event.author_id == user['value'].id
    assert client.get('/api/v1/events').json() == []
    assert client.get('/api/v1/events/' + response.json()['id']).status_code == 404


def test_suggestion_cannot_forge_approval_or_author(api):
    client, sessions, user, _ = api
    response = client.post('/api/v1/suggestions', json={**payload(), 'status': 'aprovado', 'author_id': str(uuid4())})
    assert response.status_code == 201
    with sessions() as db:
        event = db.scalar(select(PublicEvent))
        assert event.status == 'pendente'
        assert event.author_id == user['value'].id


def test_suggestion_requires_student_and_valid_input(api):
    client, _, user, _ = api
    assert client.post('/api/v1/suggestions', json={**payload(), 'title': '  '}).status_code == 422
    assert client.post('/api/v1/suggestions', json={**payload(), 'external_url': 'javascript:alert(1)'}).status_code == 422
    for role in ('professor', 'admin'):
        user['value'] = CurrentUser(id=uuid4(), role=role)
        assert client.post('/api/v1/suggestions', json=payload()).status_code == 403
    app.dependency_overrides.pop(get_current_user)
    assert client.post('/api/v1/suggestions', json=payload()).status_code == 401
