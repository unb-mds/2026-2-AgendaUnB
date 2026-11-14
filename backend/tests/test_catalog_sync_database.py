"""S7-B03 (#70) e ADR-009: sincronização do catálogo público de turmas.

Testes contra o Supabase LOCAL migrado; cada teste desfaz suas alterações.
Rode com TEST_SUPABASE_DB_URL (nunca produção).
"""
import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


@pytest.fixture
def database():
    url = os.getenv('TEST_SUPABASE_DB_URL')
    if not url:
        pytest.skip('TEST_SUPABASE_DB_URL not configured')
    assert make_url(url).host in ('localhost', '127.0.0.1'), 'Local database only'
    engine = create_engine(url)
    with engine.connect() as conn:
        transaction = conn.begin()
        users = {}
        for role in ('ana', 'bruno', 'carla', 'professor', 'admin'):
            uid = str(uuid4())
            conn.execute(text("insert into auth.users(id,email,email_confirmed_at,raw_user_meta_data) values (:id,:email,now(),:meta)"),
                         {'id': uid, 'email': f'test-{uid}@unb.br', 'meta': json.dumps({'nome_completo': 'Teste ' + role})})
            if role in ('professor', 'admin'):
                conn.execute(text('update public.profiles set papel=:role where id=:id'), {'role': role, 'id': uid})
            users[role] = uid
        yield conn, users
        transaction.rollback()
    engine.dispose()


def assume(conn, uid=None):
    conn.execute(text('reset role'))
    if uid is None:
        conn.execute(text("select set_config('request.jwt.claim.sub', '', true)"))
        conn.execute(text('set local role anon'))
        return
    conn.execute(text("select set_config('request.jwt.claim.sub', :uid, true)"), {'uid': uid})
    conn.execute(text('set local role authenticated'))


def denied(conn, sql, params=None):
    with conn.begin_nested():
        with pytest.raises(DBAPIError):
            with conn.begin_nested():
                conn.execute(text(sql), params or {})


def scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar()


def follow(conn, user_id, offering_id):
    conn.execute(text('insert into public.vinculos_turma(user_id, oferta_id) values (:u, :o)'),
                 {'u': user_id, 'o': offering_id})


def sync(conn, **item):
    payload = {'origem': 'followw', 'codigo': 'FGA0138', 'nome': 'Métodos de Desenvolvimento de Software',
               'unidade': 'FGA', 'nivel': 'graduacao', 'turma': '01', 'ano': 2026, 'semestre': 2, **item}
    payload = {key: value for key, value in payload.items() if value is not None}
    return conn.execute(text('select public.registrar_oferta_catalogo(cast(:p as jsonb))'),
                        {'p': json.dumps(payload)}).scalar_one()


def test_catalog_identity_is_stable_across_syncs(database):
    conn, users = database
    created = sync(conn, professor='Profa. Carla', horarios='24T23')
    assert created['acao'] == 'criada'
    follow(conn, users['ana'], created['id'])

    assert sync(conn, professor='Profa. Carla', horarios='24T23') == {'id': created['id'], 'acao': 'inalterada'}
    # professor e horário mudam sem trocar a identidade nem o vínculo
    updated = sync(conn, professor='Prof. Substituto', horarios='35T45')
    assert updated == {'id': created['id'], 'acao': 'atualizada'}
    assert scalar(conn, 'select professor from public.ofertas_turma where id=:id', {'id': created['id']}) == 'Prof. Substituto'
    assert scalar(conn, 'select count(*) from public.vinculos_turma where oferta_id=:id', {'id': created['id']}) == 1

    # código normalizado; zeros à esquerda da turma preservados; semestres distintos
    assert sync(conn, codigo=' fga0138 ', professor='Prof. Substituto', horarios='35T45')['id'] == created['id']
    assert sync(conn, turma='1')['id'] != created['id']
    assert sync(conn, semestre=1)['id'] != created['id']
    assert scalar(conn, "select count(*) from public.disciplinas where codigo='FGA0138'") == 1

    # a origem passa a informar o ID da oferta: o mesmo registro o adota
    adopted = sync(conn, oferta_origem_id='cls-991', professor='Prof. Substituto', horarios='35T45')
    assert adopted['id'] == created['id']
    assert sync(conn, oferta_origem_id='cls-991', professor='Prof. Substituto', horarios='35T45')['acao'] == 'inalterada'
    # colisão entre o ID da origem e a chave natural exige revisão
    with pytest.raises(DBAPIError):
        with conn.begin_nested():
            sync(conn, oferta_origem_id='cls-991', turma='02')
    with pytest.raises(DBAPIError):
        with conn.begin_nested():
            sync(conn, turma=None)


def test_catalog_state_reports_stale_cache(database):
    conn, users = database
    state = 'select public.estado_catalogo()'
    assert scalar(conn, state) == {'atualizado_em': None, 'desatualizado': True, 'tem_cache': False}

    sync(conn)
    conn.execute(text("""insert into public.sincronizacoes_catalogo(status, iniciada_em, concluida_em, ofertas_lidas, criadas)
        values ('concluida', now() - interval '2 hours', now() - interval '2 hours', 1, 1)"""))
    fresh = scalar(conn, state)
    assert fresh['desatualizado'] is False and fresh['tem_cache'] is True and fresh['atualizado_em']

    # a origem caiu: o cache e a data da última sincronização válida permanecem
    conn.execute(text("""insert into public.sincronizacoes_catalogo(status, iniciada_em, concluida_em, erro_codigo)
        values ('falha', now() - interval '1 hour', now() - interval '1 hour', 'http_503')"""))
    stale = scalar(conn, state)
    assert stale['desatualizado'] is True and stale['atualizado_em'] == fresh['atualizado_em']
    assert scalar(conn, 'select count(*) from public.ofertas_turma') >= 1

    for uid in (None, users['ana']):
        assume(conn, uid)
        denied(conn, 'select public.registrar_oferta_catalogo(cast(:p as jsonb))', {'p': '{}'})
        denied(conn, 'select count(*) from public.sincronizacoes_catalogo')
        denied(conn, state)
