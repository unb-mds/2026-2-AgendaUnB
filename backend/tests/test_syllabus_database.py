"""Worker, RLS e revisão S6-D02 no PostgreSQL/Supabase local migrado."""
import json
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from src.database.models import AssessmentCandidate, Syllabus
from src.modules.syllabus.processing_config import ProcessingConfig
from src.modules.syllabus.processing_task import process_document
from src.modules.syllabus.worker import SyllabusWorker
from syllabus_samples import make_pdf
from test_moderation_database import assume, database


def plan(conn, owner, *, status="concluido", execution=1):
    sid = str(uuid4())
    conn.execute(text("""insert into public.planos_ensino
      (id,user_id,tipo,nome_arquivo,caminho_arquivo,status,execucao_atual,processado_em)
      values (:id,:owner,'particular','sintetico.pdf',:path,:status,:execution,
              case when :status = 'concluido' then now() else null end)"""),
      dict(id=sid, owner=owner, path=f"syllabus_files/{owner}/{sid}.pdf", status=status, execution=execution))
    return sid


def candidate(conn, sid, *, order=0, execution=1):
    return str(conn.execute(text("""insert into public.candidatos_avaliacao
      (plano_id,execucao,ordem,titulo,tipo,pagina_origem,trecho_origem,provedor_ia,modelo_ia,versao_processamento)
      values (:plan,:execution,:order,'Prova sintetica','prova',1,'Prova sintetica: data a definir',
              'test','reference','s6d02-test') returning id"""),
      {"plan":sid,"execution":execution,"order":order}).scalar_one())


def selection(cid, **changes):
    result = {"candidato_id":cid,"acao":"confirmar","titulo":"Prova revisada",
              "data_hora":"2026-11-10T14:00:00-03:00"}
    result.update(changes)
    return result


def review(conn, sid, items):
    return conn.execute(text("select public.revisar_candidatos_plano(:plan,cast(:items as jsonb))"),
                        {"plan":sid,"items":json.dumps(items)}).scalar_one()


def reject(conn, operation, state):
    with pytest.raises(DBAPIError) as caught:
        with conn.begin_nested():
            operation()
    assert caught.value.orig.sqlstate == state


def test_syllabus_owner_only_reads_and_server_only_writes(database):
    conn, users = database
    sid = plan(conn, users["student"])
    cid = candidate(conn, sid)
    legacy = str(conn.execute(text("""insert into public.avaliacoes(plano_id,titulo,data_avaliacao)
        values (:sid,'Legada privada',now()) returning id"""), {"sid":sid}).scalar_one())
    for role in ("student", "other", "professor", "admin"):
        assume(conn, users[role])
        expected = 1 if role == "student" else 0
        for table, rid in (("planos_ensino",sid),("candidatos_avaliacao",cid),("avaliacoes",legacy)):
            assert conn.execute(text(f"select count(*) from public.{table} where id=:id"), {"id":rid}).scalar() == expected
    assume(conn, users["student"])
    for table, rid in (("planos_ensino",sid),("candidatos_avaliacao",cid),("avaliacoes",legacy)):
        reject(conn, lambda: conn.execute(text(f"delete from public.{table} where id=:id"), {"id":rid}), "42501")
    reject(conn, lambda: conn.execute(text("update public.planos_ensino set custo_reservado_usd=0 where id=:id"), {"id":sid}), "42501")
    reject(conn, lambda: conn.execute(text("update public.candidatos_avaliacao set status='confirmado' where id=:id"), {"id":cid}), "42501")
    conn.execute(text("reset role"))
    reject(conn, lambda: conn.execute(text("update public.planos_ensino set user_id=:other where id=:id"),
                                     {"id":sid,"other":users["other"]}), "42501")


def test_anonymous_and_unbound_privileged_review_are_denied(database):
    conn, users = database
    sid = plan(conn, users["student"])
    cid = candidate(conn, sid)
    conn.execute(text("select set_config('request.jwt.claim.sub','',true)"))
    reject(conn, lambda: review(conn, sid, [selection(cid)]), "42501")
    conn.execute(text("set local role anon"))
    for table in ("planos_ensino", "candidatos_avaliacao", "avaliacoes"):
        reject(conn, lambda: conn.execute(text(f"select * from public.{table}")), "42501")
    reject(conn, lambda: review(conn, sid, [selection(cid)]), "42501")
    conn.execute(text("reset role"))
    assert not conn.execute(text("select has_function_privilege('service_role', 'public.revisar_candidatos_plano(uuid,jsonb)','execute')")).scalar()


def test_private_storage_policies_and_bucket_are_preserved(database):
    conn, users = database
    bucket = conn.execute(text("select public,file_size_limit,allowed_mime_types from storage.buckets where id='syllabus_files'")).one()
    assert tuple(bucket) == (False,10485760,["application/pdf"])
    path = f"{users['student']}/{uuid4()}.pdf"
    assume(conn, users["student"])
    conn.execute(text("insert into storage.objects(bucket_id,name) values ('syllabus_files',:path)"), {"path":path})
    assert conn.execute(text("select count(*) from storage.objects where bucket_id='syllabus_files' and name=:path"), {"path":path}).scalar() == 1
    for bad_path in (f"{users['other']}/outro.pdf",f"{users['student']}/sub/p.pdf",f"{users['student']}/p.txt",f"{users['student']}/a\\p.pdf"):
        reject(conn, lambda: conn.execute(text("insert into storage.objects(bucket_id,name) values ('syllabus_files',:path)"),
                                         {"path":bad_path}), "42501")
    for role in ("other", "professor", "admin"):
        assume(conn, users[role])
        assert conn.execute(text("select count(*) from storage.objects where bucket_id='syllabus_files' and name=:path"), {"path":path}).scalar() == 0
    conn.execute(text("set local role anon"))
    assert conn.execute(text("select count(*) from storage.objects where bucket_id='syllabus_files' and name=:path"), {"path":path}).scalar() == 0


def test_review_partial_atomic_idempotent_and_deleted_event_not_recreated(database):
    conn, users = database
    sid = plan(conn, users["student"])
    first, second, third = [candidate(conn,sid,order=i) for i in range(3)]
    assume(conn, users["student"])
    items = [selection(first), {"candidato_id":second,"acao":"descartar"}]
    result = review(conn,sid,items)
    eid = result["itens"][0]["evento_pessoal_id"]
    assert eid and result["itens"][1]["evento_pessoal_id"] is None
    assert review(conn,sid,items) == result
    assert conn.execute(text("select status from public.candidatos_avaliacao where id=:id"), {"id":third}).scalar() == 'pendente'
    assert conn.execute(text("select count(*) from public.eventos_pessoais where user_id=:owner"), {"owner":users["student"]}).scalar() == 1
    event = conn.execute(text("select titulo,data_hora from public.eventos_pessoais where id=:id"), {"id":eid}).one()
    assert event[0] == 'Prova revisada' and event[1].hour == 17
    conn.execute(text("update public.eventos_pessoais set titulo='Edicao posterior' where id=:id"), {"id":eid})
    review(conn,sid,items)
    assert conn.execute(text("select titulo from public.eventos_pessoais where id=:id"), {"id":eid}).scalar() == 'Edicao posterior'
    conn.execute(text("delete from public.eventos_pessoais where id=:id"), {"id":eid})
    assert review(conn,sid,items)["itens"][0]["evento_pessoal_id"] is None
    assert conn.execute(text("select count(*) from public.eventos_pessoais where user_id=:owner"), {"owner":users["student"]}).scalar() == 0
    reject(conn, lambda: review(conn,sid,[selection(second)]), "22023")


def test_review_cross_owner_cross_plan_and_old_execution_roll_back(database):
    conn, users = database
    sid = plan(conn,users["student"])
    first = candidate(conn,sid)
    other_plan = plan(conn,users["other"])
    other_candidate = candidate(conn,other_plan)
    own_second_plan = plan(conn,users["student"],execution=2)
    old = candidate(conn,own_second_plan,execution=1)
    assume(conn,users["other"])
    reject(conn,lambda:review(conn,sid,[selection(first)]),"P0002")
    assume(conn,users["student"])
    reject(conn,lambda:review(conn,sid,[selection(first),selection(other_candidate)]),"P0002")
    reject(conn,lambda:review(conn,sid,[selection(old)]),"P0002")
    reject(conn,lambda:review(conn,own_second_plan,[selection(old)]),"P0002")
    assert conn.execute(text("select status from public.candidatos_avaliacao where id=:id"), {"id":first}).scalar() == 'pendente'
    assert conn.execute(text("select count(*) from public.eventos_pessoais where user_id=:owner"), {"owner":users["student"]}).scalar() == 0


@pytest.mark.parametrize("kind", ["duplicate","bad_uuid","extra","no_offset","invalid_date","short_title","empty","not_array","null","foreign_owner_field"])
def test_invalid_review_never_writes_partial_events(database, kind):
    conn, users = database
    sid = plan(conn,users["student"])
    cid = candidate(conn,sid)
    good = selection(cid)
    values = {
        'duplicate':[good,good], 'bad_uuid':[selection('not-uuid')],
        'extra':[selection(cid,unexpected=True)], 'no_offset':[selection(cid,data_hora='2026-11-10T14:00:00')],
        'invalid_date':[selection(cid,data_hora='2026-02-30T14:00:00-03:00')],
        'short_title':[selection(cid,titulo='P')], 'empty':[], 'not_array':{}, 'null':None,
        'foreign_owner_field':[selection(cid,user_id=users['other'])],
    }
    assume(conn,users["student"])
    reject(conn,lambda:review(conn,sid,values[kind]),"22023")
    assert conn.execute(text("select count(*) from public.eventos_pessoais where user_id=:owner"), {"owner":users["student"]}).scalar() == 0


def test_review_requires_completed_plan_and_matching_event_owner(database):
    conn, users = database
    sid = plan(conn,users["student"],status='pendente')
    cid = candidate(conn,sid)
    eid = conn.execute(text("insert into public.eventos_pessoais(user_id,titulo,data_hora) values (:owner,'Outro dono',now()) returning id"), {"owner":users['other']}).scalar_one()
    reject(conn,lambda:conn.execute(text("update public.candidatos_avaliacao set status='confirmado',revisado_em=now(),evento_pessoal_id=:event where id=:id"), {"event":eid,"id":cid}),"42501")
    assume(conn,users["student"])
    reject(conn,lambda:review(conn,sid,[selection(cid)]),"22023")


@pytest.fixture
def committed_plan():
    url = os.getenv('TEST_SUPABASE_DB_URL')
    if not url:
        pytest.skip('TEST_SUPABASE_DB_URL not configured')
    assert make_url(url).host in ('localhost','127.0.0.1'), 'Local database only'
    engine = create_engine(url)
    owner = str(uuid4())
    with engine.begin() as conn:
        conn.execute(text("insert into auth.users(id,email,raw_user_meta_data) values (:id,:email,:meta)"),
                     {'id':owner,'email':f's6d02-{owner}@example.com','meta':json.dumps({'nome_completo':'Teste concorrente sintetico'})})
        sid = plan(conn,owner)
        cid = candidate(conn,sid)
    try:
        yield engine,owner,sid,cid
    finally:
        with engine.begin() as conn:
            conn.execute(text('delete from public.planos_ensino where user_id=:id'),{'id':owner})
            conn.execute(text('delete from public.eventos_pessoais where user_id=:id'),{'id':owner})
            conn.execute(text('delete from auth.users where id=:id'),{'id':owner})
        engine.dispose()


def test_concurrent_confirmation_returns_one_event(committed_plan):
    engine,owner,sid,cid = committed_plan
    barrier = Barrier(2)
    def confirm():
        with engine.begin() as conn:
            conn.execute(text("set local statement_timeout='10s'"))
            assume(conn,owner)
            barrier.wait(timeout=5)
            return review(conn,sid,[selection(cid)])["itens"][0]["evento_pessoal_id"]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _:confirm(),range(2)))
    assert results[0] == results[1] and results[0] is not None
    with engine.connect() as conn:
        assert conn.execute(text('select count(*) from public.eventos_pessoais where user_id=:id'),{'id':owner}).scalar() == 1


def test_worker_postgres_constraints_and_candidate_array(database):
    connection, users = database
    sessions = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    sid = uuid4()
    owner = UUID(users["student"])
    with sessions() as db:
        db.add(Syllabus(id=sid, user_id=owner, file_name="sintetico.pdf",
                        file_path=f"syllabus_files/{owner}/{sid}.pdf"))
        db.commit()

    class Storage:
        def download_file(self, path):
            return make_pdf(["Prova sintetica - data a definir."])

    class Provider:
        def extract(self, pages):
            return json.dumps({"candidatos": [{"titulo": "Prova sintetica", "tipo": "prova",
                "data_sugerida": None, "hora_sugerida": None, "campos_ambiguos": ["data"],
                "pagina_origem": 1, "trecho_origem": "Prova sintetica - data a definir."}]})

    worker = SyllabusWorker(sessions, Storage(), Provider(), ProcessingConfig(), runner=process_document)
    assert worker.run_once()
    with sessions() as db:
        plan = db.get(Syllabus, sid)
        assert plan.status == "concluido" and plan.extracted_events_count == 1
        candidate = db.scalar(select(AssessmentCandidate).where(AssessmentCandidate.plano_id == sid))
        assert candidate.campos_ambiguos == ["data"]
        assert candidate.evento_pessoal_id is None and candidate.status == "pendente"
