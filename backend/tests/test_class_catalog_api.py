from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
import httpx
from src.database.models import CatalogSync, Subject, ClassOffering, ClassFollow, PersonalEvent
from src.modules.classes.followw import FollowwClient, CatalogError, normalize


@pytest.fixture
def catalog(api):
    with api[1]() as db:
        run = CatalogSync(status="concluida", completed_at=datetime.now(timezone.utc), units=[{"id": 673, "code": "FCTE", "name": "Gama"}], periods=["2026.2"])
        db.add(run); db.flush()
        subject = Subject(code="FGA0108", name="Computação", unit="673")
        db.add(subject); db.flush()
        offer = ClassOffering(subject_id=subject.id, class_number="01", year=2026, semester=2, publication_id=run.id)
        db.add(offer); db.commit()
        return offer.id, run.id


def test_catalog_filters_follow_and_unfollow_preserves_events(api, catalog):
    client, sessions, user, _ = api
    oid, _ = catalog
    result = client.get('/api/v1/class-offerings?year=2026&semester=2&unit=FCTE&q=FGA0108').json()
    assert result['total'] == 1 and result['items'][0]['class_number'] == '01'
    assert client.get('/api/v1/class-offerings?q=inexistente').json()['items'] == []
    assert client.get('/api/v1/class-offerings?offset=1').json()['items'] == []
    assert client.get('/api/v1/class-offerings?semester=3').status_code == 422
    assert client.get('/api/v1/class-offerings?limit=101').status_code == 422
    for _ in range(2):
        assert client.put(f'/api/v1/me/class-offerings/{oid}').status_code == 204
    assert len(client.get('/api/v1/me/class-offerings').json()['items']) == 1
    with sessions() as db:
        event = PersonalEvent(user_id=user['value'].id, title='Prova importada', starts_at=datetime.now(timezone.utc))
        db.add(event); db.commit(); eid = event.id
    assert client.delete(f'/api/v1/me/class-offerings/{oid}').status_code == 204
    assert client.get('/api/v1/me/class-offerings').json()['items'] == []
    with sessions() as db:
        assert db.get(PersonalEvent, eid) is not None


def test_cache_failure_keeps_date_and_follows(api, catalog):
    client, sessions, _, _ = api
    oid, rid = catalog
    client.put(f'/api/v1/me/class-offerings/{oid}')
    before = client.get('/api/v1/class-offerings').json()
    with sessions() as db:
        db.add(CatalogSync(status='falha', completed_at=datetime.now(timezone.utc), started_at=datetime.now(timezone.utc)+timedelta(seconds=1)))
        db.commit()
    after = client.get('/api/v1/class-offerings').json()
    assert after['stale'] and after['source_updated_at'] == before['source_updated_at']
    assert len(client.get('/api/v1/me/class-offerings').json()['items']) == 1


def test_first_publication_and_required_offer(api):
    client = api[0]
    assert client.get('/api/v1/class-offerings').status_code == 503
    assert client.get('/api/v1/class-offerings/filters').status_code == 503
    assert client.post('/api/v1/syllabus/text', json={'text': 'Prova'}).status_code == 422
    assert client.post('/api/v1/syllabus/text', json={'text': 'Prova', 'offering_id': str(uuid4())}).status_code == 503


def test_plan_is_bound_to_exact_offer(api, catalog):
    client = api[0]
    oid, _ = catalog
    response = client.post('/api/v1/syllabus/text', json={'text': 'Prova em 20/11/2026', 'offering_id': str(oid), 'disciplina': 'Nome incorreto'})
    assert response.status_code == 202, response.text
    detail = client.get('/api/v1/syllabus/' + response.json()['id']).json()
    assert detail['offeringId'] == str(oid) and detail['disciplina'] == 'Computação'
    assert client.get(f'/api/v1/syllabus?offering_id={uuid4()}').json()['total'] == 0


def test_allowlist_filters_no_credentials_and_retry():
    requests, waits = [], []
    def handler(request):
        requests.append(request)
        assert 'authorization' not in request.headers and 'cookie' not in request.headers
        return httpx.Response(429, headers={'Retry-After': '2', 'Set-Cookie': 'secret=value'}) if len(requests) == 1 else httpx.Response(200, json=[])
    client = FollowwClient(transport=httpx.MockTransport(handler), sleep=waits.append)
    assert client.get('/public/classrooms', unit=673, semester='2026.2') == []
    assert len(requests) == 2 and 2 in waits
    for path, params in [('/private', {}), ('/public/subjects', {'semester': '2026.2'}), ('/public/classrooms', {'unit': 673, 'semester': '2026.3'})]:
        with pytest.raises(CatalogError): client.get(path, **params)


@pytest.mark.parametrize('status,body', [(302, []), (200, {}), (503, []), (200, ['bad'])])
def test_invalid_source(status, body):
    client = FollowwClient(transport=httpx.MockTransport(lambda r: httpx.Response(status, json=body)), sleep=lambda _: None)
    with pytest.raises(CatalogError): client.get('/public/classrooms/units')


def test_identity_uses_classroom_id_only_and_preserves_zero():
    live = [{'subject': {'code': 'FGA0108', 'name': 'Computação', 'sigaa_id': 99}, 'number': '01', 'semester': '2026.2'}]
    subjects = [{'code': 'FGA0108', 'unit': {'id': 673}, 'classrooms': [{'number': '01', 'semester': '2026.2', 'sigaa_id': 777}]}]
    rows, rejected = normalize(live, subjects, {'id': 673}, '2026.2')
    assert not rejected and rows[0]['oferta_origem_id'] == '777' and rows[0]['disciplina_origem_id'] == '99'
    assert rows[0]['turma'] == '01' and rows[0]['nivel'] is None


def test_authentication_and_user_isolation(api, catalog):
    from src.main import app
    from src.middlewares.auth import get_current_user, CurrentUser
    client, _, user, _ = api
    oid, _ = catalog
    client.put(f'/api/v1/me/class-offerings/{oid}')
    user['value'] = CurrentUser(id=uuid4(), role='student')
    assert client.get('/api/v1/me/class-offerings').json()['items'] == []
    assert client.get(f'/api/v1/class-offerings/{oid}/shared-plans').status_code == 403
    app.dependency_overrides.pop(get_current_user)
    assert client.get('/api/v1/class-offerings').status_code == 401
    assert client.get('/api/v1/me/class-offerings').status_code == 401


def test_retired_offering_blocks_follow_and_upload_but_preserves_link(api, catalog):
    client, sessions, _, _ = api
    oid, _ = catalog
    client.put(f'/api/v1/me/class-offerings/{oid}')
    with sessions() as db:
        db.add(CatalogSync(status='concluida', completed_at=datetime.now(timezone.utc)+timedelta(seconds=1)))
        db.commit()
    assert client.get('/api/v1/class-offerings').json()['items'] == []
    assert client.get('/api/v1/me/class-offerings').json()['items'][0]['available'] is False
    assert client.put(f'/api/v1/me/class-offerings/{oid}').status_code == 409
    assert client.post('/api/v1/syllabus/text', json={'text': 'Prova', 'offering_id': str(oid)}).status_code == 409


def test_shared_versions_do_not_expose_private_author_text(api, catalog):
    from src.database.models import Syllabus, SyllabusVersion
    client, sessions, _, _ = api
    oid, _ = catalog
    with sessions() as db:
        plan = Syllabus(user_id=uuid4(), offering_id=oid, prepared_pages=[{'pagina': 1, 'texto': 'SEGREDO'}])
        db.add(plan); db.flush()
        db.add_all([SyllabusVersion(syllabus_id=plan.id, number=1, author_id=plan.user_id, visibility='privada'),
                    SyllabusVersion(syllabus_id=plan.id, number=2, author_id=plan.user_id, visibility='compartilhada')])
        db.commit(); pid = plan.id
    client.put(f'/api/v1/me/class-offerings/{oid}')
    response = client.get(f'/api/v1/class-offerings/{oid}/shared-plans')
    assert response.status_code == 200 and response.json()['total'] == 1
    assert response.json()['items'][0]['number'] == 2 and 'SEGREDO' not in response.text
    assert client.get(f'/api/v1/syllabus/{pid}/text').status_code == 404
    client.delete(f'/api/v1/me/class-offerings/{oid}')
    assert client.get(f'/api/v1/class-offerings/{oid}/shared-plans').status_code == 403


def test_timeout_and_excessive_retry_after_are_bounded():
    calls = []
    def timeout(request):
        calls.append(request)
        assert request.extensions['timeout']['read'] == 20
        raise httpx.ReadTimeout('timeout')
    client = FollowwClient(transport=httpx.MockTransport(timeout), sleep=lambda _: None)
    with pytest.raises(CatalogError): client.get('/public/classrooms/units')
    assert len(calls) == 2
    calls.clear()
    def limited(request):
        calls.append(request)
        return httpx.Response(429, headers={'Retry-After': '61'})
    client = FollowwClient(transport=httpx.MockTransport(limited), sleep=lambda _: None)
    with pytest.raises(CatalogError): client.get('/public/classrooms/units')
    assert len(calls) == 1


def test_search_ignores_accents_and_returns_unit_label(api, catalog):
    from src.database.models import Subject
    with api[1]() as db:
        subject = db.query(Subject).one()
        subject.name = 'CÁLCULO 1'
        db.commit()
    first = api[0].get('/api/v1/class-offerings?q=calculo').json()
    second = api[0].get('/api/v1/class-offerings?q=cálculo').json()
    assert first['total'] == second['total'] == 1
    assert first['items'][0]['id'] == second['items'][0]['id']
    assert first['items'][0]['unit_name'] == 'Gama'
    assert first['items'][0]['unit_code'] == 'FCTE'

@pytest.mark.parametrize('search', ['estrutura de dados', 'estruturas de dados', 'dados estrutura', 'ESTRUTURA DE DADOS'])
def test_search_matches_plural_and_reordered_words(api, catalog, search):
    with api[1]() as db:
        subject = db.query(Subject).one()
        subject.name = 'Estruturas de Dados 1'
        db.commit()
    result = api[0].get('/api/v1/class-offerings', params={'q': search}).json()
    assert result['total'] == 1
    assert result['items'][0]['subject_name'] == 'Estruturas de Dados 1'
    assert api[0].get('/api/v1/class-offerings?q=estrutura+quimica').json()['total'] == 0
