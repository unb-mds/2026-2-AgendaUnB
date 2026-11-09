"""S7-D01 (#69): turmas, vínculos, versões e isolamento dos planos.

Opt-in integration tests against migrated LOCAL Supabase; every test rolls back.
Run with TEST_SUPABASE_DB_URL (never production). Exercises real PostgreSQL
constraints, triggers and RLS, which SQLite API tests cannot verify.
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
        for name in ('ana', 'bruno', 'carla'):
            uid = str(uuid4())
            conn.execute(text("insert into auth.users(id,email,raw_user_meta_data) values (:id,:email,:meta)"),
                         {'id': uid, 'email': f'test-{uid}@aluno.unb.br',
                          'meta': json.dumps({'nome_completo': 'Teste ' + name})})
            users[name] = uid
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


def count(conn, sql, params=None):
    return conn.execute(text(sql), params or {}).scalar_one()


def subject(conn, code='FGA0138', source_id=None):
    return str(conn.execute(text("""insert into public.disciplinas(origem, origem_id, codigo, nome)
        values ('followw', :source_id, :code, 'Métodos de Desenvolvimento de Software') returning id"""),
        {'source_id': source_id, 'code': code}).scalar_one())


def offering(conn, subject_id, year=2026, semester=2, number='01'):
    return str(conn.execute(text("""insert into public.ofertas_turma(disciplina_id, turma, ano, semestre)
        values (:subject, :number, :year, :semester) returning id"""),
        {'subject': subject_id, 'number': number, 'year': year, 'semester': semester}).scalar_one())


def follow(conn, user_id, offering_id):
    conn.execute(text('insert into public.vinculos_turma(user_id, oferta_id) values (:u, :o)'),
                 {'u': user_id, 'o': offering_id})


def syllabus(conn, owner, offering_id=None):
    plan_id = str(uuid4())
    conn.execute(text("""insert into public.planos_ensino(id, user_id, nome_arquivo, caminho_arquivo,
            tipo_arquivo, status, processado_em, oferta_id)
        values (:id, :owner, 'plano.pdf', :path, 'pdf', 'concluido', now(), :offering)"""),
        {'id': plan_id, 'owner': owner, 'path': f'syllabus_files/{owner}/{plan_id}_plano.pdf',
         'offering': offering_id})
    return plan_id


def candidate(conn, plan_id, order=0, version_id=None):
    return str(conn.execute(text("""insert into public.avaliacoes(plano_id, titulo, ordem, versao_id, pagina_origem, trecho_origem)
        values (:plan, 'Prova 1', :order, :version, 2, 'P1 em 10/12') returning id"""),
        {'plan': plan_id, 'order': order, 'version': version_id}).scalar_one())


def version_of(conn, plan_id, number=1):
    return str(conn.execute(text('select id from public.versoes_plano where plano_id=:p and numero=:n'),
                            {'p': plan_id, 'n': number}).scalar_one())


def test_follow_is_unique_and_semesters_stay_distinct(database):
    conn, users = database
    subject_id = subject(conn, source_id='followw-123')
    second_semester = offering(conn, subject_id, semester=2)
    first_semester = offering(conn, subject_id, semester=1)
    assert second_semester != first_semester

    follow(conn, users['ana'], second_semester)
    denied(conn, 'insert into public.vinculos_turma(user_id, oferta_id) values (:u, :o)',
           {'u': users['ana'], 'o': second_semester})
    follow(conn, users['ana'], first_semester)
    assert count(conn, 'select count(*) from public.vinculos_turma where user_id=:u', {'u': users['ana']}) == 2

    # Same offering identity cannot be registered twice, nor the same origin id.
    denied(conn, """insert into public.ofertas_turma(disciplina_id, turma, ano, semestre)
        values (:s, '01', 2026, 2)""", {'s': subject_id})
    denied(conn, """insert into public.disciplinas(origem, origem_id, codigo, nome)
        values ('followw', 'followw-123', 'OUTRO', 'Outra')""")
    # Without origin id, code identifies the subject (case-insensitive).
    subject(conn, code='CIC0004')
    denied(conn, "insert into public.disciplinas(origem, codigo, nome) values ('followw', 'cic0004', 'Repetida')")
    denied(conn, "insert into public.ofertas_turma(disciplina_id, turma, ano, semestre) values (:s, '02', 2026, 3)",
           {'s': subject_id})


def test_existing_and_new_plans_get_initial_version(database):
    conn, users = database
    plan_id = syllabus(conn, users['ana'])
    version_id = version_of(conn, plan_id)
    row = conn.execute(text('select autor_id, visibilidade, compartilhada_em from public.versoes_plano where id=:v'),
                       {'v': version_id}).one()
    assert (str(row.autor_id), row.visibilidade, row.compartilhada_em) == (users['ana'], 'privada', None)

    # Candidate without explicit version is attached to the latest version.
    candidate_id = candidate(conn, plan_id, order=0)
    assert count(conn, 'select versao_id::text from public.avaliacoes where id=:c', {'c': candidate_id}) == version_id
    # Reprocessing the same version cannot duplicate an order slot.
    denied(conn, """insert into public.avaliacoes(plano_id, titulo, ordem, versao_id)
        values (:p, 'Duplicada', 0, :v)""", {'p': plan_id, 'v': version_id})
    # A candidate cannot point to the version of another plan.
    other_version = version_of(conn, syllabus(conn, users['bruno']))
    denied(conn, "insert into public.avaliacoes(plano_id, titulo, versao_id) values (:p, 'Errada', :v)",
           {'p': plan_id, 'v': other_version})
    # Shared without a timestamp is inconsistent.
    denied(conn, "update public.versoes_plano set visibilidade='compartilhada' where id=:v", {'v': version_id})


def test_private_plan_is_isolated_by_database_and_storage(database):
    conn, users = database
    offering_id = offering(conn, subject(conn))
    follow(conn, users['ana'], offering_id)
    follow(conn, users['bruno'], offering_id)
    plan_id = syllabus(conn, users['ana'], offering_id)
    candidate(conn, plan_id)
    conn.execute(text("insert into storage.objects(bucket_id, name) values ('syllabus_files', :name)"),
                 {'name': f"{users['ana']}/{plan_id}_plano.pdf"})

    assume(conn, users['ana'])
    assert count(conn, 'select count(*) from public.planos_ensino') == 1
    assert count(conn, 'select count(*) from public.versoes_plano') == 1
    assert count(conn, 'select count(*) from public.avaliacoes') == 1
    assert count(conn, "select count(*) from storage.objects where bucket_id='syllabus_files'") == 1

    # Bruno follows the same class, but the version is private.
    assume(conn, users['bruno'])
    for table in ('public.planos_ensino', 'public.versoes_plano', 'public.avaliacoes'):
        assert count(conn, f'select count(*) from {table}') == 0
    assert count(conn, "select count(*) from storage.objects where bucket_id='syllabus_files'") == 0
    assert count(conn, 'select count(*) from public.vinculos_turma') == 1  # only his own

    assume(conn)
    for table in ('public.planos_ensino', 'public.versoes_plano', 'public.avaliacoes', 'public.vinculos_turma'):
        assert count(conn, f'select count(*) from {table}') == 0
    assert count(conn, 'select count(*) from public.ofertas_turma') >= 1  # catalog is public


def test_shared_version_reaches_followers_only_without_pdf(database):
    conn, users = database
    offering_id = offering(conn, subject(conn))
    follow(conn, users['ana'], offering_id)
    follow(conn, users['bruno'], offering_id)
    plan_id = syllabus(conn, users['ana'], offering_id)
    candidate(conn, plan_id)
    conn.execute(text("insert into storage.objects(bucket_id, name) values ('syllabus_files', :name)"),
                 {'name': f"{users['ana']}/{plan_id}_plano.pdf"})
    conn.execute(text("""update public.versoes_plano set visibilidade='compartilhada', compartilhada_em=now()
        where plano_id=:p"""), {'p': plan_id})

    assume(conn, users['bruno'])
    assert count(conn, 'select count(*) from public.versoes_plano') == 1
    assert count(conn, 'select count(*) from public.avaliacoes') == 1
    assert count(conn, 'select count(*) from public.planos_ensino') == 0  # plan row and file path stay private
    assert count(conn, "select count(*) from storage.objects where bucket_id='syllabus_files'") == 0

    assume(conn, users['carla'])  # not following the class
    assert count(conn, 'select count(*) from public.versoes_plano') == 0
    assert count(conn, 'select count(*) from public.avaliacoes') == 0

    # Withdrawing the share stops new reads.
    as_backend(conn)
    conn.execute(text("update public.versoes_plano set visibilidade='privada', compartilhada_em=null where plano_id=:p"),
                 {'p': plan_id})
    assume(conn, users['bruno'])
    assert count(conn, 'select count(*) from public.avaliacoes') == 0


def test_import_is_unique_per_user_and_candidate(database):
    conn, users = database
    plan_id = syllabus(conn, users['ana'])
    candidate_id = candidate(conn, plan_id)
    version_id = version_of(conn, plan_id)
    insert = """insert into public.eventos_pessoais(user_id, titulo, data_hora, origem_plano_id,
            origem_avaliacao_id, origem_versao_id)
        values (:u, 'Prova 1 de MDS', now(), :p, :c, :v)"""
    params = {'p': plan_id, 'c': candidate_id, 'v': version_id}
    conn.execute(text(insert), {**params, 'u': users['ana']})
    conn.execute(text(insert), {**params, 'u': users['bruno']})  # another agenda, same shared candidate
    denied(conn, insert, {**params, 'u': users['ana']})


def test_browser_cannot_write_catalog_follows_or_versions(database):
    conn, users = database
    subject_id = subject(conn)
    offering_id = offering(conn, subject_id)
    plan_id = syllabus(conn, users['ana'], offering_id)

    assume(conn, users['ana'])
    denied(conn, "insert into public.disciplinas(origem, codigo, nome) values ('manual', 'XXX0001', 'Forjada')")
    denied(conn, 'insert into public.vinculos_turma(user_id, oferta_id) values (:u, :o)',
           {'u': users['ana'], 'o': offering_id})
    denied(conn, 'insert into public.versoes_plano(plano_id, numero, autor_id) values (:p, 2, :u)',
           {'p': plan_id, 'u': users['ana']})
    # Without an UPDATE policy, sharing from the browser changes nothing.
    assert conn.execute(text("""update public.versoes_plano set visibilidade='compartilhada', compartilhada_em=now()
        where plano_id=:p"""), {'p': plan_id}).rowcount == 0
