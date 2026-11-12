"""S8-D01 (#83): endpoints de direitos do titular. Sem rede e sem Supabase."""
import logging
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.exc import DBAPIError

from src.modules.account import repository, router as account_router
from src.modules.account.services import SupabaseAccountAdmin, get_account_admin
from src.main import app


class FakeDbError(Exception):
    def __init__(self, sqlstate, message):
        super().__init__(message)
        self.sqlstate = sqlstate


def db_error(sqlstate, message):
    return DBAPIError('select 1', {}, FakeDbError(sqlstate, message))


class FakeAdmin:
    def __init__(self):
        self.calls = []

    def delete_files(self, paths):
        self.calls.append(('files', list(paths)))

    def delete_user(self, user_id):
        self.calls.append(('user', user_id))


@pytest.fixture
def account(api, monkeypatch):
    client, _, authenticated_user, _ = api
    admin = FakeAdmin()
    app.dependency_overrides[get_account_admin] = lambda: admin
    state = {'accepted': {}, 'finished': []}
    monkeypatch.setattr(repository, 'list_acceptances', lambda db, uid: dict(state['accepted']))
    monkeypatch.setattr(repository, 'accept_document',
                        lambda db, uid, document, version: state['accepted'].__setitem__(document, version))
    monkeypatch.setattr(repository, 'finish_deletion', lambda db, record: state['finished'].append(record))
    yield client, authenticated_user['value'], admin, state, monkeypatch
    app.dependency_overrides.pop(get_account_admin, None)


def test_legal_documents_show_what_is_pending(account):
    client, _, _, _, _ = account
    current = repository.CURRENT_LEGAL_VERSIONS['termos_de_uso']
    before = client.get('/api/v1/me/legal-documents').json()
    assert before[0] == {'document': 'terms', 'currentVersion': current, 'acceptedVersion': None, 'pending': True}

    # só a versão vigente pode ser aceita
    assert client.put('/api/v1/me/legal-acceptances/terms', json={'version': '2020-01-01'}).status_code == 409
    assert client.put('/api/v1/me/legal-acceptances/terms', json={'version': 'ultima'}).status_code == 422
    assert client.put('/api/v1/me/legal-acceptances/cookies', json={'version': current}).status_code == 422
    assert client.put('/api/v1/me/legal-acceptances/terms', json={'version': current}).status_code == 204

    after = {item['document']: item['pending'] for item in client.get('/api/v1/me/legal-documents').json()}
    assert after == {'terms': False, 'privacy': True}


def test_export_is_a_private_download(account):
    client, user, _, _, monkeypatch = account
    monkeypatch.setattr(repository, 'export_account', lambda db, uid: {'conta': {'id': str(uid)}})
    response = client.get('/api/v1/me/data-export')
    assert response.status_code == 200 and response.json() == {'conta': {'id': str(user.id)}}
    assert response.headers['cache-control'] == 'no-store'
    assert 'attachment; filename="agenda-unb-meus-dados-' in response.headers['content-disposition']

    def missing(db, uid):
        raise db_error('P0002', 'Conta não encontrada')
    monkeypatch.setattr(repository, 'export_account', missing)
    assert client.get('/api/v1/me/data-export').status_code == 404


def test_delete_requires_explicit_confirmation_and_removes_files_first(account):
    client, user, admin, state, monkeypatch = account
    monkeypatch.setattr(repository, 'prepare_deletion', lambda db, uid: {
        'registro_id': 'registro-1', 'arquivos': [f'syllabus_files/{uid}/plano.pdf'], 'contagens': {}})

    assert client.request('DELETE', '/api/v1/me', json={'confirmation': 'sim'}).status_code == 422
    assert client.request('DELETE', '/api/v1/me').status_code == 422
    assert admin.calls == []

    response = client.request('DELETE', '/api/v1/me', json={'confirmation': 'EXCLUIR MINHA CONTA'})
    assert response.status_code == 204
    assert admin.calls == [('files', [f'syllabus_files/{user.id}/plano.pdf']), ('user', user.id)]
    assert state['finished'] == ['registro-1']


def test_delete_stops_before_the_account_when_files_cannot_be_removed(account):
    client, _, admin, state, monkeypatch = account
    monkeypatch.setattr(repository, 'prepare_deletion', lambda db, uid: {
        'registro_id': 'registro-1', 'arquivos': ['syllabus_files/x/plano.pdf'], 'contagens': {}})

    def failing(paths):
        from fastapi import HTTPException
        raise HTTPException(status_code=502, detail='Não foi possível remover seus arquivos. Tente novamente.')
    monkeypatch.setattr(admin, 'delete_files', failing)

    assert client.request('DELETE', '/api/v1/me', json={'confirmation': 'EXCLUIR MINHA CONTA'}).status_code == 502
    assert admin.calls == [] and state['finished'] == []     # a conta continua existindo; o pedido pode ser repetido


def test_last_admin_gets_a_conflict(account):
    client, _, admin, _, monkeypatch = account

    def last_admin(db, uid):
        raise db_error('55000', 'Transfira a administração para outra conta antes de excluir esta')
    monkeypatch.setattr(repository, 'prepare_deletion', last_admin)
    response = client.request('DELETE', '/api/v1/me', json={'confirmation': 'EXCLUIR MINHA CONTA'})
    assert response.status_code == 409 and 'Transfira a administração' in response.json()['detail']
    assert admin.calls == []


def test_supabase_admin_calls_never_log_identifiers(monkeypatch, caplog):
    user_id = uuid4()
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs.get('json')))
        return httpx.Response(200, json=[])
    monkeypatch.setattr(httpx, 'request', fake_request)
    monkeypatch.setattr(httpx, 'delete', lambda url, **kwargs: calls.append(('DELETE', url, None)) or httpx.Response(404))

    admin = SupabaseAccountAdmin('https://projeto.supabase.co', 'chave-de-servico')
    admin.delete_files([f'syllabus_files/{user_id}/plano.pdf'])
    admin.delete_files([])                         # nada a remover: sem chamada
    admin.delete_user(user_id)                     # 404 = já removida em tentativa anterior
    assert calls == [
        ('DELETE', 'https://projeto.supabase.co/storage/v1/object/syllabus_files', {'prefixes': [f'{user_id}/plano.pdf']}),
        ('DELETE', f'https://projeto.supabase.co/auth/v1/admin/users/{user_id}', None),
    ]

    from fastapi import HTTPException
    monkeypatch.setattr(httpx, 'request', lambda *a, **k: httpx.Response(500, text=f'segredo {user_id}'))
    monkeypatch.setattr(httpx, 'delete', lambda *a, **k: httpx.Response(500, text=f'segredo {user_id}'))
    with caplog.at_level(logging.WARNING):
        for call in (lambda: admin.delete_files(['syllabus_files/a/b.pdf']), lambda: admin.delete_user(user_id)):
            with pytest.raises(HTTPException) as error:
                call()
            assert error.value.status_code == 502
    assert str(user_id) not in caplog.text and 'segredo' not in caplog.text and 'chave-de-servico' not in caplog.text

    with pytest.raises(HTTPException) as error:
        SupabaseAccountAdmin('', '').delete_user(user_id)
    assert error.value.status_code == 503


def test_database_errors_are_logged_without_row_content(api, caplog):
    """A mensagem do PostgreSQL pode trazer a linha recusada; ela não vai para o log."""
    client, _, _, _ = api
    secret = 'conteúdo acadêmico confidencial'

    @app.get('/api/v1/_teste-erro-banco')
    def boom():
        raise DBAPIError('insert into planos', {'texto': secret}, FakeDbError('23514', f'Failing row contains ({secret})'))

    try:
        with caplog.at_level(logging.INFO):
            response = client.get('/api/v1/_teste-erro-banco')
        assert response.status_code == 503 and secret not in response.text
        assert secret not in caplog.text and 'sqlstate=23514' in caplog.text
    finally:
        app.router.routes[:] = [route for route in app.router.routes if getattr(route, 'path', '') != '/api/v1/_teste-erro-banco']
