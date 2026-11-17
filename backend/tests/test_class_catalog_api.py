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
    client.put(f'/api/v1/me/class-offerings/{oid}')
    response = client.post('/api/v1/syllabus/text', json={'text': 'Prova em 20/11/2026', 'offering_id': str(oid), 'disciplina': 'Nome incorreto'})
    assert response.status_code == 202, response.text
    detail = client.get('/api/v1/syllabus/' + response.json()['id']).json()
    assert detail['offeringId'] == str(oid) and detail['disciplina'] == 'Computação'
    assert client.get(f'/api/v1/syllabus?offering_id={uuid4()}').json()['total'] == 0


@pytest.mark.parametrize('source', ['pdf', 'text'])
def test_plan_requires_own_current_follow(api, catalog, source):
    from sqlalchemy import func, select
    from src.database.models import Syllabus
    from src.middlewares.auth import CurrentUser
    client, sessions, auth, _ = api
    oid, _ = catalog

    def send():
        if source == 'text':
            return client.post('/api/v1/syllabus/text', json={'offering_id': str(oid), 'text': 'Prova em 20/11/2026'})
        return client.post('/api/v1/syllabus/upload', data={'offering_id': str(oid)},
                           files={'file': ('plano.pdf', b'not parsed without permission', 'application/pdf')})

    assert send().status_code == 403
    assert client.put(f'/api/v1/me/class-offerings/{oid}').status_code == 204
    owner = auth['value']
    auth['value'] = CurrentUser(id=uuid4(), role='student')
    assert send().status_code == 403  # Another user's follow grants no permission.
    auth['value'] = owner
    assert client.delete(f'/api/v1/me/class-offerings/{oid}').status_code == 204
    assert send().status_code == 403
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Syllabus)) == 0


def test_follow_removed_during_pdf_extraction_blocks_persistence(api, published_offering, monkeypatch):
    from sqlalchemy import delete, select, func
    from src.database.models import Syllabus
    from syllabus_samples import make_pdf
    client, sessions, auth, _ = api

    def extract(*args):
        with sessions() as db:
            db.execute(delete(ClassFollow).where(ClassFollow.user_id == auth['value'].id))
            db.commit()
        return [{'pagina': 1, 'texto': 'Prova em 20/11/2026'}]

    monkeypatch.setattr('src.modules.syllabus.router.extract_pdf_isolated', extract)
    response = client.post('/api/v1/syllabus/upload', data={'offering_id': published_offering},
                           files={'file': ('plano.pdf', make_pdf(['Prova em 20/11/2026']), 'application/pdf')})
    assert response.status_code == 403
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Syllabus)) == 0


def test_allowlist_filters_no_credentials_and_retry():
    requests, waits = [], []
    def handler(request):
        requests.append(request)
        assert request.url.scheme == 'https'
        assert request.url.host == 'followw.app'
        assert request.url.path == '/api/public/classrooms'
        assert dict(request.url.params) == {'unit': '673', 'semester': '2026.2'}
        assert 'authorization' not in request.headers and 'cookie' not in request.headers
        return httpx.Response(429, headers={'Retry-After': '2', 'Set-Cookie': 'secret=value'}) if len(requests) == 1 else httpx.Response(200, json=[])
    client = FollowwClient(transport=httpx.MockTransport(handler), sleep=waits.append)
    assert client.get('/public/classrooms', unit=673, semester='2026.2') == []
    assert len(requests) == 2 and 2 in waits
    for path, params in [('/private', {}), ('/public/subjects', {'semester': '2026.2'}), ('/public/classrooms', {'unit': 673, 'semester': '2026.3'})]:
        with pytest.raises(CatalogError): client.get(path, **params)


@pytest.mark.parametrize('status,body', [(302, []), (404, 'DEPLOYMENT_NOT_FOUND'), (200, {}), (503, []), (200, ['bad'])])
def test_invalid_source(status, body):
    client = FollowwClient(transport=httpx.MockTransport(lambda r: httpx.Response(status, json=body)), sleep=lambda _: None)
    with pytest.raises(CatalogError) as failure:
        client.get('/public/classrooms/units')
    if status != 200:
        assert failure.value.path == '/public/classrooms/units'
        assert failure.value.status == status


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


def test_catalog_retries_two_transient_timeouts_before_accepting_valid_empty_unit():
    waits = []
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) < 3:
            raise httpx.ReadTimeout('timeout')
        return httpx.Response(200, json=[])

    client = FollowwClient(transport=httpx.MockTransport(handler), sleep=waits.append)
    assert client.get('/public/classrooms', unit=1877, semester='2026.2') == []
    assert len(calls) == 3
    assert 1 in waits and 2 in waits


def test_timeout_and_excessive_retry_after_are_bounded():
    calls = []
    def timeout(request):
        calls.append(request)
        assert request.extensions['timeout']['read'] == 30
        raise httpx.ReadTimeout('timeout')
    client = FollowwClient(transport=httpx.MockTransport(timeout), sleep=lambda _: None)
    with pytest.raises(CatalogError): client.get('/public/classrooms/units')
    assert len(calls) == 3
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


def test_extracted_plan_auto_shares_and_follower_imports_votes_revises_and_withdraws(api, catalog):
    from datetime import date, time as dt_time
    from sqlalchemy import select
    from src.database.models import PersonalEvent, Profile, Syllabus, SyllabusCandidate, SyllabusVersion
    from src.middlewares.auth import CurrentUser

    client, sessions, user, _ = api
    oid, _ = catalog
    author_id = user['value'].id
    follower_id = uuid4()
    prof_id = uuid4()
    outsider_id = uuid4()

    with sessions() as db:
        db.add_all([
            Profile(id=author_id, papel='student', nome_completo='Maria Autora'),
            Profile(id=follower_id, papel='student', nome_completo='João Seguidor'),
            Profile(id=prof_id, papel='professor', nome_completo='Prof. Carlos'),
            Profile(id=outsider_id, papel='student', nome_completo='Sem Vínculo'),
        ])
        plan = Syllabus(
            user_id=author_id,
            offering_id=oid,
            file_name='plano.pdf',
            status='concluido',
            extracted_events_count=2,
        )
        db.add(plan)
        db.flush()
        v1 = SyllabusVersion(
            syllabus_id=plan.id,
            number=1,
            author_id=author_id,
            author_role='student',
            visibility='privada',
        )
        db.add(v1)
        db.flush()
        plan.approved_version_id = v1.id
        c1 = SyllabusCandidate(
            syllabus_id=plan.id,
            version_id=v1.id,
            order=0,
            title='Prova 1',
            kind='prova',
            data_sugerida=date(2026, 11, 20),
            hora_sugerida=dt_time(14, 0),
            source_page=1,
            source_excerpt='Prova 1 dia 20/11',
            status='pendente',
        )
        c2 = SyllabusCandidate(
            syllabus_id=plan.id,
            version_id=v1.id,
            order=1,
            title='Trabalho Final',
            kind='trabalho',
            data_sugerida=date(2026, 12, 10),
            source_page=2,
            source_excerpt='Entrega 10/12',
            status='pendente',
        )
        db.add_all([c1, c2])
        db.commit()
        pid, v1_id, c1_id = str(plan.id), str(v1.id), str(c1.id)

    # Ao consultar o plano concluído, a versão inicial (v1) é compartilhada automaticamente para a turma (ADR-010).
    detail = client.get(f'/api/v1/syllabus/{pid}')
    assert detail.status_code == 200

    # Novo seguidor abre a turma e importa sem reenviar arquivo.
    user['value'] = CurrentUser(id=follower_id, role='student')
    assert client.put(f'/api/v1/me/class-offerings/{oid}').status_code == 204
    shared = client.get(f'/api/v1/class-offerings/{oid}/shared-plans')
    assert shared.status_code == 200
    assert shared.json()['membership_type'] == 'autodeclarado'
    items = shared.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == v1_id
    assert items[0]['is_default'] is True
    assert items[0]['author_name'] == 'Maria Autora'
    assert items[0]['author_role'] == 'student'
    assert items[0]['can_edit'] is True
    assert items[0]['has_imported_update'] is False

    imported = client.post(
        f'/api/v1/syllabus/{pid}/confirm',
        headers={'Idempotency-Key': 'import-shared-001'},
        json={
            'versionId': v1_id,
            'candidates': [{'candidateId': c1_id, 'startsAt': '2026-11-20T14:00:00-03:00', 'type': 'prova'}],
        },
    )
    assert imported.status_code == 200, imported.text
    original_event_id = imported.json()['events'][0]['id']

    # Visitante/não seguidor é recusado ao tentar votar ou revisar.
    user['value'] = CurrentUser(id=outsider_id, role='student')
    assert client.put(f'/api/v1/syllabus/{pid}/versions/{v1_id}/vote', json={'value': 'confirm'}).status_code == 403
    assert client.post(
        f'/api/v1/syllabus/{pid}/versions',
        json={'sourceVersionId': v1_id, 'share': True, 'candidates': [{'title': 'Prova X', 'type': 'prova', 'suggestedDate': '2026-11-21'}]},
    ).status_code == 403

    # Professor segue e cria uma revisão (v2), e o seguidor cria v3 com data atualizada.
    user['value'] = CurrentUser(id=prof_id, role='professor')
    assert client.put(f'/api/v1/me/class-offerings/{oid}').status_code == 204
    rev_prof = client.post(
        f'/api/v1/syllabus/{pid}/versions',
        json={
            'sourceVersionId': v1_id,
            'share': True,
            'candidates': [
                {'candidateId': c1_id, 'title': 'Prova 1', 'type': 'prova', 'suggestedDate': '2026-11-20', 'suggestedTime': '14:00:00'},
            ],
        },
    )
    assert rev_prof.status_code == 201, rev_prof.text
    v2_id = rev_prof.json()['id']

    user['value'] = CurrentUser(id=follower_id, role='student')
    rev_student = client.post(
        f'/api/v1/syllabus/{pid}/versions',
        json={
            'sourceVersionId': v1_id,
            'share': True,
            'candidates': [
                {'candidateId': c1_id, 'title': 'Prova 1 Adiada', 'type': 'prova', 'suggestedDate': '2026-11-27', 'suggestedTime': '16:00:00'},
            ],
        },
    )
    assert rev_student.status_code == 201, rev_student.text
    v3_id = rev_student.json()['id']

    # Evento pessoal já importado por João continua preservado e com data original!
    user['value'] = CurrentUser(id=follower_id, role='student')
    agenda = client.get('/api/v1/me/events').json()
    assert len(agenda) == 1
    assert agenda[0]['id'] == original_event_id
    assert agenda[0]['title'] == 'Prova 1'

    # Em empate de 0 votos, a versão mais recente (v3) aparece prioritariamente e sinaliza alteração.
    listed = client.get(f'/api/v1/class-offerings/{oid}/shared-plans').json()['items']
    assert [v['id'] for v in listed] == [v3_id, v2_id, v1_id]
    assert listed[0]['is_default'] is True
    assert listed[0]['has_imported_update'] is True
    assert listed[0]['imported_from_version_number'] == 1
    assert listed[0]['candidates'][0]['modified_since_import'] is True
    assert listed[1]['author_role'] == 'professor'

    # Votar na v2 coloca v2 no topo (mais votos positivos); votar repetido não multiplica.
    user['value'] = CurrentUser(id=prof_id, role='professor')
    v_prof = client.put(f'/api/v1/syllabus/{pid}/versions/{v2_id}/vote', json={'value': 'confirm'}).json()
    assert v_prof['confirmCount'] == 1
    v_prof_repeat = client.put(f'/api/v1/syllabus/{pid}/versions/{v2_id}/vote', json={'value': 'confirm'}).json()
    assert v_prof_repeat['confirmCount'] == 1

    user['value'] = CurrentUser(id=follower_id, role='student')
    listed_after_vote = client.get(f'/api/v1/class-offerings/{oid}/shared-plans').json()['items']
    assert listed_after_vote[0]['id'] == v2_id
    assert listed_after_vote[0]['is_default'] is True

    # Importar atualização da v3 atualiza o evento existente sem duplicar!
    c1_v3_id = listed[0]['candidates'][0]['id']
    reimported = client.post(
        f'/api/v1/syllabus/{pid}/confirm',
        headers={'Idempotency-Key': 'import-shared-002'},
        json={
            'versionId': v3_id,
            'candidates': [{'candidateId': c1_v3_id, 'title': 'Prova 1 Adiada', 'startsAt': '2026-11-27T16:00:00-03:00', 'type': 'prova'}],
        },
    )
    assert reimported.status_code == 200
    assert reimported.json()['events'][0]['id'] == original_event_id
    assert len(client.get('/api/v1/me/events').json()) == 1

    # Retirar candidato e retirar versão: apenas autor da versão ou admin podem.
    user['value'] = CurrentUser(id=prof_id, role='professor')
    assert client.delete(f'/api/v1/syllabus/{pid}/versions/{v3_id}/sharing').status_code == 403
    assert client.delete(f'/api/v1/syllabus/{pid}/versions/{v3_id}/candidates/{c1_v3_id}').status_code == 403

    user['value'] = CurrentUser(id=follower_id, role='student')
    assert client.delete(f'/api/v1/syllabus/{pid}/versions/{v3_id}/candidates/{c1_v3_id}').status_code == 204
    withdrawn = client.delete(f'/api/v1/syllabus/{pid}/versions/{v3_id}/sharing')
    assert withdrawn.status_code == 200
    assert withdrawn.json()['visibility'] == 'privada'
    assert withdrawn.json()['withdrawnAt'] is not None
    # Evento pessoal já importado continua preservado mesmo após retirada da versão.
    assert len(client.get('/api/v1/me/events').json()) == 1
    with sessions() as db:
        assert db.scalar(select(PersonalEvent).where(PersonalEvent.user_id == follower_id)) is not None

    # Admin também pode retirar a versão de outro autor; após retirada, v1 não é recompartilhada automaticamente ao consultar o plano.
    admin_id = uuid4()
    user['value'] = CurrentUser(id=admin_id, role='admin')
    assert client.delete(f'/api/v1/syllabus/{pid}/versions/{v2_id}/sharing').status_code == 200
    assert client.delete(f'/api/v1/syllabus/{pid}/versions/{v1_id}/sharing').status_code == 200

    user['value'] = CurrentUser(id=author_id, role='student')
    assert client.get(f'/api/v1/syllabus/{pid}').status_code == 200
    user['value'] = CurrentUser(id=follower_id, role='student')
    assert client.get(f'/api/v1/class-offerings/{oid}/shared-plans').json()['items'] == []
