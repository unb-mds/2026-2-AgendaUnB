"""Dados de planos da Release 2: compartilhamento, revisões, votos, importação e catálogo.

S7-B04 (#72), S8-B01 (#77), S7-B03 (#70), ADR-009 e ADR-010. Testes contra o
Supabase LOCAL migrado; cada teste desfaz suas alterações. Rode com
TEST_SUPABASE_DB_URL (nunca produção).

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


def hidden(conn, sql, params=None):
    """Leitura sem resultado: recusada pelo banco ou zero linhas visíveis."""
    try:
        with conn.begin_nested():
            assert conn.execute(text(sql), params or {}).scalar() == 0
    except DBAPIError:
        pass


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
    return conn.execute(text('select (public.compartilhar_versao(:a, :v)).visibilidade'),
                        {'a': actor, 'v': version_id}).scalar_one()


def confirm(conn, actor, key, version_id, items):
    return conn.execute(text('select public.confirmar_importacao(:a, :k, :v, cast(:i as jsonb))'),
                        {'a': actor, 'k': key, 'v': version_id, 'i': json.dumps(items)}).scalar_one()


CONFIRM = 'select public.confirmar_importacao(:a, :k, :v, cast(:i as jsonb))'
EVENTS = 'select count(*) from public.eventos_pessoais where user_id=:u'


# ---------------------------------------------------------------------------
# Compartilhamento e leitura (S8-B01)
# ---------------------------------------------------------------------------

def test_only_the_author_shares_and_only_followers_read(database):
    conn, users = database
    turma = offering(conn)
    _, version_id, candidates = plan(conn, users['ana'], turma)
    follow(conn, users['bruno'], turma)

    # papel nenhum publica material privado alheio
    for other in (users['bruno'], users['professor'], users['admin']):
        refused(conn, '42501', 'select public.compartilhar_versao(:a, :v)', {'a': other, 'v': version_id})
    refused(conn, 'P0002', 'select public.compartilhar_versao(:a, :v)', {'a': users['ana'], 'v': str(uuid4())})

    assert share(conn, users['ana'], version_id) == 'compartilhada'
    assert share(conn, users['ana'], version_id) == 'compartilhada'   # repetir é seguro

    visible = 'select count(*) from public.avaliacoes where versao_id=:v'
    assume(conn, users['bruno'])                    # segue a turma
    assert scalar(conn, visible, {'v': version_id}) == 2
    for outsider in (users['carla'], users['professor'], users['admin']):   # não seguem
        assume(conn, outsider)
        assert scalar(conn, visible, {'v': version_id}) == 0
        assert scalar(conn, 'select count(*) from public.versoes_plano where id=:v', {'v': version_id}) == 0
    assume(conn)
    hidden(conn, visible, {'v': version_id})

    as_backend(conn)
    assert candidates and scalar(conn, 'select public.ator_pode_ler_versao(:a, :v)',
                                 {'a': users['carla'], 'v': version_id}) is False


def test_sharing_requires_a_class_and_a_finished_plan(database):
    conn, users = database
    _, no_class, _ = plan(conn, users['ana'])
    refused(conn, '55000', 'select public.compartilhar_versao(:a, :v)', {'a': users['ana'], 'v': no_class})
    _, pending, _ = plan(conn, users['ana'], offering(conn), status='pendente')
    refused(conn, '55000', 'select public.compartilhar_versao(:a, :v)', {'a': users['ana'], 'v': pending})


def test_shared_content_is_immutable(database):
    conn, users = database
    plan_id, version_id, candidates = plan(conn, users['ana'], offering(conn))
    # privada: o autor ainda ajusta o conteúdo
    conn.execute(text("update public.avaliacoes set titulo='Prova 1 (revisada)' where id=:id"), {'id': candidates[0]})
    share(conn, users['ana'], version_id)

    refused(conn, '55000', "update public.avaliacoes set titulo='Outra' where id=:id", {'id': candidates[0]})
    refused(conn, '55000', "update public.avaliacoes set data_avaliacao=now() where id=:id", {'id': candidates[1]})
    refused(conn, '55000', 'delete from public.avaliacoes where id=:id', {'id': candidates[0]})
    refused(conn, '55000', """insert into public.avaliacoes(plano_id, versao_id, ordem, titulo)
        values (:p, :v, 9, 'Trabalho extra')""", {'p': plan_id, 'v': version_id})

    # excluir o plano continua possível e leva versões e candidatos
    conn.execute(text('delete from public.planos_ensino where id=:p'), {'p': plan_id})
    assert scalar(conn, 'select count(*) from public.avaliacoes where plano_id=:p', {'p': plan_id}) == 0


def test_withdrawal_blocks_new_access_and_keeps_imported_copies(database):
    conn, users = database
    turma = offering(conn)
    _, version_id, candidates = plan(conn, users['ana'], turma)
    follow(conn, users['bruno'], turma)
    follow(conn, users['carla'], turma)
    share(conn, users['ana'], version_id)
    confirm(conn, users['bruno'], 'chave-bruno-1', version_id, [{'candidato_id': candidates[0]}])
    conn.execute(text('select public.votar_avaliacao(:a, :c, :v)'), {'a': users['bruno'], 'c': candidates[0], 'v': 'confirma'})

    # nem seguidor nem professor retira; autor ou admin, sim
    for other in (users['bruno'], users['professor']):
        refused(conn, '42501', 'select public.retirar_compartilhamento(:a, :v)', {'a': other, 'v': version_id})
    withdrawn = row(conn, 'select (r).visibilidade, (r).retirada_por from public.retirar_compartilhamento(:a, :v) r',
                    {'a': users['admin'], 'v': version_id})
    assert withdrawn['visibilidade'] == 'privada' and str(withdrawn['retirada_por']) == users['admin']
    conn.execute(text('select public.retirar_compartilhamento(:a, :v)'), {'a': users['ana'], 'v': version_id})   # repetir é seguro

    # novos acessos, votos e importações são bloqueados
    assume(conn, users['carla'])
    assert scalar(conn, 'select count(*) from public.avaliacoes where versao_id=:v', {'v': version_id}) == 0
    as_backend(conn)
    refused(conn, '42501', CONFIRM, {'a': users['carla'], 'k': 'chave-carla-1', 'v': version_id,
                                     'i': json.dumps([{'candidato_id': candidates[0]}])})
    refused(conn, 'P0002', 'select public.votar_avaliacao(:a, :c, :v)',
            {'a': users['carla'], 'c': candidates[0], 'v': 'confirma'})

    # a cópia que Bruno já importou continua na agenda dele
    assert scalar(conn, EVENTS, {'u': users['bruno']}) == 1
    assert scalar(conn, 'select count(*) from public.votos_avaliacao where avaliacao_id=:c', {'c': candidates[0]}) == 1


# ---------------------------------------------------------------------------
# Revisões e procedência (S8-B01, ADR-010)
# ---------------------------------------------------------------------------

def revise(conn, actor, version_id):
    return row(conn, """select (r).id, (r).numero, (r).autor_papel, (r).versao_origem_id, (r).visibilidade,
        (r).procedencia_institucional, (r).fonte_institucional_url from public.criar_revisao(:a, :v) r""",
        {'a': actor, 'v': version_id})


def test_revision_creates_a_new_version_and_keeps_the_previous_one(database):
    conn, users = database
    turma = offering(conn)
    _, version_id, candidates = plan(conn, users['ana'], turma)
    follow(conn, users['bruno'], turma)
    share(conn, users['ana'], version_id)
    confirm(conn, users['bruno'], 'chave-bruno-1', version_id, [{'candidato_id': candidates[0]}])

    # estudante que não é o autor não revisa; papel não revisa conteúdo privado
    refused(conn, '42501', 'select public.criar_revisao(:a, :v)', {'a': users['bruno'], 'v': version_id})
    _, private_version, _ = plan(conn, users['carla'], turma)
    for role in ('professor', 'admin'):
        refused(conn, '42501', 'select public.criar_revisao(:a, :v)', {'a': users[role], 'v': private_version})

    revision = revise(conn, users['professor'], version_id)
    assert (revision['numero'], revision['autor_papel'], revision['visibilidade']) == (2, 'professor', 'privada')
    assert str(revision['versao_origem_id']) == version_id
    # papel de professor não cria procedência institucional
    assert revision['procedencia_institucional'] is False

    new_id = str(revision['id'])
    assert scalar(conn, 'select count(*) from public.avaliacoes where versao_id=:v', {'v': new_id}) == 2
    conn.execute(text("update public.avaliacoes set data_avaliacao='2027-04-17T10:00:00-03:00', ambiguo=false where versao_id=:v and ordem=1"),
                 {'v': new_id})

    # o rascunho da revisão é de quem a escreveu: nem a dona do plano o lê
    assume(conn, users['ana'])
    assert scalar(conn, 'select count(*) from public.avaliacoes where versao_id=:v', {'v': new_id}) == 0
    as_backend(conn)

    # professor publica direto a própria revisão; a anterior e as cópias ficam como estavam
    assert share(conn, users['professor'], new_id) == 'compartilhada'
    assert scalar(conn, "select visibilidade from public.versoes_plano where id=:v", {'v': version_id}) == 'compartilhada'
    assert scalar(conn, 'select count(*) from public.avaliacoes where versao_id=:v', {'v': version_id}) == 2
    assert scalar(conn, EVENTS, {'u': users['bruno']}) == 1
    event = row(conn, 'select origem_versao_id, data_hora from public.eventos_pessoais where user_id=:u', {'u': users['bruno']})
    assert str(event['origem_versao_id']) == version_id

    # retirar a original não retira a revisão
    conn.execute(text('select public.retirar_compartilhamento(:a, :v)'), {'a': users['ana'], 'v': version_id})
    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.avaliacoes where versao_id=:v', {'v': new_id}) == 2
    assert scalar(conn, 'select count(*) from public.avaliacoes where versao_id=:v', {'v': version_id}) == 0


def test_institutional_provenance_needs_admin_evidence_and_is_inherited_by_staff_only(database):
    conn, users = database
    turma = offering(conn)
    _, version_id, _ = plan(conn, users['ana'], turma)
    validate = 'select public.validar_procedencia_institucional(:a, :v, :u)'
    url = 'https://fga.unb.br/planos/fga0138.pdf'

    refused(conn, 'P0002', validate, {'a': users['admin'], 'v': version_id, 'u': url})   # ainda privada
    share(conn, users['ana'], version_id)
    refused(conn, '42501', validate, {'a': users['professor'], 'v': version_id, 'u': url})
    refused(conn, '42501', validate, {'a': users['ana'], 'v': version_id, 'u': url})
    refused(conn, '22023', validate, {'a': users['admin'], 'v': version_id, 'u': 'javascript:alert(1)'})
    # sem evidência, o banco não aceita marcar a procedência
    denied(conn, 'update public.versoes_plano set procedencia_institucional=true where id=:v', {'v': version_id})

    conn.execute(text(validate), {'a': users['admin'], 'v': version_id, 'u': url})

    by_professor = revise(conn, users['professor'], version_id)
    assert by_professor['procedencia_institucional'] and by_professor['fonte_institucional_url'] == url
    by_student = revise(conn, users['ana'], version_id)      # a autora revisa o próprio plano
    assert by_student['procedencia_institucional'] is False and by_student['fonte_institucional_url'] is None
    assert (by_professor['numero'], by_student['numero']) == (2, 3)


# ---------------------------------------------------------------------------
# Votos (S8-B01)
# ---------------------------------------------------------------------------

def test_one_vote_per_account_and_candidate(database):
    conn, users = database
    turma = offering(conn)
    _, version_id, candidates = plan(conn, users['ana'], turma)
    for name in ('bruno', 'carla'):
        follow(conn, users[name], turma)
    vote = 'select public.votar_avaliacao(:a, :c, :v)'

    refused(conn, 'P0002', vote, {'a': users['bruno'], 'c': candidates[0], 'v': 'confirma'})   # ainda privada
    share(conn, users['ana'], version_id)
    refused(conn, '42501', vote, {'a': users['professor'], 'c': candidates[0], 'v': 'confirma'})   # não segue a turma
    refused(conn, '22023', vote, {'a': users['bruno'], 'c': candidates[0], 'v': 'talvez'})

    scalar(conn, vote, {'a': users['bruno'], 'c': candidates[0], 'v': 'confirma'})
    repeated = scalar(conn, vote, {'a': users['bruno'], 'c': candidates[0], 'v': 'confirma'})
    assert (repeated['confirmam'], repeated['contestam']) == (1, 0)          # repetir não soma
    scalar(conn, vote, {'a': users['carla'], 'c': candidates[0], 'v': 'confirma'})
    changed = scalar(conn, vote, {'a': users['bruno'], 'c': candidates[0], 'v': 'contesta'})
    assert (changed['confirmam'], changed['contestam'], changed['meu_voto']) == (1, 1, 'contesta')

    summary = conn.execute(text('select * from public.resumo_votos_versao(:a, :v)'),
                           {'a': users['carla'], 'v': version_id}).mappings().all()
    assert [(str(r['avaliacao_id']), r['confirmam'], r['contestam'], r['meu_voto']) for r in summary] == [
        (candidates[0], 1, 1, 'confirma'), (candidates[1], 0, 0, None)]
    refused(conn, '42501', 'select * from public.resumo_votos_versao(:a, :v)', {'a': users['professor'], 'v': version_id})

    # divergência não muda a data do candidato
    assert str(scalar(conn, "select data_avaliacao at time zone 'America/Sao_Paulo' from public.avaliacoes where id=:c",
                      {'c': candidates[0]})) == '2027-04-10 10:00:00'


def test_votes_are_private_and_written_only_by_the_server(database):
    conn, users = database
    turma = offering(conn)
    _, version_id, candidates = plan(conn, users['ana'], turma)
    for name in ('bruno', 'carla'):
        follow(conn, users[name], turma)
    share(conn, users['ana'], version_id)
    scalar(conn, 'select public.votar_avaliacao(:a, :c, :v)', {'a': users['bruno'], 'c': candidates[0], 'v': 'contesta'})

    assume(conn, users['carla'])
    assert scalar(conn, 'select count(*) from public.votos_avaliacao') == 0     # não vê o voto de Bruno
    denied(conn, "insert into public.votos_avaliacao(user_id, avaliacao_id, valor) values (:u, :c, 'confirma')",
           {'u': users['carla'], 'c': candidates[0]})
    denied(conn, 'select public.votar_avaliacao(:a, :c, :v)', {'a': users['bruno'], 'c': candidates[0], 'v': 'confirma'})
    assume(conn, users['bruno'])
    assert scalar(conn, 'select valor from public.votos_avaliacao') == 'contesta'
    denied(conn, "update public.votos_avaliacao set valor='confirma'")
    assume(conn)
    denied(conn, 'select count(*) from public.votos_avaliacao')


# ---------------------------------------------------------------------------
# Confirmação idempotente (S7-B04, ADR-010)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Catálogo (S7-B03, ADR-009)
# ---------------------------------------------------------------------------

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
