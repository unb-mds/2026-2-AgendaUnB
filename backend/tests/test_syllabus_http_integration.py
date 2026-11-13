"""Auth/Storage/PostgREST reais; FastAPI via ASGI e PostgreSQL local, sem dados reais."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from src.database.connection import get_db
from src.database.models import AssessmentCandidate, PersonalEvent, Syllabus, CatalogSync, ClassOffering, Subject
from src.main import app
from src.middlewares.auth import get_current_user
from src.modules.syllabus.gemini import GeminiProvider
from src.modules.syllabus.processing_config import ProcessingConfig
from src.modules.syllabus.privacy import privacy_checks
from src.modules.syllabus.worker import SyllabusWorker
from src.services.storage import SupabaseStorageService, get_storage_service
from syllabus_samples import make_pdf


@dataclass(repr=False)
class LocalHTTP:
    url: str
    anon_key: str
    service_key: str
    sessions: object
    users: dict = field(default_factory=dict)
    tokens: dict = field(default_factory=dict)
    paths: list = field(default_factory=list)
    result: dict | None = None
    offering_id: str | None = None

    def headers(self, role=None, *, service=False):
        return {"apikey":self.service_key if service else self.anon_key,
                "Authorization":"Bearer " + (self.service_key if service else self.tokens.get(role,self.anon_key))}


@pytest.fixture
def local_http(monkeypatch):
    url = os.getenv("TEST_LOCAL_SUPABASE_URL")
    anon = os.getenv("TEST_LOCAL_SUPABASE_ANON_KEY")
    service = os.getenv("TEST_LOCAL_SUPABASE_SERVICE_ROLE_KEY")
    db_url = os.getenv("TEST_SUPABASE_DB_URL")
    if not all((url,anon,service,db_url)):
        pytest.skip("Integração HTTP local opt-in: use scripts/test_syllabus_local_http.py")
    assert urlsplit(url).hostname in ("127.0.0.1","localhost"), "Apenas Auth/Storage locais"
    assert make_url(db_url).host in ("127.0.0.1","localhost"), "Apenas PostgreSQL local"
    engine = create_engine(db_url)
    sessions = sessionmaker(bind=engine)
    ctx = LocalHTTP(url.rstrip("/"),anon,service,sessions)
    storage = SupabaseStorageService(supabase_url=ctx.url,supabase_key=service)
    overrides = app.dependency_overrides.copy()
    created = []
    seeded_subject = seeded_run = None
    try:
        with engine.connect() as connection:
            assert all(privacy_checks(connection).values()), "Privacidade local ainda não validada"
        # Admin create + email_confirm não envia mensagens/e-mails.
        for role in ("owner","other","professor","admin"):
            email = f"e2e-{uuid4()}@unb.br"
            password = secrets.token_urlsafe(24)
            response = httpx.post(ctx.url+"/auth/v1/admin/users",headers=ctx.headers(service=True),
                json={"email":email,"password":password,"email_confirm":True,
                      "user_metadata":{"nome_completo":"Usuario sintetico HTTP"}},timeout=15)
            assert response.status_code in (200,201), "Falha ao criar conta sintética local"
            uid = response.json().get("id")
            if not uid:
                pytest.fail("Auth local não retornou ID da conta sintética")
            created.append(uid)
            ctx.users[role] = uid
            if role in ("professor","admin"):
                with engine.begin() as connection:
                    connection.execute(text("update public.profiles set papel=:role where id=:id"),{"role":role,"id":uid})
            login = httpx.post(ctx.url+"/auth/v1/token?grant_type=password",headers={"apikey":anon},
                              json={"email":email,"password":password},timeout=15)
            assert login.status_code == 200, "Falha no login HTTP da conta sintética"
            token = login.json().get("access_token")
            if not isinstance(token,str) or not token:
                pytest.fail("Auth local não retornou sessão")
            ctx.tokens[role] = token
        with sessions() as session:
            run = session.scalar(select(CatalogSync).where(CatalogSync.status == "concluida").order_by(CatalogSync.completed_at.desc()).limit(1))
            if run is None:
                run = CatalogSync(status="concluida", completed_at=datetime.now(timezone.utc))
                session.add(run); session.flush(); seeded_run = run.id
            subject = Subject(code="HTTP" + uuid4().hex[:12].upper(), name="Oferta sintética HTTP", unit="673")
            session.add(subject); session.flush(); seeded_subject = subject.id
            offer = ClassOffering(subject_id=subject.id, class_number="01", year=2026, semester=2, publication_id=run.id)
            session.add(offer); session.flush()
            from src.database.models import ClassFollow
            session.add(ClassFollow(user_id=UUID(ctx.users["owner"]), offering_id=offer.id))
            session.commit(); ctx.offering_id = str(offer.id)
        monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY","true")
        monkeypatch.setenv("SUPABASE_URL",ctx.url)
        monkeypatch.setenv("SUPABASE_ANON_KEY",anon)
        def database():
            with sessions() as session:
                yield session
        app.dependency_overrides[get_db] = database
        app.dependency_overrides[get_storage_service] = lambda:storage
        assert get_current_user not in app.dependency_overrides, "Autenticação precisa ser real"
        with TestClient(app) as client:
            yield ctx,client,storage
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides)
        # Remover objetos pelos endpoints do Storage, nunca apenas seus metadados.
        if ctx.paths:
            result = httpx.request("DELETE",ctx.url+"/storage/v1/object/syllabus_files",headers=ctx.headers(service=True),
                                   json={"prefixes":ctx.paths},timeout=15)
            assert result.status_code == 200, "Falha na limpeza dos objetos sintéticos"
        for uid in created:
            with engine.begin() as connection:
                connection.execute(text("delete from public.planos_ensino where user_id=:id"),{"id":uid})
                connection.execute(text("delete from public.eventos_pessoais where user_id=:id"),{"id":uid})
            result = httpx.delete(ctx.url+"/auth/v1/admin/users/"+uid,headers=ctx.headers(service=True),timeout=15)
            assert result.status_code == 200, "Falha na limpeza da conta sintética"
        with engine.begin() as connection:
            if ctx.offering_id:
                connection.execute(text("delete from public.ofertas_turma where id=:id"), {"id": ctx.offering_id})
            if seeded_subject:
                connection.execute(text("delete from public.disciplinas where id=:id"), {"id": seeded_subject})
            if seeded_run:
                connection.execute(text("delete from public.sincronizacoes_catalogo where id=:id"), {"id": seeded_run})
        engine.dispose()
        report_path = os.getenv("TEST_SYLLABUS_HTTP_REPORT")
        if ctx.result is not None and report_path:
            report_path = Path(report_path)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            report["results"].append(ctx.result)
            report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


class ReferenceProvider:
    def extract(self,pages):
        return json.dumps({"candidatos":[{
            "titulo":"Prova de integracao","tipo":"prova","data_sugerida":"2026-11-10","hora_sugerida":"14:00",
            "campos_ambiguos":[],"pagina_origem":1,"trecho_origem":"Prova de integracao - 10/11/2026 - 14:00."
        },{
            "titulo":"Trabalho de integracao","tipo":"trabalho","data_sugerida":"2026-11-24","hora_sugerida":None,
            "campos_ambiguos":[],"pagina_origem":1,"trecho_origem":"Trabalho de integracao - 24/11/2026."
        }]})


@pytest.mark.parametrize("provider_kind",["reference",pytest.param("gemini",marks=pytest.mark.skipif(
    os.getenv("TEST_GEMINI_LIVE") != "true",reason="Gemini real exige --gemini-live"))])
def test_authenticated_upload_private_download_processing_and_review(local_http,provider_kind):
    if provider_kind == "gemini" and os.getenv("TEST_GEMINI_LIVE") != "true":
        pytest.skip("Gemini real exige --gemini-live")
    ctx,client,storage = local_http
    config = ProcessingConfig.from_env()
    if provider_kind == "gemini" and not config.api_key:
        pytest.fail("GEMINI_API_KEY ausente; nenhuma leitura do registro do Windows é feita")
    pdf = make_pdf(["Plano inteiramente sintetico\nCronograma\nProva de integracao - 10/11/2026 - 14:00.\nTrabalho de integracao - 24/11/2026."])
    started = time.monotonic()
    response = client.post("/api/v1/syllabus/upload",headers=ctx.headers("owner"),
                           files={"file":("integracao.pdf",pdf,"application/pdf")}, data={"offering_id": ctx.offering_id})
    upload_ms = round((time.monotonic()-started)*1000)
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "pendente" and body["userId"] == ctx.users["owner"]
    sid = body["id"]
    assert body["filePath"] is None and body["authorizationRequired"]
    preview = client.get(f"/api/v1/syllabus/{sid}/text", headers=ctx.headers("owner"))
    assert preview.status_code == 200
    assert preview.headers["cache-control"] == "no-store"
    for role in ("other","professor","admin",None):
        for suffix in ("", "/text"):
            hidden = client.get(f"/api/v1/syllabus/{sid}{suffix}",headers=ctx.headers(role))
            assert hidden.status_code == (401 if role is None else 404)
    with ctx.sessions() as session:
        assert session.execute(text("select count(*) from storage.objects where bucket_id='syllabus_files'")).scalar() == 0
    # Snapshot sintético conhecido: autorização explícita após conferir o conteúdo.
    preview = preview.json()
    authorized = client.post(f"/api/v1/syllabus/{sid}/extractions",headers=ctx.headers("owner"), json={
        "pages":preview["pages"],"textHash":preview["textHash"],"authorize":True,"contentEligible":True})
    assert authorized.status_code == 202
    queue_started = time.monotonic()
    provider = GeminiProvider(config) if provider_kind == "gemini" else ReferenceProvider()
    worker = SyllabusWorker(ctx.sessions,None,provider,config)
    for _ in range(config.max_attempts):
        worker.run_once()
        with ctx.sessions() as session:
            status = session.scalar(select(Syllabus.status).where(Syllabus.id == sid))
        if status in ("concluido","falha"):
            break
        time.sleep(config.retry_delay_seconds)
    status = client.get(f"/api/v1/syllabus/{sid}",headers=ctx.headers("owner"))
    assert status.status_code == 200 and status.json()["status"] == "concluido"
    assert status.json()["extractedEventsCount"] == 2
    upload_to_candidates_ms = round((time.monotonic()-started)*1000)
    total_processing_ms = status.json()["totalDurationMs"]
    attempt_ms = status.json()["processingDurationMs"]
    with ctx.sessions() as session:
        assert not session.scalars(select(PersonalEvent).where(PersonalEvent.user_id == ctx.users["owner"])).all()
    candidates_url = ctx.url+"/rest/v1/avaliacoes"
    params = {"plano_id":"eq."+sid,"select":"id,titulo,status,versao_id","order":"ordem"}
    own = httpx.get(candidates_url,params=params,headers=ctx.headers("owner"),timeout=15)
    assert own.status_code == 200 and len(own.json()) == 2
    for role in ("other","professor","admin"):
        hidden = httpx.get(candidates_url,params=params,headers=ctx.headers(role),timeout=15)
        assert hidden.status_code == 200 and hidden.json() == []
    first,second = own.json()
    payload = {"p_plano_id":sid,"p_itens":[
        {"candidato_id":first["id"],"acao":"confirmar","titulo":"Prova revisada HTTP","data_hora":"2026-11-10T14:00:00-03:00"},
        {"candidato_id":second["id"],"acao":"descartar"}]}
    rpc = ctx.url+"/rest/v1/rpc/revisar_candidatos_plano"
    confirmed = httpx.post(rpc,json=payload,headers=ctx.headers("owner"),timeout=15)
    assert confirmed.status_code == 200
    repeated = httpx.post(rpc,json=payload,headers=ctx.headers("owner"),timeout=15)
    assert repeated.status_code == 200 and repeated.json() == confirmed.json()
    with ctx.sessions() as session:
        events = session.scalars(select(PersonalEvent).where(PersonalEvent.user_id == ctx.users["owner"])).all()
        assert len(events) == 1 and events[0].title == "Prova revisada HTTP"
    # Somente métricas; nenhum token, corpo do PDF ou retorno bruto da IA.
    ctx.result = {"case":"upload_processing_review","provider":provider_kind,
                  "flow_total_seconds":round(time.monotonic()-started,3),
                  "upload_duration_ms":upload_ms,"upload_to_candidates_ms":upload_to_candidates_ms,
                  "upload_to_candidates_under_20s":upload_to_candidates_ms < 20000,
                  "processing_total_ms":total_processing_ms,"last_attempt_ms":attempt_ms,
                  "processing_under_20s":total_processing_ms < 20000,
                  "candidates":2,"events_before_review":0,"events_after_review":1,
                  "pdf_persisted":False,"cross_user_text_denied":True,
                  "processing_wall_ms":round((time.monotonic()-queue_started)*1000),
                  "human_review_seconds":0,"cleanup_completed":True}


def test_storage_http_rejects_foreign_upload_and_invalid_mime(local_http):
    ctx,_,_ = local_http
    pdf = make_pdf(["Documento sintetico sem cronograma."])
    bad_paths = [f"{ctx.users['owner']}/{uuid4()}.pdf",f"{ctx.users['other']}/sub/{uuid4()}.pdf"]
    for path in bad_paths:
        ctx.paths.append(path)
        response = httpx.post(ctx.url+"/storage/v1/object/syllabus_files/"+path,
                             headers={**ctx.headers("other"),"Content-Type":"application/pdf"},content=pdf,timeout=15)
        assert response.status_code in (400,401,403)
    own_path = f"{ctx.users['owner']}/{uuid4()}.pdf"
    ctx.paths.append(own_path)
    own_upload = httpx.post(ctx.url+"/storage/v1/object/syllabus_files/"+own_path,
        headers={**ctx.headers("owner"),"Content-Type":"application/pdf"},content=pdf,timeout=15)
    assert own_upload.status_code in (400,401,403)
    path = f"{ctx.users['owner']}/{uuid4()}.pdf"
    ctx.paths.append(path)
    response = httpx.post(ctx.url+"/storage/v1/object/syllabus_files/"+path,
                         headers={**ctx.headers("owner"),"Content-Type":"text/plain"},content=b"not a pdf",timeout=15)
    assert response.status_code == 400
    ctx.result = {"case":"storage_constraints","foreign_folder_upload_denied":True,
                  "nested_folder_upload_denied":True,"own_pdf_retention_denied":True,"invalid_mime_denied":True,"cleanup_completed":True}
