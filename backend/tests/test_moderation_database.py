"""Opt-in integration tests against migrated LOCAL Supabase; every test rolls back.

Run with TEST_SUPABASE_DB_URL (never production). Exercises real PostgreSQL RLS,
RPCs and triggers, which SQLite API tests cannot verify.
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
        for role in ('student', 'other', 'professor', 'admin', 'personal'):
            uid = str(uuid4())
            email = f'test-{uid}@example.com' if role == 'personal' else f'test-{uid}@unb.br'
            conn.execute(text("insert into auth.users(id,email,raw_user_meta_data) values (:id,:email,:meta)"),
                         {'id': uid, 'email': email, 'meta': json.dumps({'nome_completo': 'Teste ' + role})})
            if role in ('professor', 'admin'):
                conn.execute(text('update public.profiles set papel=:role where id=:id'), {'role': role, 'id': uid})
            users[role] = uid
        yield conn, users
        transaction.rollback()
    engine.dispose()


def assume(conn, uid):
    conn.execute(text('reset role'))
    conn.execute(text("select set_config('request.jwt.claim.sub', :uid, true)"), {'uid': uid})
    conn.execute(text('set local role authenticated'))


def suggestion(conn, author):
    return str(conn.execute(text("""insert into public.eventos(autor_id,titulo,descricao,data_evento,status)
        values (:author, 'Sugestão de teste', 'Descrição', now() + interval '1 day', 'aprovado') returning id"""),
        {'author': author}).scalar_one())


def denied(conn, sql, params=None):
    with conn.begin_nested():
        with pytest.raises(DBAPIError):
            # Nested savepoint must roll back after the expected statement error.
            with conn.begin_nested():
                conn.execute(text(sql), params or {})


def test_student_rls_submission_and_notifications(database):
    conn, users = database
    assume(conn, users['student'])
    event_id = suggestion(conn, users['student'])
    event = conn.execute(text('select status, justificativa_recusa, interessados_count from public.eventos where id=:id'), {'id': event_id}).one()
    assert tuple(event) == ('pendente', None, 0)
    assert conn.execute(text("select count(*) from public.notificacoes where evento_id=:id and tipo='submissao'"), {'id': event_id}).scalar() == 1
    assert conn.execute(text('select count(*) from public.profiles')).scalar() == 1
    denied(conn, 'select public.listar_sugestoes()')
    denied(conn, 'select public.admin_buscar_usuarios()')
    denied(conn, "select public.moderar_sugestao(:id,'aprovado')", {'id': event_id})
    # Direct UPDATE has no policy and cannot change any pending event.
    assert conn.execute(text("update public.eventos set status='aprovado' where id=:id"), {'id': event_id}).rowcount == 0
    denied(conn, "update public.notificacoes set titulo_evento='forjado'")
    assume(conn, users['other'])
    assert conn.execute(text('select count(*) from public.eventos where id=:id'), {'id': event_id}).scalar() == 0
    assert conn.execute(text('select count(*) from public.notificacoes where evento_id=:id'), {'id': event_id}).scalar() == 0


@pytest.mark.parametrize('moderator', ['professor', 'admin'])
@pytest.mark.parametrize('status', ['aprovado', 'rejeitado'])
def test_moderation_and_atomic_notification(database, moderator, status):
    conn, users = database
    assume(conn, users['student'])
    event_id = suggestion(conn, users['student'])
    assume(conn, users[moderator])
    listing = conn.execute(text('select public.listar_sugestoes()')).scalar()
    assert any(item['id'] == event_id for item in listing['items'])
    denied(conn, "select public.moderar_sugestao(:id,'rejeitado','   ')", {'id': event_id})
    conn.execute(text('select public.moderar_sugestao(:id,:status,:reason)'),
                 {'id': event_id, 'status': status, 'reason': 'Informe o local do evento.' if status == 'rejeitado' else None})
    denied(conn, "select public.moderar_sugestao(:id,'aprovado')", {'id': event_id})
    assume(conn, users['student'])
    notifications = conn.execute(text('select tipo,justificativa from public.notificacoes where evento_id=:id'), {'id': event_id}).all()
    assert len(notifications) == 2
    assert ('submissao', None) in notifications
    assert (('aprovacao', None) if status == 'aprovado' else ('recusa', 'Informe o local do evento.')) in notifications
    conn.execute(text('update public.notificacoes set lida_em=now() where evento_id=:id'), {'id': event_id})
    assert conn.execute(text('select count(*) from public.notificacoes where evento_id=:id and lida_em is null'), {'id': event_id}).scalar() == 0


def test_admin_role_guards_and_professor_isolation(database):
    conn, users = database
    assume(conn, users['professor'])
    denied(conn, 'select public.admin_listar_usuarios()')
    denied(conn, 'select public.admin_buscar_usuarios()')
    denied(conn, "select public.admin_definir_papel(:id,'admin','student')", {'id': users['student']})
    assert conn.execute(text('select count(*) from public.profiles')).scalar() == 1
    assume(conn, users['admin'])
    denied(conn, "select public.admin_definir_papel(:id,'student','admin')", {'id': users['admin']})
    denied(conn, "select public.admin_definir_papel(:id,'admin','professor')", {'id': users['student']})
    conn.execute(text("select public.admin_definir_papel(:id,'professor','student')"), {'id': users['student']})
    assert conn.execute(text('select papel from public.profiles where id=:id'), {'id': users['student']}).scalar() == 'professor'
    result = conn.execute(text("select public.admin_buscar_usuarios('Teste student','professor')")).scalar()
    assert result['total'] == 1
    assert result['items'][0]['id'] == users['student']


def test_admin_can_promote_personal_email_but_user_cannot(database):
    conn, users = database
    personal = users['personal']
    assume(conn, personal)
    denied(conn, "update public.profiles set papel='professor' where id=:id", {'id': personal})
    assert conn.execute(text('select papel from public.profiles where id=:id'), {'id': personal}).scalar() == 'student'

    assume(conn, users['admin'])
    conn.execute(text("select public.admin_definir_papel(:id,'professor','student')"), {'id': personal})
    assert conn.execute(text('select papel from public.profiles where id=:id'), {'id': personal}).scalar() == 'professor'
    assume(conn, personal)
    assert conn.execute(text('select public.is_event_moderator()')).scalar() is True
