"""Consentimento e texto privado no PostgreSQL LOCAL isolado, nunca produção."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from src.database.models import Syllabus
from src.modules.syllabus.preparation import ExtractionAuthorization, authorize, owned_plan, text_hash
from src.modules.syllabus.processing_config import ProcessingConfig
from test_moderation_database import assume, database
from test_syllabus_database import committed_plan, plan, reject


def test_prepared_and_approved_text_are_owner_only(database):
    conn, users = database
    sid = plan(conn, users["student"])
    for role in ("student", "other", "professor", "admin"):
        assume(conn, users[role])
        rows = conn.execute(text("select texto_preparado,texto_aprovado from public.planos_ensino where id=:sid"), {"sid":sid}).all()
        assert len(rows) == (1 if role == "student" else 0)
        reject(conn, lambda: conn.execute(text("update public.planos_ensino set texto_aprovado='[]' where id=:sid"), {"sid":sid}), "42501")


def test_processing_snapshot_is_immutable_even_for_backend(database):
    conn, users = database
    sid = plan(conn, users["student"], status="pendente")
    conn.execute(text("update public.planos_ensino set status='processando',processamento_iniciado_em=now() where id=:sid"), {"sid":sid})
    reject(conn, lambda: conn.execute(text("update public.planos_ensino set texto_aprovado='[]' where id=:sid"), {"sid":sid}), "42501")


def test_concurrent_authorization_is_idempotent(committed_plan):
    engine, owner, _, _ = committed_plan
    sid = uuid4()
    pages = [{"pagina":None,"texto":"Prova sintetica - data a definir."}]
    sessions = sessionmaker(bind=engine)
    with sessions() as db:
        db.add(Syllabus(id=sid,user_id=UUID(owner),file_name="texto.txt",file_type="text",prepared_pages=pages))
        db.commit()
    body = ExtractionAuthorization.model_validate({"pages":pages,"textHash":text_hash(pages),"authorize":True,"contentEligible":True})
    barrier = Barrier(2)
    def approve(_):
        barrier.wait(timeout=5)
        with sessions() as db:
            record = owned_plan(db, UUID(owner), sid, lock=True)
            return authorize(db,record,body,ProcessingConfig(provider_terms_ready=True)).text_revision
    with ThreadPoolExecutor(max_workers=2) as pool:
        revisions = list(pool.map(approve,range(2)))
    assert revisions == [1,1]
    with sessions() as db:
        record=db.get(Syllabus,sid)
        assert record.text_revision == 1 and record.execucao_atual == 0
        assert record.approved_pages == pages
