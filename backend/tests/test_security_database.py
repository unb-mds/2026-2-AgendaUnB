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


def blocked(conn, sql, params=None):
    """Escrita sem efeito: recusada pelo banco ou sem nenhuma linha afetada."""
    try:
        with conn.begin_nested():
            assert conn.execute(text(sql), params or {}).rowcount == 0
    except DBAPIError:
        pass


def hidden(conn, sql, params=None):
    """Leitura sem resultado: recusada pelo banco ou sem nenhuma linha."""
    try:
        with conn.begin_nested():
            assert conn.execute(text(sql), params or {}).scalar() in (0, None)
    except DBAPIError:
        pass


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
    blocked(conn, "update public.eventos_pessoais set titulo='Alterado por outro' where id=:id", {'id': event_id})
    blocked(conn, 'delete from public.eventos_pessoais where id=:id', {'id': event_id})
    denied(conn, "insert into public.eventos_pessoais(user_id, titulo, data_hora) values (:u, 'Plantado na agenda alheia', now())",
           {'u': users['ana']})

    assume(conn)
    hidden(conn, 'select count(*) from public.eventos_pessoais')
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
    blocked(conn, 'delete from public.eventos_salvos where user_id=:u', {'u': users['ana']})

    assume(conn)
    hidden(conn, 'select count(*) from public.eventos_salvos')


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
    blocked(conn, "update public.eventos set titulo='Alterado' where id=:id", {'id': approved})
    blocked(conn, 'delete from public.eventos where id=:id', {'id': approved})


def test_notifications_cannot_be_read_or_marked_by_others(database):
    conn, users = database
    event_id = public_event(conn, users['ana'], 'pendente')
    notification = scalar(conn, 'select id from public.notificacoes where evento_id=:e limit 1', {'e': event_id})
    assert notification is not None

    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.notificacoes where id=:n', {'n': notification}) == 0
    blocked(conn, 'update public.notificacoes set lida_em=now() where id=:n', {'n': notification})

    assume(conn)
    hidden(conn, 'select count(*) from public.notificacoes')


def test_profiles_cannot_be_read_or_changed_by_others(database):
    conn, users = database
    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.profiles where id=:id', {'id': users['ana']}) == 0
    blocked(conn, "update public.profiles set nome_completo='Hackeado' where id=:id", {'id': users['ana']})
    # O próprio e-mail é imutável e o papel não sobe pelo navegador.
    denied(conn, "update public.profiles set email='outro@unb.br' where id=:id", {'id': users['bruno']})
    denied(conn, "update public.profiles set papel='admin' where id=:id", {'id': users['bruno']})

    assume(conn)
    hidden(conn, 'select count(*) from public.profiles')


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
    denied(conn, "update public.avaliacoes set status='confirmado' where id=:c", {'c': candidate_id})
    denied(conn, "insert into public.avaliacoes(plano_id, titulo) values (:p, 'Plantada')", {'p': plan_id})

    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.avaliacoes where id=:c', {'c': candidate_id}) == 0
    assert scalar(conn, 'select count(*) from public.planos_ensino where id=:p', {'p': plan_id}) == 0

    assume(conn)
    denied(conn, 'select count(*) from public.avaliacoes')


# ---------------------------------------------------------------------------
# Endurecimento (20261110090000): menor privilégio e validação no banco
# ---------------------------------------------------------------------------

def signup(conn, email, role=None, confirmed=False):
    uid = str(uuid4())
    meta = {'nome_completo': 'Cadastro de teste', **({'papel': role} if role else {})}
    conn.execute(text("""insert into auth.users(id, email, raw_user_meta_data, email_confirmed_at)
        values (:id, :email, :meta, case when :confirmed then now() end)"""),
        {'id': uid, 'email': email, 'meta': json.dumps(meta), 'confirmed': confirmed})
    return uid


def role_of(conn, uid):
    return scalar(conn, 'select papel from public.profiles where id=:id', {'id': uid})


def test_visitors_have_no_write_privilege_and_nobody_can_truncate(database):
    conn, _ = database
    rows = conn.execute(text("""select grantee, table_name, privilege_type
        from information_schema.role_table_grants
        where table_schema = 'public'
          and ((grantee = 'anon' and privilege_type <> 'SELECT')
            or (grantee in ('anon', 'authenticated') and privilege_type in ('TRUNCATE', 'TRIGGER', 'REFERENCES')))
        order by 1, 2, 3""")).all()
    assert rows == [], f'Privilégios excessivos: {rows}'


def test_every_write_grant_of_logged_users_is_backed_by_a_policy(database):
    """GRANT de escrita sem política é um descuido esperando uma política permissiva."""
    conn, _ = database
    rows = conn.execute(text("""select g.table_name, g.privilege_type
        from information_schema.role_table_grants g
        where g.table_schema = 'public' and g.grantee = 'authenticated'
          and g.privilege_type in ('INSERT', 'UPDATE', 'DELETE')
          and not exists (select 1 from pg_policies p
            where p.schemaname = 'public' and p.tablename = g.table_name
              and p.cmd in (g.privilege_type, 'ALL'))
        order by 1, 2""")).all()
    assert rows == [], f'Escrita concedida sem política: {rows}'


def test_no_function_is_callable_by_visitors_and_rpcs_are_hardened(database):
    conn, _ = database
    for_visitors = conn.execute(text("""select p.oid::regprocedure::text from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public' and has_function_privilege('anon', p.oid, 'execute')
        order by 1""")).scalars().all()
    assert for_visitors == [], f'Funções chamáveis sem login: {for_visitors}'

    # O que a conta logada chama via /rpc precisa de search_path fixo.
    loose = conn.execute(text("""select p.oid::regprocedure::text from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname = 'public' and has_function_privilege('authenticated', p.oid, 'execute')
          and not exists (select 1 from unnest(coalesce(p.proconfig, '{}')) c where c like 'search_path=%')
        order by 1""")).scalars().all()
    assert loose == [], f'RPCs sem search_path fixo: {loose}'


def test_queue_status_is_visible_to_the_plan_owner_only(database):
    conn, users = database
    plan_id = str(uuid4())
    conn.execute(text("""insert into public.planos_ensino(id, user_id, nome_arquivo, caminho_arquivo, tipo_arquivo, status)
        values (:id, :u, 'plano.pdf', :path, 'pdf', 'pendente')"""),
        {'id': plan_id, 'u': users['ana'], 'path': f"syllabus_files/{users['ana']}/{plan_id}_plano.pdf"})
    conn.execute(text('insert into public.fila_processamento_ia(plano_id) values (:p)'), {'p': plan_id})
    denied(conn, "update public.fila_processamento_ia set erro_tecnico=repeat('x', 61) where plano_id=:p", {'p': plan_id})

    assume(conn, users['ana'])
    assert scalar(conn, 'select count(*) from public.fila_processamento_ia where plano_id=:p', {'p': plan_id}) == 1
    denied(conn, "update public.fila_processamento_ia set status='concluido' where plano_id=:p", {'p': plan_id})
    denied(conn, 'insert into public.fila_processamento_ia(plano_id) values (:p)', {'p': plan_id})
    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.fila_processamento_ia') == 0
    assume(conn)
    hidden(conn, 'select count(*) from public.fila_processamento_ia')


def test_legacy_interest_counter_is_closed_to_the_browser(database):
    conn, users = database
    event_id = public_event(conn, users['professor'], 'aprovado')
    for uid in (None, users['ana']):
        assume(conn, uid)
        denied(conn, 'select public.registrar_interesse(:e)', {'e': event_id})
    as_backend(conn)
    assert scalar(conn, 'select interessados_count from public.eventos where id=:e', {'e': event_id}) == 0


@pytest.mark.parametrize('link', ['javascript:alert(document.cookie)', 'data:text/html,<script>1</script>',
                                  'JaVaScRiPt:alert(1)', 'ftp://example.org/a', 'https://example.org/a b',
                                  'https://example.org/"><script>', 'example.org'])
def test_event_link_must_be_http_on_every_write_path(database, link):
    """O link é aberto pela tela do evento; javascript: executaria código na sessão de quem clica."""
    conn, users = database
    insert = """insert into public.eventos(autor_id, titulo, descricao, data_evento, link_externo)
        values (:a, 'Evento com link', 'Descrição', now() + interval '1 day', :l)"""
    denied(conn, insert, {'a': users['professor'], 'l': link})  # nem o back-end grava
    event_id = public_event(conn, users['professor'], 'aprovado')
    denied(conn, 'update public.eventos set link_externo=:l where id=:e', {'l': link, 'e': event_id})


def test_event_and_profile_text_limits_hold_in_the_database(database):
    conn, users = database
    event_id = public_event(conn, users['professor'], 'aprovado')
    conn.execute(text("update public.eventos set link_externo='https://unb.br/evento?id=1&x=y' where id=:e"), {'e': event_id})
    denied(conn, "update public.eventos set titulo=repeat('a', 201) where id=:e", {'e': event_id})
    denied(conn, "update public.eventos set descricao=repeat('a', 10001) where id=:e", {'e': event_id})
    denied(conn, "update public.eventos set localizacao=repeat('a', 251) where id=:e", {'e': event_id})
    denied(conn, "insert into public.eventos_pessoais(user_id, titulo, data_hora) values (:u, repeat('a', 201), now())",
           {'u': users['ana']})

    assume(conn, users['ana'])
    conn.execute(text("update public.profiles set nome_completo='Ana Atualizada' where id=:u"), {'u': users['ana']})
    denied(conn, "update public.profiles set avatar_url='javascript:alert(1)' where id=:u", {'u': users['ana']})
    denied(conn, "update public.profiles set avatar_url='http://sem-tls.example/a.png' where id=:u", {'u': users['ana']})
    denied(conn, "update public.profiles set nome_completo=repeat('a', 201) where id=:u", {'u': users['ana']})
    # Só nome, avatar e papel são editáveis; papel segue protegido pelo trigger.
    denied(conn, "update public.profiles set criado_em=now() - interval '5 years' where id=:u", {'u': users['ana']})
    denied(conn, 'delete from public.profiles where id=:u', {'u': users['ana']})


def test_public_events_cannot_be_written_directly_even_by_professors(database):
    conn, users = database
    assume(conn, users['professor'])
    denied(conn, """insert into public.eventos(autor_id, titulo, descricao, data_evento, status)
        values (:a, 'Publicado sem API', 'Descrição', now() + interval '1 day', 'aprovado')""", {'a': users['professor']})


def test_professor_role_requires_confirmed_institutional_email(database):
    conn, _ = database
    # Cadastro pendente de confirmação: ainda não há prova de posse do endereço.
    pending = signup(conn, f'docente-{uuid4()}@unb.br', role='professor')
    assert role_of(conn, pending) == 'student'
    assume(conn, pending)
    denied(conn, "update public.profiles set papel='professor' where id=:u", {'u': pending})
    assert scalar(conn, 'select public.is_event_moderator()') is False

    # Ao confirmar, o papel pedido no cadastro é concedido automaticamente.
    as_backend(conn)
    conn.execute(text('update auth.users set email_confirmed_at=now() where id=:u'), {'u': pending})
    assert role_of(conn, pending) == 'professor'

    # Já confirmado no cadastro (Google ou ambiente sem confirmação): professor na hora.
    assert role_of(conn, signup(conn, f'docente-{uuid4()}@unb.br', role='professor', confirmed=True)) == 'professor'

    # Estudante com e-mail institucional confirmado ainda pode se promover pelo navegador.
    student = signup(conn, f'servidor-{uuid4()}@unb.br', confirmed=True)
    assume(conn, student)
    conn.execute(text("update public.profiles set papel='professor' where id=:u"), {'u': student})
    as_backend(conn)
    assert role_of(conn, student) == 'professor'

    # Confirmar o e-mail não promove quem não pediu, nem quem está fora do domínio.
    plain = signup(conn, f'aluno-{uuid4()}@unb.br')
    outsider = signup(conn, f'pessoa-{uuid4()}@example.com')
    conn.execute(text("""update auth.users set email_confirmed_at=now(),
        raw_user_meta_data = raw_user_meta_data || '{"papel":"professor"}' where id=:u"""), {'u': outsider})
    conn.execute(text('update auth.users set email_confirmed_at=now() where id=:u'), {'u': plain})
    assert (role_of(conn, plain), role_of(conn, outsider)) == ('student', 'student')
    # admin nunca nasce do cadastro.
    assert role_of(conn, signup(conn, f'x-{uuid4()}@unb.br', role='admin', confirmed=True)) == 'student'


def test_role_changes_are_audited_and_only_admins_read_the_trail(database):
    conn, users = database
    assume(conn, users['admin'])
    conn.execute(text("select public.admin_definir_papel(:u, 'professor', 'student')"), {'u': users['ana']})
    trail = conn.execute(text("""select ator_id::text, papel_anterior, papel_novo
        from public.auditoria_papeis where usuario_id=:u"""), {'u': users['ana']}).all()
    assert trail == [(users['admin'], 'student', 'professor')]
    denied(conn, 'delete from public.auditoria_papeis')
    denied(conn, "update public.auditoria_papeis set papel_novo='student'")

    for uid in (users['ana'], users['bruno']):
        assume(conn, uid)
        assert scalar(conn, 'select count(*) from public.auditoria_papeis') == 0
    assume(conn)
    hidden(conn, 'select count(*) from public.auditoria_papeis')
