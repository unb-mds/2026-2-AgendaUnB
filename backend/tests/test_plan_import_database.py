"""S7-B04 (#72) e ADR-010: confirmação idempotente e importação por usuário.

Testes contra o Supabase LOCAL migrado; cada teste desfaz suas alterações.
Rode com TEST_SUPABASE_DB_URL (nunca produção).

As funções recebem o ator porque o back-end conecta com um usuário que
ignora RLS: quem confere a permissão é o banco.
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


def refused(conn, sqlstate, sql, params=None):
    """A chamada falha com o código que a API traduz para o status HTTP."""
    with conn.begin_nested():
        with pytest.raises(DBAPIError) as error:
            with conn.begin_nested():
                conn.execute(text(sql), params or {})
    assert error.value.orig.sqlstate == sqlstate, str(error.value.orig)


def denied(conn, sql, params=None):
    with conn.begin_nested():
        with pytest.raises(DBAPIError):
            with conn.begin_nested():
                conn.execute(text(sql), params or {})


def scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar()


def row(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).mappings().one()


def offering(conn):
    subject_id = conn.execute(text("""insert into public.disciplinas(origem, codigo, nome)
        values ('followw', :code, 'Métodos de Desenvolvimento de Software') returning id"""),
        {'code': 'T' + uuid4().hex[:8].upper()}).scalar_one()
    return str(conn.execute(text("""insert into public.ofertas_turma(disciplina_id, turma, ano, semestre)
        values (:s, '01', 2026, 2) returning id"""), {'s': subject_id}).scalar_one())


def follow(conn, user_id, offering_id):
    conn.execute(text('insert into public.vinculos_turma(user_id, oferta_id) values (:u, :o)'),
                 {'u': user_id, 'o': offering_id})


def plan(conn, owner, offering_id=None, status='concluido'):
    """Plano com a versão 1 (criada pelo banco) e dois candidatos. Devolve (plano, versão, [candidatos])."""
    plan_id = str(uuid4())
    done = 'now()' if status in ('concluido', 'falha') else 'null'
    started = 'now()' if status == 'processando' else 'null'
    conn.execute(text(f"""insert into public.planos_ensino(id, user_id, nome_arquivo, caminho_arquivo,
            tipo_arquivo, status, processado_em, processamento_iniciado_em, oferta_id)
        values (:id, :owner, 'plano.pdf', :path, 'pdf', :status, {done}, {started}, :offering)"""),
        {'id': plan_id, 'owner': owner, 'path': f'syllabus_files/{owner}/{plan_id}_plano.pdf',
         'status': status, 'offering': offering_id})
    version_id = str(scalar(conn, 'select id from public.versoes_plano where plano_id=:p', {'p': plan_id}))
    candidates = [
        str(conn.execute(text("""insert into public.avaliacoes(plano_id, versao_id, ordem, titulo, data_avaliacao, tipo, ambiguo, pagina_origem, trecho_origem)
            values (:p, :v, :o, :t, :d, 'prova', :a, 2, 'trecho do plano') returning id"""),
            {'p': plan_id, 'v': version_id, 'o': order, 't': title, 'd': date, 'a': ambiguous}).scalar_one())
        for order, (title, date, ambiguous) in enumerate([
            ('Prova 1', '2027-04-10T10:00:00-03:00', False),
            ('Prova 2', None, True),
        ])
    ]
    return plan_id, version_id, candidates


def share(conn, actor, version_id):
    """Marca a versão como compartilhada. O fluxo de compartilhamento é da S8-B01 (#77)."""
    conn.execute(text("""update public.versoes_plano set visibilidade = 'compartilhada', compartilhada_em = now()
        where id = :v and autor_id = :a"""), {'a': actor, 'v': version_id})
    return 'compartilhada'


def confirm(conn, actor, key, version_id, items):
    return conn.execute(text('select public.confirmar_importacao(:a, :k, :v, cast(:i as jsonb))'),
                        {'a': actor, 'k': key, 'v': version_id, 'i': json.dumps(items)}).scalar_one()


CONFIRM = 'select public.confirmar_importacao(:a, :k, :v, cast(:i as jsonb))'
EVENTS = 'select count(*) from public.eventos_pessoais where user_id=:u'


def test_two_followers_import_into_independent_agendas(database):
    conn, users = database
    turma = offering(conn)
    _, version_id, candidates = plan(conn, users['ana'], turma)
    for name in ('bruno', 'carla'):
        follow(conn, users[name], turma)
    share(conn, users['ana'], version_id)
    items = [{'candidato_id': candidates[0]}]

    for name in ('bruno', 'carla'):
        result = confirm(conn, users[name], f'chave-{name}-0001', version_id, items)
        assert result['repetida'] is False and result['itens'][0]['resultado'] == 'criado'
    assert scalar(conn, EVENTS, {'u': users['bruno']}) == scalar(conn, EVENTS, {'u': users['carla']}) == 1

    event = row(conn, """select titulo, origem_avaliacao_id, origem_versao_id, origem_pagina, origem_trecho
        from public.eventos_pessoais where user_id=:u""", {'u': users['bruno']})
    assert event['titulo'] == 'Prova 1' and str(event['origem_avaliacao_id']) == candidates[0]
    assert str(event['origem_versao_id']) == version_id and event['origem_pagina'] == 2
    # a decisão de quem importa não altera o candidato compartilhado
    assert scalar(conn, 'select status from public.avaliacoes where id=:c', {'c': candidates[0]}) == 'pendente'

    # quem não segue a turma, e visitante, são recusados
    refused(conn, '42501', CONFIRM, {'a': users['professor'], 'k': 'chave-prof-0001', 'v': version_id, 'i': json.dumps(items)})
    for uid in (None, users['bruno']):
        assume(conn, uid)
        denied(conn, CONFIRM, {'a': users['bruno'], 'k': 'chave-navegador', 'v': version_id, 'i': json.dumps(items)})


def test_retry_with_the_same_key_never_duplicates_or_restores(database):
    conn, users = database
    _, version_id, candidates = plan(conn, users['ana'])
    items = [{'candidato_id': candidates[0], 'titulo': 'P1 de MDS'}]

    first = confirm(conn, users['ana'], 'chave-acao-0001', version_id, items)
    retry = confirm(conn, users['ana'], 'chave-acao-0001', version_id, items)
    assert retry['repetida'] is True and retry['operacao_id'] == first['operacao_id']
    assert retry['itens'][0]['evento_id'] == first['itens'][0]['evento_id']
    assert scalar(conn, EVENTS, {'u': users['ana']}) == 1
    assert scalar(conn, 'select status from public.avaliacoes where id=:c', {'c': candidates[0]}) == 'confirmado'

    # mesma chave, outro conteúdo
    refused(conn, 'AG409', CONFIRM, {'a': users['ana'], 'k': 'chave-acao-0001', 'v': version_id,
                                     'i': json.dumps([{'candidato_id': candidates[0], 'titulo': 'Outro título'}])})

    # outra ação sobre o mesmo candidato: continua um único evento ativo
    other = confirm(conn, users['ana'], 'chave-acao-0002', version_id, items)
    assert other['itens'][0]['resultado'] == 'ja_importado'
    assert scalar(conn, EVENTS, {'u': users['ana']}) == 1

    # a pessoa apaga o evento; o retry antigo informa a remoção e não o recria
    conn.execute(text('delete from public.eventos_pessoais where user_id=:u'), {'u': users['ana']})
    stale = confirm(conn, users['ana'], 'chave-acao-0001', version_id, items)
    assert stale['itens'][0] == {'candidato_id': candidates[0], 'evento_id': None, 'resultado': 'criado', 'removido': True}
    assert scalar(conn, EVENTS, {'u': users['ana']}) == 0

    # "Adicionar novamente": chave nova recria, e o histórico anterior permanece
    again = confirm(conn, users['ana'], 'chave-acao-0003', version_id, items)
    assert again['itens'][0]['resultado'] == 'criado' and scalar(conn, EVENTS, {'u': users['ana']}) == 1
    assert scalar(conn, 'select count(*) from public.operacoes_importacao where user_id=:u', {'u': users['ana']}) == 3


def test_invalid_selection_writes_nothing(database):
    conn, users = database
    _, version_id, candidates = plan(conn, users['ana'])
    _, _, foreign = plan(conn, users['ana'])

    cases = [
        [{'candidato_id': candidates[0]}, {'candidato_id': foreign[0]}],          # candidato de outro plano
        [{'candidato_id': candidates[0]}, {'candidato_id': candidates[1]}],       # data ambígua sem correção
        [{'candidato_id': candidates[0]}, {'candidato_id': candidates[0]}],       # repetido
        [{'candidato_id': candidates[0], 'inicio': '2027-04-10T10:00:00'}],       # sem fuso
        [{'candidato_id': candidates[0], 'titulo': 'ab'}],
        [{'candidato_id': candidates[0], 'dia_inteiro': True, 'data_inicio': '2027-04-10', 'data_fim': '2027-04-10'}],
        [],
    ]
    for number, items in enumerate(cases):
        refused(conn, '22023', CONFIRM, {'a': users['ana'], 'k': f'chave-invalida-{number}', 'v': version_id,
                                         'i': json.dumps(items)})
    refused(conn, '22023', CONFIRM, {'a': users['ana'], 'k': 'curta', 'v': version_id,
                                     'i': json.dumps([{'candidato_id': candidates[0]}])})
    # rollback completo: nem evento, nem operação, nem candidato marcado
    assert scalar(conn, EVENTS, {'u': users['ana']}) == 0
    assert scalar(conn, 'select count(*) from public.operacoes_importacao where user_id=:u', {'u': users['ana']}) == 0
    assert scalar(conn, 'select status from public.avaliacoes where id=:c', {'c': candidates[0]}) == 'pendente'

    # a mesma chave serve depois de corrigir, porque a ação inválida não foi registrada
    fixed = confirm(conn, users['ana'], 'chave-invalida-1', version_id, [
        {'candidato_id': candidates[0]},
        {'candidato_id': candidates[1], 'dia_inteiro': True, 'data_inicio': '2027-05-08'},
    ])
    assert [item['resultado'] for item in fixed['itens']] == ['criado', 'criado']
    all_day = row(conn, """select dia_inteiro, data_inicio_civil, data_fim_civil from public.eventos_pessoais
        where user_id=:u and origem_avaliacao_id=:c""", {'u': users['ana'], 'c': candidates[1]})
    assert all_day['dia_inteiro'] and (str(all_day['data_inicio_civil']), str(all_day['data_fim_civil'])) == ('2027-05-08', '2027-05-09')


def test_discarded_and_unfinished_plans_are_refused(database):
    conn, users = database
    _, version_id, candidates = plan(conn, users['ana'])
    conn.execute(text("update public.avaliacoes set status='descartado' where id=:c"), {'c': candidates[0]})
    refused(conn, '22023', CONFIRM, {'a': users['ana'], 'k': 'chave-descartado', 'v': version_id,
                                     'i': json.dumps([{'candidato_id': candidates[0]}])})
    _, processing, pending = plan(conn, users['ana'], status='processando')
    refused(conn, '55000', CONFIRM, {'a': users['ana'], 'k': 'chave-processando', 'v': processing,
                                     'i': json.dumps([{'candidato_id': pending[0]}])})
    refused(conn, 'P0002', CONFIRM, {'a': users['ana'], 'k': 'chave-inexistente', 'v': str(uuid4()),
                                     'i': json.dumps([{'candidato_id': candidates[0]}])})


def test_import_history_is_private(database):
    conn, users = database
    _, version_id, candidates = plan(conn, users['ana'])
    confirm(conn, users['ana'], 'chave-acao-0001', version_id, [{'candidato_id': candidates[0]}])
    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.operacoes_importacao') == 0
    assert scalar(conn, 'select count(*) from public.itens_importacao') == 0
    assume(conn, users['ana'])
    assert scalar(conn, 'select count(*) from public.itens_importacao') == 1
    denied(conn, 'delete from public.operacoes_importacao')
    denied(conn, "update public.itens_importacao set resultado='ja_importado'")
    assume(conn)
    denied(conn, 'select count(*) from public.operacoes_importacao')


def test_concurrent_confirmations_create_a_single_event(database):
    """Duas conexões reais confirmando o mesmo candidato com chaves diferentes."""
    conn, users = database
    url = os.getenv('TEST_SUPABASE_DB_URL')
    engine = create_engine(url)
    setup = engine.connect()
    uid = str(uuid4())
    try:
        setup.execute(text("insert into auth.users(id,email,raw_user_meta_data) values (:id,:e,:m)"),
                      {'id': uid, 'e': f'test-{uid}@unb.br', 'm': json.dumps({'nome_completo': 'Teste concorrente'})})
        _, version_id, candidates = plan(setup, uid)
        setup.commit()

        from concurrent.futures import ThreadPoolExecutor

        def run(key):
            with engine.connect() as worker:
                result = confirm(worker, uid, key, version_id, [{'candidato_id': candidates[0]}])
                worker.commit()
                return result['itens'][0]['resultado']

        with ThreadPoolExecutor(max_workers=4) as pool:
            results = sorted(pool.map(run, [f'chave-concorrente-{n}' for n in range(4)]))
        assert results == ['criado', 'ja_importado', 'ja_importado', 'ja_importado']
        assert scalar(setup, EVENTS, {'u': uid}) == 1
    finally:
        setup.rollback()
        setup.execute(text('delete from public.eventos_pessoais where user_id=:u'), {'u': uid})
        setup.execute(text('delete from auth.users where id=:u'), {'u': uid})
        setup.commit()
        setup.close()
        engine.dispose()
