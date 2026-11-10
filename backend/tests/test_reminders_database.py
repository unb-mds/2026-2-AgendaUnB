"""S8-B03 (#81) e ADR-013: lembretes persistentes 24 h antes do início.

Testes contra o Supabase LOCAL migrado; cada teste desfaz suas alterações.
Rode com TEST_SUPABASE_DB_URL (nunca produção).

O agendador é simulado pela conexão privilegiada (as_backend); o navegador,
pelos papéis anon e authenticated.
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


def row(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).mappings().one()


def manual_event(conn, author, status='aprovado', **extra):
    columns = {'autor_id': author, 'titulo': 'Evento de teste', 'descricao': 'Descrição',
               'status': status, **extra}
    names = ', '.join(columns)
    values = ', '.join(f':{name}' for name in columns)
    date = '' if 'data_evento' in columns or 'dia_inteiro' in columns else ", data_evento"
    date_value = '' if not date else ", now() + interval '10 days'"
    return str(conn.execute(text(f'insert into public.eventos({names}{date}) values ({values}{date_value}) returning id'),
                            columns).scalar_one())


def personal_event(conn, owner, start_sql="now() + interval '10 days'"):
    return str(conn.execute(text(f"""insert into public.eventos_pessoais(user_id, titulo, data_hora)
        values (:u, 'Compromisso privado', {start_sql}) returning id"""), {'u': owner}).scalar_one())


REMINDERS = "select count(*) from public.lembretes where user_id=:u"


def test_personal_event_schedules_one_reminder_24h_before(database):
    conn, users = database
    event_id = personal_event(conn, users['ana'])
    reminder = row(conn, """select status, tipo_evento, inicio_referencia - agendado_para as antecedencia
        from public.lembretes where evento_pessoal_id=:id""", {'id': event_id})
    assert (reminder['status'], reminder['tipo_evento']) == ('pendente', 'pessoal')
    assert reminder['antecedencia'].total_seconds() == 24 * 3600

    # editar sem mudar o início não duplica
    conn.execute(text("update public.eventos_pessoais set titulo='Novo título' where id=:id"), {'id': event_id})
    assert scalar(conn, REMINDERS, {'u': users['ana']}) == 1

    # mudar o início troca o aviso pendente
    conn.execute(text("update public.eventos_pessoais set data_hora = now() + interval '20 days' where id=:id"), {'id': event_id})
    assert scalar(conn, REMINDERS, {'u': users['ana']}) == 1
    assert scalar(conn, """select inicio_referencia = now() + interval '20 days'
        from public.lembretes where evento_pessoal_id=:id""", {'id': event_id})

    # trazer o início para dentro da janela cancela, sem aviso retroativo
    conn.execute(text("update public.eventos_pessoais set data_hora = now() + interval '3 hours' where id=:id"), {'id': event_id})
    assert scalar(conn, REMINDERS, {'u': users['ana']}) == 0

    other = personal_event(conn, users['ana'])
    conn.execute(text('delete from public.eventos_pessoais where id=:id'), {'id': other})
    assert scalar(conn, REMINDERS, {'u': users['ana']}) == 0


def test_event_created_inside_the_window_gets_no_reminder(database):
    conn, users = database
    personal_event(conn, users['ana'], "now() + interval '23 hours'")
    personal_event(conn, users['ana'], "now() - interval '1 day'")
    assert scalar(conn, REMINDERS, {'u': users['ana']}) == 0


def test_all_day_reminder_uses_local_midnight_of_the_first_day(database):
    conn, users = database
    conn.execute(text("""insert into public.eventos_pessoais(user_id, titulo, data_hora, dia_inteiro, data_inicio_civil, data_fim_civil)
        values (:u, 'Feriado', now(), true, '2030-04-21', '2030-04-23')"""), {'u': users['ana']})
    assert str(scalar(conn, """select agendado_para at time zone 'America/Sao_Paulo'
        from public.lembretes where user_id=:u""", {'u': users['ana']})) == '2030-04-20 00:00:00'


def test_saved_public_event_reminder_follows_the_event(database):
    conn, users = database
    event_id = manual_event(conn, users['professor'])
    save = 'insert into public.eventos_salvos(user_id, event_id) values (:u, :e)'
    conn.execute(text(save), {'u': users['ana'], 'e': event_id})
    conn.execute(text(save), {'u': users['bruno'], 'e': event_id})
    assert scalar(conn, 'select count(*) from public.lembretes where evento_id=:e', {'e': event_id}) == 2

    # remover da agenda cancela só o aviso de quem removeu
    conn.execute(text('delete from public.eventos_salvos where user_id=:u and event_id=:e'), {'u': users['bruno'], 'e': event_id})
    assert scalar(conn, REMINDERS, {'u': users['bruno']}) == 0
    assert scalar(conn, REMINDERS, {'u': users['ana']}) == 1

    # o evento mudou de data: o aviso acompanha
    conn.execute(text("update public.eventos set data_evento = now() + interval '30 days' where id=:e"), {'e': event_id})
    assert scalar(conn, """select count(*) from public.lembretes
        where user_id=:u and inicio_referencia = now() + interval '30 days'""", {'u': users['ana']}) == 1

    # saiu do catálogo: cancela; voltou: reagenda
    conn.execute(text("update public.eventos set status='rejeitado' where id=:e"), {'e': event_id})
    assert scalar(conn, REMINDERS, {'u': users['ana']}) == 0
    conn.execute(text("update public.eventos set status='aprovado' where id=:e"), {'e': event_id})
    assert scalar(conn, REMINDERS, {'u': users['ana']}) == 1


def make_due(conn, where, params):
    """Simula a passagem do tempo: o aviso pendente já deveria ter disparado."""
    conn.execute(text(f"update public.lembretes set agendado_para = now() - interval '1 minute' where {where}"), params)


def test_firing_is_idempotent_and_reminders_are_private(database):
    conn, users = database
    ana_event = personal_event(conn, users['ana'])
    personal_event(conn, users['bruno'])
    make_due(conn, 'evento_pessoal_id=:id', {'id': ana_event})

    # antes do disparo o aviso não aparece nem para o dono
    assume(conn, users['ana'])
    assert scalar(conn, 'select count(*) from public.lembretes') == 0

    as_backend(conn)
    assert scalar(conn, 'select public.disparar_lembretes()') == 1
    assert scalar(conn, 'select public.disparar_lembretes()') == 0   # reexecução ou reinício do job
    assert scalar(conn, "select count(*) from public.lembretes where status='disparado'") == 1

    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.lembretes') == 0
    blocked(conn, 'update public.lembretes set lido_em = now() where evento_pessoal_id=:id', {'id': ana_event})

    assume(conn)
    denied(conn, 'select count(*) from public.lembretes')

    assume(conn, users['ana'])
    assert scalar(conn, 'select count(*) from public.lembretes') == 1   # continua lá quando ela volta
    denied(conn, 'select public.disparar_lembretes()')
    denied(conn, "update public.lembretes set status='pendente' where evento_pessoal_id=:id", {'id': ana_event})
    denied(conn, 'delete from public.lembretes where evento_pessoal_id=:id', {'id': ana_event})
    denied(conn, """insert into public.lembretes(user_id, tipo_evento, evento_pessoal_id, inicio_referencia, agendado_para)
        values (:u, 'pessoal', :id, now() + interval '2 days', now())""", {'u': users['ana'], 'id': ana_event})
    assert conn.execute(text('update public.lembretes set lido_em = now() where evento_pessoal_id=:id'),
                        {'id': ana_event}).rowcount == 1

    as_backend(conn)
    first_read = scalar(conn, 'select lido_em from public.lembretes where evento_pessoal_id=:id', {'id': ana_event})
    conn.execute(text("update public.lembretes set lido_em = now() + interval '1 hour' where evento_pessoal_id=:id"), {'id': ana_event})
    assert scalar(conn, 'select lido_em from public.lembretes where evento_pessoal_id=:id', {'id': ana_event}) == first_read


def test_firing_revalidates_the_event(database):
    conn, users = database
    event_id = manual_event(conn, users['professor'])
    conn.execute(text('insert into public.eventos_salvos(user_id, event_id) values (:u, :e)'), {'u': users['ana'], 'e': event_id})
    started = personal_event(conn, users['ana'])
    make_due(conn, 'user_id=:u', {'u': users['ana']})

    # o evento público saiu do catálogo sem passar pelo trigger (trava extra) e o
    # compromisso já começou: nenhum dos dois avisos é entregue
    conn.execute(text('alter table public.eventos disable trigger eventos_reagenda_lembretes'))
    conn.execute(text("update public.eventos set status='rejeitado' where id=:e"), {'e': event_id})
    conn.execute(text('alter table public.eventos enable trigger eventos_reagenda_lembretes'))
    conn.execute(text("""update public.lembretes set inicio_referencia = now() - interval '1 hour',
        agendado_para = now() - interval '25 hours' where evento_pessoal_id=:id"""), {'id': started})
    conn.execute(text('alter table public.eventos_pessoais disable trigger eventos_pessoais_agenda_lembrete'))
    conn.execute(text("update public.eventos_pessoais set data_hora = now() - interval '1 hour' where id=:id"), {'id': started})
    conn.execute(text('alter table public.eventos_pessoais enable trigger eventos_pessoais_agenda_lembrete'))

    assert scalar(conn, 'select public.disparar_lembretes()') == 0
    assert scalar(conn, REMINDERS, {'u': users['ana']}) == 0
