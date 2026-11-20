from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from src.database.models import PersonalEvent, Profile, PublicEvent, Reminder, SavedPublicEvent
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


def test_removing_saved_event_cancels_future_reminder_and_history_separates_past_lists(saved_api):
    client, sessions, authenticated, _ = saved_api
    owner_id = authenticated['value'].id
    future_start = datetime.now(timezone.utc) + timedelta(days=5)
    past_public_start = datetime.now(timezone.utc) - timedelta(days=4)
    past_personal_start = datetime.now(timezone.utc) - timedelta(days=2)

    with sessions() as db:
        future_public = PublicEvent(
            author_id=owner_id,
            title='Congresso Futuro',
            description='Com lembrete agendado',
            starts_at=future_start,
            status='aprovado',
            external_url='https://example.org/congresso',
        )
        past_public_saved = PublicEvent(
            author_id=owner_id,
            title='Seminário Público Passado Salvo',
            description='Salvo pelo usuário',
            starts_at=past_public_start,
            status='aprovado',
            external_url='https://example.org/seminario-passado',
        )
        past_public_only_clicked = PublicEvent(
            author_id=owner_id,
            title='Evento Público Apenas Conferido',
            description='Aberto em Conferir evento sem salvar',
            starts_at=past_public_start,
            status='aprovado',
            external_url='https://example.org/apenas-conferido',
        )
        past_personal = PersonalEvent(
            user_id=owner_id,
            title='Prova Passada Privada',
            description='Compromisso privado encerrado',
            starts_at=past_personal_start,
        )
        future_personal = PersonalEvent(
            user_id=owner_id,
            title='Entrega Futura Privada',
            description='Compromisso privado futuro',
            starts_at=future_start,
        )
        db.add_all([
            future_public,
            past_public_saved,
            past_public_only_clicked,
            past_personal,
            future_personal,
        ])
        db.commit()
        future_public_id = future_public.id
        past_public_saved_id = past_public_saved.id
        past_public_clicked_id = past_public_only_clicked.id
        past_personal_id = past_personal.id

    # Salvar evento futuro agenda lembrete pendente; repetir PUT não duplica vínculo nem lembrete.
    for _ in range(2):
        res = client.put(f'/api/v1/me/saved-events/{future_public_id}')
        assert res.status_code == 200
        assert res.json() == {'saved': True}

    with sessions() as db:
        pending_count = db.scalar(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.user_id == owner_id,
                Reminder.public_event_id == future_public_id,
                Reminder.status == 'pendente',
            )
        )
        assert pending_count == 1

    # Salvar evento público passado (entra no histórico de públicos salvos, sem lembrete retroativo).
    assert client.put(f'/api/v1/me/saved-events/{past_public_saved_id}').status_code == 200
    with sessions() as db:
        retro_count = db.scalar(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.user_id == owner_id,
                Reminder.public_event_id == past_public_saved_id,
            )
        )
        assert retro_count == 0

    # Acionar Conferir evento em um evento passado NÃO o adiciona à agenda nem ao histórico.
    click_res = client.post(
        f'/api/v1/events/{past_public_clicked_id}/outbound-clicks',
        json={'clickId': str(uuid4())},
    )
    assert click_res.status_code == 200
    assert click_res.json()['outbound_clicks_count'] == 1

    history = client.get('/api/v1/me/events/history')
    assert history.status_code == 200
    body = history.json()
    assert [item['id'] for item in body['saved_public_events']] == [str(past_public_saved_id)]
    assert [item['id'] for item in body['personal_events']] == [str(past_personal_id)]

    # Remover o vínculo do evento futuro cancela o lembrete pendente; repetir DELETE é seguro (204).
    for _ in range(2):
        assert client.delete(f'/api/v1/me/saved-events/{future_public_id}').status_code == 204

    with sessions() as db:
        remaining_reminders = db.scalar(
            select(func.count())
            .select_from(Reminder)
            .where(
                Reminder.user_id == owner_id,
                Reminder.public_event_id == future_public_id,
                Reminder.status == 'pendente',
            )
        )
        assert remaining_reminders == 0

    # Remover o vínculo do evento passado retira-o do histórico de públicos salvos, mantendo o privado.
    assert client.delete(f'/api/v1/me/saved-events/{past_public_saved_id}').status_code == 204
    after_unsave = client.get('/api/v1/me/events/history').json()
    assert after_unsave['saved_public_events'] == []
    assert [item['id'] for item in after_unsave['personal_events']] == [str(past_personal_id)]
