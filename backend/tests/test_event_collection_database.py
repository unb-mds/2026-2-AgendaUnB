"""S7-B05 (#75) e ADR-011: datas de eventos e coleta da Agenda UnB Notícias.

Testes contra o Supabase LOCAL migrado; cada teste desfaz suas alterações.
Rode com TEST_SUPABASE_DB_URL (nunca produção).

O coletor é simulado pela conexão privilegiada (as_backend); o navegador,
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


def collect(conn, **item):
    """Chama a função de coleta como o coletor faria."""
    payload = {
        'fonte': 'agenda_unb_noticias', 'fonte_id': '4521',
        'fonte_url': 'https://noticias.unb.br/agenda/4521', 'hash': 'hash-inicial',
        'titulo': 'Semana Universitária 2026', 'descricao': 'Programação da semana.',
        'inicio': '2027-03-18T14:00:00-03:00', **item,
    }
    payload = {key: value for key, value in payload.items() if value is not None}
    return conn.execute(text('select public.registrar_evento_coletado(cast(:p as jsonb))'),
                        {'p': json.dumps(payload)}).scalar_one()


def manual_event(conn, author, status='aprovado', **extra):
    columns = {'autor_id': author, 'titulo': 'Evento de teste', 'descricao': 'Descrição',
               'status': status, **extra}
    names = ', '.join(columns)
    values = ', '.join(f':{name}' for name in columns)
    date = '' if 'data_evento' in columns or 'dia_inteiro' in columns else ", data_evento"
    date_value = '' if not date else ", now() + interval '10 days'"
    return str(conn.execute(text(f'insert into public.eventos({names}{date}) values ({values}{date_value}) returning id'),
                            columns).scalar_one())


# ---------------------------------------------------------------------------
# Datas (ADR-011)
# ---------------------------------------------------------------------------


def test_all_day_event_uses_civil_dates_with_exclusive_end(database):
    conn, users = database
    event_id = manual_event(conn, users['professor'], dia_inteiro=True,
                            data_inicio_civil='2027-03-18', data_fim_civil='2027-03-21')
    event = row(conn, """select data_evento at time zone 'America/Sao_Paulo' as inicio,
        data_fim at time zone 'America/Sao_Paulo' as fim from public.eventos where id=:id""", {'id': event_id})
    # 18 a 20/03 inclusive: começa na meia-noite local do dia 18 e termina na do dia 21.
    assert str(event['inicio']) == '2027-03-18 00:00:00'
    assert str(event['fim']) == '2027-03-21 00:00:00'

    personal = str(conn.execute(text("""insert into public.eventos_pessoais
        (user_id, titulo, data_hora, dia_inteiro, data_inicio_civil, data_fim_civil)
        values (:u, 'Feriado', now(), true, '2027-04-21', '2027-04-22') returning id"""),
        {'u': users['ana']}).scalar_one())
    assert str(scalar(conn, """select data_hora at time zone 'America/Sao_Paulo'
        from public.eventos_pessoais where id=:id""", {'id': personal})) == '2027-04-21 00:00:00'


def test_invalid_intervals_are_rejected(database):
    conn, users = database
    base = "insert into public.eventos(autor_id, titulo, descricao, status, "
    params = {'a': users['professor']}
    # fim exclusivo precisa ser depois do início
    denied(conn, base + """dia_inteiro, data_inicio_civil, data_fim_civil)
        values (:a, 'Dia inteiro', 'Descrição', 'aprovado', true, '2027-03-18', '2027-03-18')""", params)
    # dia inteiro sem as datas civis
    denied(conn, base + """data_evento, dia_inteiro) values (:a, 'Dia inteiro', 'Descrição', 'aprovado', now(), true)""", params)
    # data civil em evento com horário
    denied(conn, base + """data_evento, data_inicio_civil, data_fim_civil)
        values (:a, 'Com horário', 'Descrição', 'aprovado', now(), '2027-03-18', '2027-03-19')""", params)
    # fim antes do início
    denied(conn, base + """data_evento, data_fim)
        values (:a, 'Com horário', 'Descrição', 'aprovado', now(), now() - interval '1 hour')""", params)
    denied(conn, """insert into public.eventos_pessoais(user_id, titulo, data_hora, data_fim)
        values (:a, 'Compromisso', now(), now())""", params)
    # nada é publicado sem data
    denied(conn, base + "data_evento) values (:a, 'Sem data', 'Descrição', 'aprovado', null)", params)


# ---------------------------------------------------------------------------
# Coleta (S7-B05)
# ---------------------------------------------------------------------------


def test_successive_collections_update_the_same_record(database):
    conn, _ = database
    first = collect(conn)
    assert (first['acao'], first['status'], first['motivo_revisao']) == ('criado', 'aprovado', None)

    again = collect(conn)
    assert (again['acao'], again['id']) == ('inalterado', first['id'])

    moved = collect(conn, hash='hash-nova-data', inicio='2027-03-19T10:00:00-03:00',
                    fim='2027-03-19T12:00:00-03:00')
    assert (moved['acao'], moved['id'], moved['status']) == ('atualizado', first['id'], 'aprovado')

    assert scalar(conn, "select count(*) from public.eventos where fonte_id='4521'") == 1
    event = row(conn, """select autor_id, sugestao_estudante, link_externo, fonte_url,
        data_evento at time zone 'America/Sao_Paulo' as inicio,
        data_fim at time zone 'America/Sao_Paulo' as fim from public.eventos where id=:id""", {'id': first['id']})
    assert event['autor_id'] is None and event['sugestao_estudante'] is False
    assert str(event['inicio']) == '2027-03-19 10:00:00' and str(event['fim']) == '2027-03-19 12:00:00'
    # sem link próprio, o evento aponta para a página de origem
    assert event['link_externo'] == event['fonte_url'] == 'https://noticias.unb.br/agenda/4521'


def test_all_day_collected_event(database):
    conn, _ = database
    result = collect(conn, inicio=None, dia_inteiro=True, data_inicio='2027-03-18', data_fim='2027-03-21')
    event = row(conn, 'select dia_inteiro, data_inicio_civil, data_fim_civil, status from public.eventos where id=:id',
                {'id': result['id']})
    assert event['dia_inteiro'] and str(event['data_inicio_civil']) == '2027-03-18'
    assert str(event['data_fim_civil']) == '2027-03-21' and event['status'] == 'aprovado'
    # um único dia: o fim exclusivo é o dia seguinte
    single = collect(conn, fonte_id='4600', fonte_url='https://noticias.unb.br/agenda/4600',
                     titulo='Aula inaugural', inicio=None, dia_inteiro=True, data_inicio='2027-03-22')
    assert str(scalar(conn, 'select data_fim_civil from public.eventos where id=:id', {'id': single['id']})) == '2027-03-23'


@pytest.mark.parametrize('item, reason', [
    ({'inicio': None}, 'incompleto'),
    ({'ambiguo': True}, 'ambiguo'),
    ({'tipo': 'informe'}, 'informe'),
    ({'fim': '2027-03-18T13:00:00-03:00'}, 'ambiguo'),  # fim antes do início
])
def test_incomplete_or_ambiguous_items_wait_for_review(database, item, reason):
    conn, _ = database
    result = collect(conn, **item)
    assert (result['status'], result['motivo_revisao']) == ('pendente', reason)
    # fora do catálogo público enquanto ninguém decidir
    assume(conn)
    assert scalar(conn, 'select count(*) from public.eventos where id=:id', {'id': result['id']}) == 0


def test_instants_must_carry_an_offset(database):
    conn, _ = database
    with pytest.raises(DBAPIError):
        with conn.begin_nested():
            collect(conn, inicio='2027-03-18T14:00:00')
    with pytest.raises(DBAPIError):
        with conn.begin_nested():
            collect(conn, fonte_id=None)
    with pytest.raises(DBAPIError):
        with conn.begin_nested():
            collect(conn, titulo='  ')


def test_unsafe_link_is_dropped_instead_of_published(database):
    conn, _ = database
    result = collect(conn, link_externo='javascript:alert(1)')
    assert scalar(conn, 'select link_externo from public.eventos where id=:id',
                  {'id': result['id']}) == 'https://noticias.unb.br/agenda/4521'


def test_similar_title_on_the_same_day_goes_to_review(database):
    conn, users = database
    existing = manual_event(conn, users['professor'], titulo='SEMANA universitária — 2026!',
                            data_evento='2027-03-18T09:00:00-03:00')
    result = collect(conn)
    assert (result['status'], result['motivo_revisao']) == ('pendente', 'possivel_duplicata')
    assert str(scalar(conn, 'select possivel_duplicata_de from public.eventos where id=:id',
                      {'id': result['id']})) == existing
    # uma nova coleta não publica o item por conta própria
    later = collect(conn, hash='hash-segundo', descricao='Texto revisado.')
    assert (later['status'], later['motivo_revisao']) == ('pendente', 'possivel_duplicata')


def test_manual_event_with_the_same_url_is_reconciled(database):
    conn, users = database
    manual = manual_event(conn, users['professor'], titulo='Título escolhido pela professora',
                          link_externo='https://noticias.unb.br/agenda/4521/')
    result = collect(conn)
    assert (result['acao'], result['id']) == ('conciliado', manual)
    assert scalar(conn, "select count(*) from public.eventos where fonte_id='4521' or id=:id", {'id': manual}) == 1

    # o conteúdo cadastrado na plataforma prevalece sobre coletas seguintes
    collect(conn, hash='hash-segundo', titulo='Título da fonte', descricao='Descrição da fonte')
    event = row(conn, 'select titulo, descricao, autor_id, fonte from public.eventos where id=:id', {'id': manual})
    assert event['titulo'] == 'Título escolhido pela professora' and event['descricao'] == 'Descrição'
    assert str(event['autor_id']) == users['professor'] and event['fonte'] == 'agenda_unb_noticias'


def test_local_edits_survive_new_collections(database):
    conn, _ = database
    created = collect(conn, local='Auditório A')
    # edição feita na plataforma (API ou painel)
    conn.execute(text("update public.eventos set titulo='Título corrigido', data_evento='2027-03-20T08:00:00-03:00' where id=:id"),
                 {'id': created['id']})
    assert scalar(conn, 'select campos_editados from public.eventos where id=:id',
                  {'id': created['id']}) == ['datas', 'titulo']

    collect(conn, hash='hash-segundo', titulo='Título da fonte', local='Auditório B',
            inicio='2027-03-25T14:00:00-03:00')
    event = row(conn, """select titulo, localizacao, data_evento at time zone 'America/Sao_Paulo' as inicio
        from public.eventos where id=:id""", {'id': created['id']})
    assert event['titulo'] == 'Título corrigido'          # editado: mantido
    assert str(event['inicio']) == '2027-03-20 08:00:00'  # editado: mantido
    assert event['localizacao'] == 'Auditório B'          # não editado: atualizado


def test_source_failure_keeps_known_data(database):
    conn, _ = database
    created = collect(conn)
    # leitura parcial: a página deixou de informar a data
    partial = collect(conn, hash='hash-parcial', inicio=None)
    assert (partial['acao'], partial['status']) == ('atualizado', 'aprovado')
    assert scalar(conn, 'select data_evento is not null from public.eventos where id=:id', {'id': created['id']})


def test_moderation_decisions_are_never_undone_by_collection(database):
    conn, users = database
    pending = collect(conn, ambiguo=True)

    assume(conn, users['ana'])
    denied(conn, "select public.moderar_sugestao(:id, 'aprovado')", {'id': pending['id']})
    denied(conn, 'select public.listar_revisoes_coleta()')

    assume(conn, users['professor'])
    queue = scalar(conn, 'select public.listar_revisoes_coleta()')
    assert queue['total'] == 1 and queue['items'][0]['motivo_revisao'] == 'ambiguo'
    assert queue['items'][0]['fonte_url'] == 'https://noticias.unb.br/agenda/4521'
    conn.execute(text("select public.moderar_sugestao(:id, 'rejeitado', 'Não é um evento aberto.')"), {'id': pending['id']})

    as_backend(conn)
    decided = row(conn, 'select status, moderado_por, moderado_em from public.eventos where id=:id', {'id': pending['id']})
    assert decided['status'] == 'rejeitado' and str(decided['moderado_por']) == users['professor']

    after = collect(conn, hash='hash-segundo', ambiguo=False)
    assert (after['acao'], after['status']) == ('atualizado', 'rejeitado')

    # item sem data não pode ser publicado
    undated = collect(conn, fonte_id='4700', fonte_url='https://noticias.unb.br/agenda/4700',
                      titulo='Seminário sem data', inicio=None)
    assume(conn, users['admin'])
    denied(conn, "select public.moderar_sugestao(:id, 'aprovado')", {'id': undated['id']})


def test_browser_cannot_collect_or_forge_provenance(database):
    conn, users = database
    created = collect(conn)
    run_id = str(conn.execute(text("insert into public.coletas_eventos(fonte) values ('agenda_unb_noticias') returning id")).scalar_one())
    payload = {'p': json.dumps({'fonte': 'agenda_unb_noticias', 'fonte_id': '9', 'fonte_url': 'https://noticias.unb.br/9',
                                'hash': 'hash-forjado', 'titulo': 'Evento forjado', 'inicio': '2027-03-18T14:00:00-03:00'})}
    forged = """insert into public.eventos(autor_id, titulo, descricao, data_evento, fonte, fonte_id, fonte_url, fonte_hash, coletado_em)
        values (:a, 'Evento forjado', 'Descrição', now() + interval '2 days', 'agenda_unb_noticias', '9',
                'https://noticias.unb.br/9', 'hash-forjado', now())"""

    for uid in (None, users['ana'], users['professor']):
        assume(conn, uid)
        denied(conn, 'select public.registrar_evento_coletado(cast(:p as jsonb))', payload)
        denied(conn, forged, {'a': uid or users['ana']})
        denied(conn, 'select count(*) from public.coletas_eventos')
        denied(conn, "insert into public.coletas_eventos(fonte) values ('agenda_unb_noticias')")
        blocked(conn, "update public.eventos set fonte_id='outro' where id=:id", {'id': created['id']})
        blocked(conn, "update public.eventos set campos_editados='{}' where id=:id", {'id': created['id']})

    # nem o admin altera a origem pelo navegador
    assume(conn, users['admin'])
    blocked(conn, "update public.eventos set fonte_url='https://exemplo.com/x' where id=:id", {'id': created['id']})

    as_backend(conn)
    assert scalar(conn, 'select fonte_id from public.eventos where id=:id', {'id': created['id']}) == '4521'
    assert scalar(conn, 'select status from public.coletas_eventos where id=:id', {'id': run_id}) == 'executando'


def test_collection_run_log_is_consistent(database):
    conn, _ = database
    run_id = str(conn.execute(text("insert into public.coletas_eventos(fonte) values ('agenda_unb_noticias') returning id")).scalar_one())
    denied(conn, "update public.coletas_eventos set status='concluida' where id=:id", {'id': run_id})
    denied(conn, "update public.coletas_eventos set erro_codigo='timeout' where id=:id", {'id': run_id})
    conn.execute(text("""update public.coletas_eventos set status='falha', concluida_em=now(), erro_codigo='http_503'
        where id=:id"""), {'id': run_id})
