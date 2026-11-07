from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.database.models import Profile, PublicEvent, SavedPublicEvent
from src.main import app
from src.middlewares.auth import CurrentUser, get_current_user


@pytest.fixture
def saved_api(api):
    client, sessions, authenticated, ids = api
    with sessions() as db:
        # Exercita FKs e ON DELETE CASCADE, também no SQLite de testes.
        db.connection().exec_driver_sql('PRAGMA foreign_keys=ON')
        db.add(Profile(id=authenticated['value'].id, papel='student', nome_completo='Autor'))
        db.commit()
        public = PublicEvent(
            author_id=authenticated['value'].id, title='Evento público', description='Descrição',
            starts_at=datetime(2026, 10, 20, 15, tzinfo=timezone.utc),
            status='aprovado', location='Auditório', external_url='https://example.org/evento',
            campus_id=ids['campus'], category_id=ids['category'],
        )
        db.add(public)
        db.commit()
        event_id = public.id
    yield client, sessions, authenticated, event_id


def test_save_is_idempotent_and_preserves_public_data(saved_api):
    client, sessions, _, event_id = saved_api
    path = f'/api/v1/me/saved-events/{event_id}'
    assert client.get(path).json() == {'saved': False}
    for _ in range(2):
        response = client.put(path)
        assert response.status_code == 200
        assert response.json() == {'saved': True}
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(SavedPublicEvent)) == 1
        event = db.get(PublicEvent, event_id)
        event.title = 'Título atualizado'
        db.commit()
    events = client.get('/api/v1/me/saved-events').json()
    assert len(events) == 1
    assert events[0]['title'] == 'Título atualizado'
    assert events[0]['location'] == 'Auditório'
    assert events[0]['external_url'] == 'https://example.org/evento'
    assert events[0]['organizer_name'] == 'Autor'
    assert client.get('/api/v1/me/events').json() == []
    assert client.get(path).json() == {'saved': True}


def test_users_only_remove_their_own_links(saved_api):
    client, sessions, authenticated, event_id = saved_api
    path = f'/api/v1/me/saved-events/{event_id}'
    owner = authenticated['value']
    client.put(path)
    other = CurrentUser(id=uuid4(), role='student')
    with sessions() as db:
        db.add(Profile(id=other.id, papel='student'))
        db.commit()
    authenticated['value'] = other
    assert client.get('/api/v1/me/saved-events').json() == []
    assert client.get(path).json() == {'saved': False}
    assert client.delete(path).status_code == 204
    assert client.put(path).status_code == 200
    assert client.delete(f'/api/v1/events/{event_id}').status_code == 403
    assert client.put(f'/api/v1/me/events/{event_id}', json={
        'title': 'Tentativa de edição', 'starts_at': '2026-10-20T15:00:00Z',
    }).status_code == 404
    authenticated['value'] = owner
    assert client.get(path).json() == {'saved': True}
    assert client.delete(path).status_code == 204
    assert client.delete(path).status_code == 204
    assert client.get(f'/api/v1/events/{event_id}').status_code == 200
    authenticated['value'] = other
    assert client.get(path).json() == {'saved': True}


def test_database_rejects_duplicate_links(saved_api):
    client, sessions, authenticated, event_id = saved_api
    client.put(f'/api/v1/me/saved-events/{event_id}')
    with sessions() as db:
        db.add(SavedPublicEvent(user_id=authenticated['value'].id, event_id=event_id))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert db.scalar(select(func.count()).select_from(SavedPublicEvent)) == 1


def test_unapproved_missing_and_deleted_events(saved_api):
    client, sessions, authenticated, event_id = saved_api
    path = f'/api/v1/me/saved-events/{event_id}'
    assert client.put(f'/api/v1/me/saved-events/{uuid4()}').status_code == 404
    client.put(path)
    with sessions() as db:
        db.get(PublicEvent, event_id).status = 'pendente'
        db.commit()
    assert client.put(path).status_code == 404
    assert client.get(path).json() == {'saved': False}
    assert client.get('/api/v1/me/saved-events').json() == []
    authenticated['value'] = CurrentUser(id=authenticated['value'].id, role='admin')
    assert client.delete(f'/api/v1/events/{event_id}').status_code == 204
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(SavedPublicEvent)) == 0


def test_saved_endpoints_require_authentication(saved_api):
    client, _, _, event_id = saved_api
    override = app.dependency_overrides.pop(get_current_user)
    try:
        assert client.get('/api/v1/me/saved-events').status_code == 401
        path = f'/api/v1/me/saved-events/{event_id}'
        assert client.get(path).status_code == 401
        assert client.put(path).status_code == 401
        assert client.delete(path).status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = override
