"""S8-B02 (#79): redirecionamento de Conferir evento contado uma vez por clique.

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
        for role in ('ana', 'bruno', 'professor', 'admin'):
            uid = str(uuid4())
            conn.execute(text("insert into auth.users(id,email,raw_user_meta_data) values (:id,:email,:meta)"),
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


def as_backend(conn):
    conn.execute(text('reset role'))


def denied(conn, sql, params=None):
    with conn.begin_nested():
        with pytest.raises(DBAPIError):
            with conn.begin_nested():
                conn.execute(text(sql), params or {})


def blocked(conn, sql, params=None):
    """Escrita sem efeito: recusada pelo banco ou sem nenhuma linha afetada."""
    try:
        with conn.begin_nested():
            assert conn.execute(text(sql), params or {}).rowcount == 0
    except DBAPIError:
        pass


def scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar()


def manual_event(conn, author, status='aprovado', **extra):
    columns = {'autor_id': author, 'titulo': 'Evento de teste', 'descricao': 'Descrição',
               'status': status, **extra}
    names = ', '.join(columns)
    values = ', '.join(f':{name}' for name in columns)
    date = '' if 'data_evento' in columns or 'dia_inteiro' in columns else ", data_evento"
    date_value = '' if not date else ", now() + interval '10 days'"
    return str(conn.execute(text(f'insert into public.eventos({names}{date}) values ({values}{date_value}) returning id'),
                            columns).scalar_one())


def test_redirect_is_counted_once_per_click(database):
    conn, users = database
    event_id = manual_event(conn, users['professor'], link_externo='https://exemplo.unb.br/inscricao')
    click = str(uuid4())
    call = 'select public.registrar_clique_evento(:e, :c)'

    assert scalar(conn, call, {'e': event_id, 'c': click}) == 'https://exemplo.unb.br/inscricao'
    scalar(conn, call, {'e': event_id, 'c': click})   # retry ou duplo clique
    assert scalar(conn, 'select interessados_count from public.eventos where id=:id', {'id': event_id}) == 1

    scalar(conn, call, {'e': event_id, 'c': str(uuid4())})   # outro acionamento
    assert scalar(conn, 'select interessados_count from public.eventos where id=:id', {'id': event_id}) == 2

    pending = manual_event(conn, users['professor'], status='pendente', link_externo='https://exemplo.unb.br/x')
    no_link = manual_event(conn, users['professor'])
    for unavailable in (pending, no_link, str(uuid4())):
        denied(conn, call, {'e': unavailable, 'c': str(uuid4())})
    denied(conn, call, {'e': event_id, 'c': None})
    assert scalar(conn, 'select interessados_count from public.eventos where id=:id', {'id': pending}) == 0


def test_click_log_holds_no_person_and_is_closed_to_the_browser(database):
    conn, users = database
    event_id = manual_event(conn, users['professor'], link_externo='https://exemplo.unb.br/inscricao')
    scalar(conn, 'select public.registrar_clique_evento(:e, :c)', {'e': event_id, 'c': str(uuid4())})
    columns = conn.execute(text("""select column_name from information_schema.columns
        where table_schema='public' and table_name='cliques_evento' order by 1""")).scalars().all()
    assert columns == ['click_id', 'criado_em', 'evento_id']

    for uid in (None, users['ana']):
        assume(conn, uid)
        denied(conn, 'select public.registrar_clique_evento(:e, :c)', {'e': event_id, 'c': str(uuid4())})
        denied(conn, 'select count(*) from public.cliques_evento')
        blocked(conn, 'update public.eventos set interessados_count = 999 where id=:id', {'id': event_id})
    as_backend(conn)
    assert scalar(conn, 'select interessados_count from public.eventos where id=:id', {'id': event_id}) == 1
    assert scalar(conn, "select to_regprocedure('public.registrar_interesse(uuid)')") is None
