"""S8-D02 (#84): matriz cross-user e travas de segurança do banco exposto.

Testes preventivos (Sprint 07) contra o Supabase LOCAL migrado; cada teste
desfaz suas alterações. Rode com TEST_SUPABASE_DB_URL (nunca produção).

Cobre o que o navegador consegue fazer direto pelo banco (supabase-js), sem
passar pela API: leitura, escrita e chamadas de função de um usuário sobre
os dados de outro, e de visitantes sobre dados privados.
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


def scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar()


def personal_event(conn, owner, **extra):
    columns = {'user_id': owner, 'titulo': 'Compromisso privado', **extra}
    names = ', '.join(columns)
    values = ', '.join(f':{name}' for name in columns)
    return str(conn.execute(text(f'insert into public.eventos_pessoais({names}, data_hora) values ({values}, now()) returning id'),
                            columns).scalar_one())


def public_event(conn, author, status):
    return str(conn.execute(text("""insert into public.eventos(autor_id, titulo, descricao, data_evento, status)
        values (:a, 'Evento de teste', 'Descrição', now() + interval '1 day', :s) returning id"""),
        {'a': author, 's': status}).scalar_one())


# ---------------------------------------------------------------------------
# Travas estruturais: valem para qualquer migration futura
# ---------------------------------------------------------------------------

def test_every_public_table_has_rls_enabled(database):
    conn, _ = database
    without_rls = conn.execute(text("""select c.relname from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity
        order by 1""")).scalars().all()
    assert without_rls == [], f'Tabelas expostas sem RLS: {without_rls}'


def test_security_definer_functions_pin_search_path(database):
    conn, _ = database
    unpinned = conn.execute(text("""select p.proname from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public' and p.prosecdef
          and not exists (select 1 from unnest(coalesce(p.proconfig, '{}')) c where c like 'search_path=%')
        order by 1""")).scalars().all()
    assert unpinned == [], f'Funções SECURITY DEFINER sem search_path fixo: {unpinned}'


# ---------------------------------------------------------------------------
# Matriz cross-user
# ---------------------------------------------------------------------------

def test_personal_agenda_is_private(database):
    conn, users = database
    event_id = personal_event(conn, users['ana'])

    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.eventos_pessoais where id=:id', {'id': event_id}) == 0
    assert conn.execute(text("update public.eventos_pessoais set titulo='Alterado por outro' where id=:id"),
                        {'id': event_id}).rowcount == 0
    assert conn.execute(text('delete from public.eventos_pessoais where id=:id'), {'id': event_id}).rowcount == 0
    denied(conn, "insert into public.eventos_pessoais(user_id, titulo, data_hora) values (:u, 'Plantado na agenda alheia', now())",
           {'u': users['ana']})

    assume(conn)
    assert scalar(conn, 'select count(*) from public.eventos_pessoais') == 0
    denied(conn, "insert into public.eventos_pessoais(user_id, titulo, data_hora) values (:u, 'Visitante', now())",
           {'u': users['ana']})

    assume(conn, users['ana'])
    assert scalar(conn, 'select titulo from public.eventos_pessoais where id=:id', {'id': event_id}) == 'Compromisso privado'


def test_user_cannot_block_another_users_import(database):
    """Um usuário não pode ocupar, pela própria agenda, o candidato de outra pessoa.

    Com unicidade global de origem_avaliacao_id, Bruno inseriria um evento
    apontando para o candidato da Ana e a confirmação dela passaria a falhar.
    """
    conn, users = database
    plan_id = scalar(conn, """insert into public.planos_ensino(user_id, caminho_arquivo, status, processado_em)
        values (:u, :p, 'concluido', now()) returning id""",
        {'u': users['ana'], 'p': f"syllabus_files/{users['ana']}/{uuid4()}.pdf"})
    candidate_id = scalar(conn, "insert into public.avaliacoes(plano_id, titulo) values (:p, 'Prova 1') returning id", {'p': plan_id})

    assume(conn, users['bruno'])
    try:
        with conn.begin_nested():
            personal_event(conn, users['bruno'], origem_avaliacao_id=candidate_id)
    except DBAPIError:
        pass  # recusar a inserção também é um resultado seguro

    as_backend(conn)
    personal_event(conn, users['ana'], origem_avaliacao_id=candidate_id, origem_plano_id=plan_id)
    assert scalar(conn, 'select count(*) from public.eventos_pessoais where user_id=:u and origem_avaliacao_id=:c',
                  {'u': users['ana'], 'c': candidate_id}) == 1


def test_saved_events_are_private_and_only_for_approved_events(database):
    conn, users = database
    approved = public_event(conn, users['professor'], 'aprovado')
    pending = public_event(conn, users['professor'], 'pendente')

    assume(conn, users['ana'])
    conn.execute(text('insert into public.eventos_salvos(user_id, event_id) values (:u, :e)'), {'u': users['ana'], 'e': approved})
    denied(conn, 'insert into public.eventos_salvos(user_id, event_id) values (:u, :e)', {'u': users['ana'], 'e': pending})
    denied(conn, 'insert into public.eventos_salvos(user_id, event_id) values (:u, :e)', {'u': users['bruno'], 'e': approved})

    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.eventos_salvos') == 0
    assert conn.execute(text('delete from public.eventos_salvos where user_id=:u'), {'u': users['ana']}).rowcount == 0

    assume(conn)
    assert scalar(conn, 'select count(*) from public.eventos_salvos') == 0


def test_public_events_hide_pending_and_block_impersonation(database):
    conn, users = database
    pending = public_event(conn, users['professor'], 'pendente')
    approved = public_event(conn, users['professor'], 'aprovado')

    assume(conn)
    assert scalar(conn, 'select count(*) from public.eventos where id=:id', {'id': approved}) == 1
    assert scalar(conn, 'select count(*) from public.eventos where id=:id', {'id': pending}) == 0

    assume(conn, users['ana'])
    assert scalar(conn, 'select count(*) from public.eventos where id=:id', {'id': pending}) == 0
    # Estudante não pode publicar em nome de professor para escapar da moderação.
    denied(conn, """insert into public.eventos(autor_id, titulo, descricao, data_evento, status)
        values (:a, 'Forjado', 'x', now() + interval '1 day', 'aprovado')""", {'a': users['professor']})
    assert conn.execute(text("update public.eventos set titulo='Alterado' where id=:id"), {'id': approved}).rowcount == 0
    assert conn.execute(text('delete from public.eventos where id=:id'), {'id': approved}).rowcount == 0


def test_notifications_cannot_be_read_or_marked_by_others(database):
    conn, users = database
    assume(conn, users['ana'])
    event_id = public_event(conn, users['ana'], 'pendente')
    as_backend(conn)
    notification = scalar(conn, 'select id from public.notificacoes where evento_id=:e limit 1', {'e': event_id})
    assert notification is not None

    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.notificacoes where id=:n', {'n': notification}) == 0
    assert conn.execute(text('update public.notificacoes set lida_em=now() where id=:n'), {'n': notification}).rowcount == 0

    assume(conn)
    # O visitante não tem sequer permissão na tabela: recusa total também é seguro.
    try:
        with conn.begin_nested():
            assert scalar(conn, 'select count(*) from public.notificacoes') == 0
    except DBAPIError:
        pass


def test_profiles_cannot_be_read_or_changed_by_others(database):
    conn, users = database
    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.profiles where id=:id', {'id': users['ana']}) == 0
    assert conn.execute(text("update public.profiles set nome_completo='Hackeado' where id=:id"),
                        {'id': users['ana']}).rowcount == 0
    # O próprio e-mail é imutável e o papel não sobe pelo navegador.
    denied(conn, "update public.profiles set email='outro@unb.br' where id=:id", {'id': users['bruno']})
    denied(conn, "update public.profiles set papel='admin' where id=:id", {'id': users['bruno']})

    assume(conn)
    assert scalar(conn, 'select count(*) from public.profiles') == 0


def test_admin_functions_refuse_students_and_visitors(database):
    conn, users = database
    calls = [
        'select * from public.admin_listar_usuarios()',
        "select public.admin_alterar_papel(:u, 'admin')",
        "select public.admin_definir_papel(:u, 'admin', 'student')",
        'select public.admin_buscar_usuarios()',
        'select public.listar_sugestoes()',
    ]
    for uid in (users['ana'], None):
        assume(conn, uid)
        for call in calls:
            denied(conn, call, {'u': users['ana']})
    as_backend(conn)
    assert scalar(conn, 'select papel from public.profiles where id=:u', {'u': users['ana']}) == 'student'


def test_plan_candidates_are_private_and_read_only(database):
    conn, users = database
    plan_id = scalar(conn, """insert into public.planos_ensino(user_id, caminho_arquivo, status, processado_em)
        values (:u, :p, 'concluido', now()) returning id""",
        {'u': users['ana'], 'p': f"syllabus_files/{users['ana']}/{uuid4()}.pdf"})
    candidate_id = scalar(conn, "insert into public.avaliacoes(plano_id, titulo) values (:p, 'Prova 1') returning id", {'p': plan_id})

    assume(conn, users['ana'])
    assert scalar(conn, 'select count(*) from public.avaliacoes where id=:c', {'c': candidate_id}) == 1
    # Nem o dono altera candidatos direto: revisão e confirmação passam pela API.
    assert conn.execute(text("update public.avaliacoes set status='confirmado' where id=:c"), {'c': candidate_id}).rowcount == 0
    denied(conn, "insert into public.avaliacoes(plano_id, titulo) values (:p, 'Plantada')", {'p': plan_id})

    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.avaliacoes where id=:c', {'c': candidate_id}) == 0
    assert scalar(conn, 'select count(*) from public.planos_ensino where id=:p', {'p': plan_id}) == 0

    assume(conn)
    assert scalar(conn, 'select count(*) from public.avaliacoes') == 0
