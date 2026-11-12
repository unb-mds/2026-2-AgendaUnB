"""S8-D01 (#83): privacidade, termos e ciclo de vida dos dados.

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


def refused(conn, sqlstate, sql, params=None):
    with conn.begin_nested():
        with pytest.raises(DBAPIError) as error:
            with conn.begin_nested():
                conn.execute(text(sql), params or {})
    assert error.value.orig.sqlstate == sqlstate, str(error.value.orig)


def scalar(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar()


def populate(conn, users):
    """Dá a Ana um pouco de tudo o que a plataforma guarda. Bruno segue a turma e importa."""
    ana, bruno = users['ana'], users['bruno']
    subject = conn.execute(text("""insert into public.disciplinas(origem, codigo, nome)
        values ('followw', :c, 'Métodos de Desenvolvimento de Software') returning id"""),
        {'c': 'T' + uuid4().hex[:8].upper()}).scalar_one()
    turma = str(conn.execute(text("""insert into public.ofertas_turma(disciplina_id, turma, ano, semestre)
        values (:s, '01', 2026, 2) returning id"""), {'s': subject}).scalar_one())
    for uid in (ana, bruno):
        conn.execute(text('insert into public.vinculos_turma(user_id, oferta_id) values (:u, :o)'), {'u': uid, 'o': turma})

    plan_id = str(uuid4())
    path = f'syllabus_files/{ana}/{plan_id}_plano.pdf'
    conn.execute(text("""insert into public.planos_ensino(id, user_id, nome_arquivo, caminho_arquivo, tipo_arquivo,
            tamanho_bytes, status, processado_em, oferta_id)
        values (:id, :u, 'plano.pdf', :path, 'pdf', 1024, 'concluido', now(), :o)"""),
        {'id': plan_id, 'u': ana, 'path': path, 'o': turma})
    version_id = str(scalar(conn, 'select id from public.versoes_plano where plano_id=:p', {'p': plan_id}))
    candidate = str(conn.execute(text("""insert into public.avaliacoes(plano_id, versao_id, ordem, titulo, data_avaliacao, trecho_origem)
        values (:p, :v, 0, 'Prova 1', '2027-04-10T10:00:00-03:00', 'trecho do plano') returning id"""),
        {'p': plan_id, 'v': version_id}).scalar_one())
    conn.execute(text('select public.compartilhar_versao(:a, :v)'), {'a': ana, 'v': version_id})
    conn.execute(text("select public.confirmar_importacao(:a, 'chave-bruno-0001', :v, cast(:i as jsonb))"),
                 {'a': bruno, 'v': version_id, 'i': json.dumps([{'candidato_id': candidate}])})
    conn.execute(text("select public.confirmar_importacao(:a, 'chave-ana-00001', :v, cast(:i as jsonb))"),
                 {'a': ana, 'v': version_id, 'i': json.dumps([{'candidato_id': candidate}])})
    conn.execute(text("select public.votar_avaliacao(:a, :c, 'confirma')"), {'a': ana, 'c': candidate})
    conn.execute(text("select public.votar_avaliacao(:a, :c, 'contesta')"), {'a': bruno, 'c': candidate})

    conn.execute(text("""insert into public.eventos_pessoais(user_id, titulo, descricao, data_hora)
        values (:u, 'Consulta médica', 'Anotação particular da Ana', now() + interval '10 days')"""), {'u': ana})
    event = str(conn.execute(text("""insert into public.eventos(autor_id, titulo, descricao, data_evento, status)
        values (:a, 'Palestra aberta', 'Descrição', now() + interval '12 days', 'aprovado') returning id"""),
        {'a': users['professor']}).scalar_one())
    for uid in (ana, bruno):
        conn.execute(text('insert into public.eventos_salvos(user_id, event_id) values (:u, :e)'), {'u': uid, 'e': event})
    conn.execute(text("""insert into public.eventos(autor_id, titulo, descricao, data_evento)
        values (:a, 'Sugestão da Ana', 'Descrição', now() + interval '15 days')"""), {'a': ana})
    conn.execute(text("select public.registrar_aceite_termos(:u, 'termos_de_uso', '2026-11-10')"), {'u': ana})
    conn.execute(text("select public.registrar_consentimento(:u, 'google_agenda', :v, :h)"),
                 {'u': ana, 'v': version_id, 'h': 'a' * 64})
    return {'turma': turma, 'plan': plan_id, 'version': version_id, 'candidate': candidate, 'path': path, 'event': event}


# ---------------------------------------------------------------------------
# Aceite de termos e consentimento
# ---------------------------------------------------------------------------

def test_terms_acceptance_keeps_the_first_date_per_version(database):
    conn, users = database
    accept = 'select (public.registrar_aceite_termos(:u, :d, :v)).aceito_em'
    first = scalar(conn, accept, {'u': users['ana'], 'd': 'termos_de_uso', 'v': '2026-11-10'})
    conn.execute(text("update public.aceites_termos set aceito_em = aceito_em - interval '1 day'"))
    again = scalar(conn, accept, {'u': users['ana'], 'd': 'termos_de_uso', 'v': '2026-11-10'})
    assert again < first                                              # repetir não renova a data
    scalar(conn, accept, {'u': users['ana'], 'd': 'termos_de_uso', 'v': '2027-01-15'})   # versão nova
    scalar(conn, accept, {'u': users['ana'], 'd': 'politica_de_privacidade', 'v': '2026-11-10'})
    assert scalar(conn, 'select count(*) from public.aceites_termos where user_id=:u', {'u': users['ana']}) == 3
    denied(conn, accept, {'u': users['ana'], 'd': 'contrato', 'v': '2026-11-10'})
    denied(conn, accept, {'u': users['ana'], 'd': 'termos_de_uso', 'v': 'v1'})


def test_consent_is_specific_and_revocable(database):
    conn, users = database
    version, other = str(uuid4()), str(uuid4())
    grant = 'select (public.registrar_consentimento(:u, :f, :r, :h)).id'
    has = 'select public.tem_consentimento(:u, :f, :r, :h)'
    p = {'u': users['ana'], 'f': 'google_agenda', 'r': version, 'h': 'a' * 64}

    assert scalar(conn, has, p) is False
    first = scalar(conn, grant, p)
    assert scalar(conn, grant, p) == first                      # repetir não duplica
    assert scalar(conn, has, p) is True
    # mudou o texto (hash) ou a versão: a autorização anterior não vale
    assert scalar(conn, has, {**p, 'h': 'b' * 64}) is False
    assert scalar(conn, has, {**p, 'r': other}) is False
    assert scalar(conn, has, {**p, 'u': users['bruno']}) is False
    # aceitar os termos não é consentir
    conn.execute(text("select public.registrar_aceite_termos(:u, 'termos_de_uso', '2026-11-10')"), {'u': users['bruno']})
    assert scalar(conn, has, {**p, 'u': users['bruno']}) is False

    revoke = 'select public.revogar_consentimento(:u, :f, :r)'
    assert scalar(conn, revoke, {'u': users['ana'], 'f': 'google_agenda', 'r': version}) == 1
    assert scalar(conn, revoke, {'u': users['ana'], 'f': 'google_agenda', 'r': version}) == 0
    assert scalar(conn, has, p) is False
    # o histórico da autorização revogada permanece; autorizar de novo cria outro registro
    assert scalar(conn, grant, p) != first
    assert scalar(conn, 'select count(*) from public.consentimentos where user_id=:u', {'u': users['ana']}) == 2
    denied(conn, grant, {**p, 'f': 'marketing'})
    denied(conn, grant, {**p, 'f': 'envio_texto_ia'})   # registrada no snapshot do plano


def test_legal_records_are_private_and_server_written(database):
    conn, users = database
    conn.execute(text("select public.registrar_aceite_termos(:u, 'termos_de_uso', '2026-11-10')"), {'u': users['ana']})
    conn.execute(text("select public.registrar_consentimento(:u, 'google_agenda')"), {'u': users['ana']})
    conn.execute(text("insert into public.exclusoes_conta(contagens) values ('{}')"))

    assume(conn, users['bruno'])
    assert scalar(conn, 'select count(*) from public.aceites_termos') == 0
    assert scalar(conn, 'select count(*) from public.consentimentos') == 0
    assume(conn, users['ana'])
    assert scalar(conn, 'select count(*) from public.aceites_termos') == 1
    assert scalar(conn, 'select count(*) from public.consentimentos') == 1
    denied(conn, "insert into public.aceites_termos(user_id, documento, versao) values (:u, 'termos_de_uso', '2020-01-01')", {'u': users['ana']})
    denied(conn, 'update public.consentimentos set revogado_em = null')
    denied(conn, 'delete from public.aceites_termos')
    for function in ("registrar_aceite_termos(:u, 'termos_de_uso', '2026-11-10')", "registrar_consentimento(:u, 'google_agenda')",
                     "revogar_consentimento(:u, 'google_agenda')", 'exportar_dados_da_conta(:u)', 'preparar_exclusao_conta(:u)'):
        denied(conn, f'select public.{function}', {'u': users['ana']})
    for uid in (None, users['ana'], users['admin']):
        assume(conn, uid)
        denied(conn, 'select count(*) from public.exclusoes_conta')


# ---------------------------------------------------------------------------
# Exportação
# ---------------------------------------------------------------------------

def test_export_contains_the_account_data_and_nobody_elses(database):
    conn, users = database
    data = populate(conn, users)
    export = scalar(conn, 'select public.exportar_dados_da_conta(:u)', {'u': users['ana']})

    assert export['formato'] == 'agenda-unb-exportacao-v1'
    assert export['conta']['id'] == users['ana'] and export['conta']['email'].startswith('test-')
    assert {e['titulo'] for e in export['agenda_pessoal']} == {'Consulta médica', 'Prova 1'}
    assert [e['titulo'] for e in export['eventos_publicos_salvos']] == ['Palestra aberta']
    assert [e['titulo'] for e in export['eventos_enviados']] == ['Sugestão da Ana']
    assert export['turmas_seguidas'][0]['turma'] == '01'
    assert export['planos_de_ensino'][0]['arquivo_original_armazenado'] is True
    # o texto guardado do plano também é dado do titular
    assert {'texto_preparado', 'texto_aprovado', 'texto_autorizado_em'} <= set(export['planos_de_ensino'][0])
    assert export['versoes_de_planos'][0]['candidatos'][0]['titulo'] == 'Prova 1'
    assert [v['valor'] for v in export['votos']] == ['confirma']
    assert len(export['importacoes']) == 1 and export['importacoes'][0]['itens'][0]['resultado'] == 'criado'
    assert export['aceites_de_termos'][0]['documento'] == 'termos_de_uso'
    assert export['consentimentos'][0]['finalidade'] == 'google_agenda'
    assert len(export['lembretes']) >= 1 and len(export['notificacoes']) >= 1

    # nada de Bruno, nem o caminho interno do arquivo, nem o hash do texto autorizado
    raw = json.dumps(export)
    assert users['bruno'] not in raw and 'contesta' not in raw
    assert data['path'] not in raw and 'a' * 64 not in raw

    bruno = scalar(conn, 'select public.exportar_dados_da_conta(:u)', {'u': users['bruno']})
    assert 'Consulta médica' not in json.dumps(bruno) and bruno['versoes_de_planos'] == []
    refused(conn, 'P0002', 'select public.exportar_dados_da_conta(:u)', {'u': str(uuid4())})


# ---------------------------------------------------------------------------
# Exclusão de conta
# ---------------------------------------------------------------------------

LEFTOVERS = {
    'profiles': 'id', 'eventos_pessoais': 'user_id', 'eventos_salvos': 'user_id', 'eventos': 'autor_id',
    'notificacoes': 'usuario_id', 'lembretes': 'user_id', 'vinculos_turma': 'user_id', 'planos_ensino': 'user_id',
    'versoes_plano': 'autor_id', 'votos_avaliacao': 'user_id', 'operacoes_importacao': 'user_id',
    'aceites_termos': 'user_id', 'consentimentos': 'user_id',
}


def test_account_deletion_end_to_end(database):
    conn, users = database
    data = populate(conn, users)

    plan = scalar(conn, 'select public.preparar_exclusao_conta(:u)', {'u': users['ana']})
    assert plan['arquivos'] == [data['path']]                # o que a API remove do Storage
    assert plan['contagens']['agenda_pessoal'] == 2 and plan['contagens']['planos'] == 1

    # a conta tinha compromissos na agenda: antes da correção do FK esta exclusão falhava
    conn.execute(text('delete from auth.users where id=:u'), {'u': users['ana']})
    assert scalar(conn, 'select public.concluir_exclusao_conta(:r)', {'r': plan['registro_id']}) is True
    assert scalar(conn, 'select public.concluir_exclusao_conta(:r)', {'r': plan['registro_id']}) is False

    for table, column in LEFTOVERS.items():
        assert scalar(conn, f'select count(*) from public.{table} where {column}=:u', {'u': users['ana']}) == 0, table
    assert scalar(conn, 'select count(*) from public.avaliacoes where plano_id=:p', {'p': data['plan']}) == 0
    assert scalar(conn, 'select count(*) from public.votos_avaliacao where avaliacao_id=:c', {'c': data['candidate']}) == 0

    # o registro da exclusão não identifica a pessoa
    record = json.dumps(scalar(conn, 'select to_jsonb(e) from public.exclusoes_conta e where id=:r', {'r': plan['registro_id']}))
    assert users['ana'] not in record and 'test-' not in record

    # Bruno: a cópia que importou continua na agenda dele, sem vínculo com a origem apagada;
    # o evento público de outra pessoa e a turma do catálogo também continuam
    copy = conn.execute(text("""select titulo, origem_versao_id from public.eventos_pessoais where user_id=:u"""),
                        {'u': users['bruno']}).mappings().one()
    assert copy['titulo'] == 'Prova 1' and copy['origem_versao_id'] is None
    assert scalar(conn, 'select count(*) from public.eventos_salvos where user_id=:u', {'u': users['bruno']}) == 1
    assert scalar(conn, 'select count(*) from public.vinculos_turma where user_id=:u', {'u': users['bruno']}) == 1
    assert scalar(conn, 'select count(*) from public.ofertas_turma where id=:o', {'o': data['turma']}) == 1
    # a operação de importação de Bruno sobrevive, sem apontar para a versão apagada
    assert scalar(conn, 'select versao_id from public.operacoes_importacao where user_id=:u', {'u': users['bruno']}) is None


def test_last_admin_cannot_delete_the_account(database):
    conn, users = database
    conn.execute(text("update public.profiles set papel='professor' where papel='admin' and id<>:a"), {'a': users['admin']})
    refused(conn, '55000', 'select public.preparar_exclusao_conta(:u)', {'u': users['admin']})
    conn.execute(text("update public.profiles set papel='admin' where id=:p"), {'p': users['professor']})
    assert scalar(conn, 'select public.preparar_exclusao_conta(:u)', {'u': users['admin']})['arquivos'] == []
    refused(conn, 'P0002', 'select public.preparar_exclusao_conta(:u)', {'u': str(uuid4())})


# ---------------------------------------------------------------------------
# Descarte do PDF original (ADR-003)
# ---------------------------------------------------------------------------

def test_original_pdf_is_discarded_and_the_plan_remains(database):
    conn, users = database
    data = populate(conn, users)
    pending = str(uuid4())
    conn.execute(text("""insert into public.planos_ensino(id, user_id, nome_arquivo, caminho_arquivo, tipo_arquivo, status)
        values (:id, :u, 'novo.pdf', :path, 'pdf', 'pendente')"""),
        {'id': pending, 'u': users['ana'], 'path': f"syllabus_files/{users['ana']}/{pending}_novo.pdf"})

    # só planos com processamento encerrado entram na lista
    queue = conn.execute(text('select plano_id::text, caminho_arquivo from public.arquivos_a_descartar()')).all()
    assert (data['plan'], data['path']) in queue and pending not in [plan for plan, _ in queue]

    assert scalar(conn, 'select public.registrar_descarte_arquivo(:p)', {'p': data['plan']}) is True
    assert scalar(conn, 'select public.registrar_descarte_arquivo(:p)', {'p': data['plan']}) is False   # repetir é seguro
    plan = conn.execute(text("""select caminho_arquivo, tamanho_bytes, arquivo_descartado_em, nome_arquivo, status
        from public.planos_ensino where id=:p"""), {'p': data['plan']}).mappings().one()
    assert plan['caminho_arquivo'] is None and plan['tamanho_bytes'] is None and plan['arquivo_descartado_em']
    assert plan['nome_arquivo'] == 'plano.pdf' and plan['status'] == 'concluido'
    # candidatos, versão compartilhada e agenda continuam
    assert scalar(conn, 'select count(*) from public.avaliacoes where plano_id=:p', {'p': data['plan']}) == 1
    assert scalar(conn, 'select count(*) from public.eventos_pessoais where origem_plano_id=:p', {'p': data['plan']}) == 2
    assert data['plan'] not in [plan for plan, _ in conn.execute(text('select plano_id::text, caminho_arquivo from public.arquivos_a_descartar()')).all()]

    # envio novo: só o texto preparado, sem PDF; plano sem nenhuma fonte continua recusado
    conn.execute(text("""insert into public.planos_ensino(user_id, tipo_arquivo, status, texto_preparado)
        values (:u, 'pdf', 'pendente', '[{"pagina": 1, "texto": "Prova 1 em 10/04"}]')"""), {'u': users['ana']})
    denied(conn, "insert into public.planos_ensino(user_id, tipo_arquivo, status) values (:u, 'pdf', 'pendente')",
           {'u': users['ana']})
    for uid in (None, users['ana']):
        assume(conn, uid)
        denied(conn, 'select * from public.arquivos_a_descartar()')
        denied(conn, 'select public.registrar_descarte_arquivo(:p)', {'p': pending})
