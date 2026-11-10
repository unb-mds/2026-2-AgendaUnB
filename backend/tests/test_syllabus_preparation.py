import hashlib
import io
import json
from dataclasses import replace
from uuid import UUID

import pytest
from sqlalchemy import select

from src.database.models import AssessmentCandidate, PersonalEvent, Profile, Syllabus
from src.modules.syllabus.processing_config import ProcessingConfig
from src.modules.syllabus.processing_task import process_document
from src.modules.syllabus.worker import SyllabusWorker
from syllabus_samples import make_pdf


TEXT = "Prova 1 - 10/11/2026 - 14:00."


def prepare(api, text=TEXT):
    client, sessions, auth, _ = api
    with sessions() as db:
        if not db.get(Profile, auth["value"].id):
            db.add(Profile(id=auth["value"].id, papel="student"))
            db.commit()
    response = client.post("/api/v1/syllabus/text", json={"text": text})
    assert response.status_code == 202
    sid = response.json()["id"]
    preview = client.get(f"/api/v1/syllabus/{sid}/text")
    assert preview.status_code == 200
    return sid, preview.json()


def approval(preview, **changes):
    body = {"pages": preview["pages"], "textHash": preview["textHash"],
            "authorize": True, "contentEligible": True, "reprocess": False}
    body.update(changes)
    return body


def test_raw_text_prepares_without_queueing_or_persisting_pdf(api):
    sid, preview = prepare(api, "Professor: Pessoa Exemplo\nEmail: pessoa@example.test\nMatricula: 123456789\n" + TEXT)
    assert "Pessoa Exemplo" not in json.dumps(preview)
    assert "pessoa@example.test" not in json.dumps(preview)
    assert "123456789" not in json.dumps(preview)
    assert preview["pages"][0]["pagina"] is None
    assert preview["authorizationRequired"] is True
    with api[1]() as db:
        plan = db.get(Syllabus, UUID(sid))
        assert plan.file_path is None and plan.approved_pages is None
        assert plan.authorized_at is None
    worker = SyllabusWorker(api[1], None, None, ProcessingConfig(), runner=process_document)
    assert worker.claim() is None


def test_pdf_prepares_page_references_without_using_storage(api):
    client, sessions, auth, _ = api
    with sessions() as db:
        db.add(Profile(id=auth["value"].id, papel="student"))
        db.commit()
    response = client.post("/api/v1/syllabus/upload", files={
        "file": ("sintetico.pdf", make_pdf([TEXT, "Trabalho final - data a definir."]), "application/pdf")})
    assert response.status_code == 202
    assert response.json()["filePath"] is None
    preview = client.get(f"/api/v1/syllabus/{response.json()['id']}/text").json()
    assert [page["pagina"] for page in preview["pages"]] == [1, 2]
    with sessions() as db:
        assert db.get(Syllabus, UUID(response.json()["id"])).file_path is None


@pytest.mark.parametrize("changes,status", [
    ({"authorize": False}, 422), ({"contentEligible": False}, 422),
    ({"textHash": "0" * 64}, 409),
    ({"pages": [{"pagina": 8, "texto": TEXT}]}, 422),
])
def test_approval_requires_exact_text_consent_and_valid_source(api, monkeypatch, changes, status):
    monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY", "true")
    sid, preview = prepare(api)
    response = api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=approval(preview, **changes))
    assert response.status_code == status
    with api[1]() as db:
        assert db.get(Syllabus, UUID(sid)).authorized_at is None


def test_terms_gate_blocks_approval(api, monkeypatch):
    monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY", "false")
    sid, preview = prepare(api)
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=approval(preview)).status_code == 503


def test_approved_text_is_exact_private_and_idempotent(api, monkeypatch):
    monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY", "true")
    sid, preview = prepare(api)
    received = []
    class Provider:
        def extract(self, pages):
            received.extend(pages)
            return json.dumps({"candidatos": [{"titulo": "Prova 1", "tipo": "prova",
                "data_sugerida": "2026-11-10", "hora_sugerida": "14:00",
                "pagina_origem": None, "trecho_origem": TEXT}]})
    payload = approval(preview)
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=payload).status_code == 202
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=payload).status_code == 202
    worker = SyllabusWorker(api[1], None, Provider(), ProcessingConfig(), runner=process_document)
    assert worker.run_once() and not worker.run_once()
    assert received[0].texto == TEXT and received[0].pagina is None
    with api[1]() as db:
        assert len(db.scalars(select(AssessmentCandidate)).all()) == 1
        assert not db.scalars(select(PersonalEvent)).all()
        assert db.get(Syllabus, UUID(sid)).text_revision == 1
    # Repetir uma autorização concluída não dispara outra execução.
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=payload).status_code == 202
    assert not worker.run_once()
    # Reprocessamento explícito descarta candidatos pendentes da versão anterior.
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=approval(preview, reprocess=True)).status_code == 202
    assert worker.run_once()
    with api[1]() as db:
        candidates = db.scalars(select(AssessmentCandidate)).all()
        assert len([row for row in candidates if row.status == "pendente"]) == 1
        assert len([row for row in candidates if row.status == "descartado"]) == 1


def test_other_user_cannot_read_or_approve_text(api, monkeypatch):
    from src.middlewares.auth import CurrentUser
    from uuid import uuid4
    sid, preview = prepare(api)
    api[2]["value"] = CurrentUser(id=uuid4(), role="student")
    assert api[0].get(f"/api/v1/syllabus/{sid}/text").status_code == 404
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=approval(preview)).status_code == 404


def test_raw_text_utf8_limit(api):
    assert api[0].post("/api/v1/syllabus/text", json={"text": "é" * 20001}).status_code == 413


def test_text_preview_is_not_cacheable(api):
    sid, _ = prepare(api)
    assert api[0].get(f"/api/v1/syllabus/{sid}/text").headers["cache-control"] == "no-store"


@pytest.mark.parametrize("text", ["invalid\x00text", " ", "\n\t"])
def test_invalid_or_blank_text_is_rejected(api, text):
    assert api[0].post("/api/v1/syllabus/text", json={"text": text}).status_code == 422


def test_pdf_temporary_is_closed_before_text_is_persisted(api, monkeypatch):
    from starlette.datastructures import UploadFile
    import src.modules.syllabus.router as router
    original_close = UploadFile.close
    original_register = router.process_syllabus_upload
    closed = []
    async def close(file):
        await original_close(file)
        closed.append(file.file.closed)
    def register(**kwargs):
        assert closed and all(closed)
        assert "content" not in kwargs
        return original_register(**kwargs)
    monkeypatch.setattr(UploadFile, "close", close)
    monkeypatch.setattr(router, "process_syllabus_upload", register)
    response = api[0].post("/api/v1/syllabus/upload", files={
        "file": ("sintetico.pdf", make_pdf([TEXT]), "application/pdf")})
    assert response.status_code == 202
    assert closed and all(closed)


def test_human_review_wait_does_not_consume_processing_sla(api, monkeypatch):
    from datetime import datetime, timedelta, timezone
    monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY", "true")
    sid, preview = prepare(api)
    with api[1]() as db:
        db.get(Syllabus, UUID(sid)).created_at = datetime.now(timezone.utc)-timedelta(hours=2)
        db.commit()
    api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=approval(preview))
    class EmptyProvider:
        def extract(self, pages):
            return '{"candidatos": []}'
    worker = SyllabusWorker(api[1], None, EmptyProvider(), ProcessingConfig(), runner=process_document)
    assert worker.run_once()
    result = api[0].get(f"/api/v1/syllabus/{sid}").json()
    assert result["totalDurationMs"] < 20000
    assert result["reviewDurationMs"] >= 7_199_000


def test_provider_requires_terms_gate_before_http(monkeypatch):
    import httpx
    from src.modules.syllabus.gemini import GeminiProvider
    from src.modules.syllabus.extraction import TextPage
    from src.modules.syllabus.processing_config import ProcessingError
    def unexpected(*args, **kwargs):
        pytest.fail("Não pode chamar HTTP antes da liberação S7-B02")
    monkeypatch.setattr(httpx.Client, "stream", unexpected)
    with pytest.raises(ProcessingError):
        GeminiProvider(ProcessingConfig(api_key="synthetic-key")).extract([TextPage(None, TEXT)])


@pytest.mark.parametrize("title", ["Aula sobre prova", "Bibliografia de prova", "Leitura para trabalho"])
def test_classes_and_bibliography_do_not_become_candidates(title):
    from src.modules.syllabus.extraction import TextPage, validate_candidates
    text = title + " - 10/11/2026."
    kind = "trabalho" if "trabalho" in title else "prova"
    result = validate_candidates(json.dumps({"candidatos": [{"titulo": title, "tipo": kind,
        "pagina_origem": None, "trecho_origem": text}]}), [TextPage(None, text)])
    assert result.candidates == []


def test_other_assessment_types_are_rejected():
    from src.modules.syllabus.extraction import TextPage, validate_candidates
    from src.modules.syllabus.processing_config import ProcessingError
    with pytest.raises(ProcessingError):
        validate_candidates(json.dumps({"candidatos": [{"titulo": "Seminario", "tipo": "seminario",
            "pagina_origem": None, "trecho_origem": "Seminario"}]}), [TextPage(None, "Seminario")])


def test_snapshot_hash_is_stable_after_jsonb_reorders_keys():
    from src.modules.syllabus.preparation import text_hash
    assert text_hash([{"pagina":1,"texto":TEXT}]) == text_hash([{"texto":TEXT,"pagina":1}])


@pytest.mark.parametrize("failure_stage", ["validation", "extraction"])
def test_preparation_failure_closes_pdf_and_leaves_no_job(api, monkeypatch, failure_stage):
    from fastapi import HTTPException
    from starlette.datastructures import UploadFile
    from src.modules.syllabus import services
    import src.modules.syllabus.router as router
    original_close = UploadFile.close
    closed = []
    async def close(file):
        await original_close(file)
        closed.append(file.file.closed)
    def unavailable(*args):
        raise HTTPException(422, "Preparação indisponível; use a organização manual.")
    monkeypatch.setattr(UploadFile, "close", close)
    if failure_stage == "validation":
        monkeypatch.setattr(services, "validate_pdf_structure", unavailable)
    else:
        monkeypatch.setattr(router, "extract_pdf_isolated", unavailable)
    response = api[0].post("/api/v1/syllabus/upload", files={
        "file": ("sintetico.pdf", make_pdf([TEXT]), "application/pdf")})
    assert response.status_code == 422
    assert closed and all(closed)
    with api[1]() as db:
        assert db.scalar(select(Syllabus)) is None


def test_approval_keeps_only_the_students_corrected_text(api, monkeypatch):
    from src.modules.syllabus.preparation import text_hash
    monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY", "true")
    sid, preview = prepare(api, "NomeSemRotulo Exemplo\n" + TEXT)
    pages = [{"pagina":None,"texto":TEXT}]
    response = api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=approval(preview,pages=pages,textHash=text_hash(pages)))
    assert response.status_code == 202
    with api[1]() as db:
        plan = db.get(Syllabus,UUID(sid))
        assert plan.prepared_pages == plan.approved_pages == pages


def test_reprocessing_preserves_shared_version_and_pins_private_output(api, monkeypatch):
    from datetime import datetime, timezone
    from src.database.models import SyllabusVersion
    monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY", "true")
    sid, preview = prepare(api)
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=approval(preview)).status_code == 202
    class Provider:
        def extract(self, pages):
            return json.dumps({"candidatos": [{"titulo": "Prova 1", "tipo": "prova",
                "data_sugerida": "2026-11-10", "hora_sugerida": "14:00",
                "pagina_origem": None, "trecho_origem": TEXT}]})
    worker = SyllabusWorker(api[1], None, Provider(), ProcessingConfig(), runner=process_document)
    assert worker.run_once()
    with api[1]() as db:
        plan = db.get(Syllabus, UUID(sid))
        first_version = plan.approved_version_id
        version = db.get(SyllabusVersion, first_version)
        version.visibility = "compartilhada"
        version.shared_at = datetime.now(timezone.utc)
        db.commit()
    payload = approval(preview, reprocess=True)
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=payload).status_code == 202
    assert worker.run_once()
    with api[1]() as db:
        plan = db.get(Syllabus, UUID(sid))
        assert plan.approved_version_id != first_version
        assert db.get(SyllabusVersion, plan.approved_version_id).visibility == "privada"
        candidates = db.scalars(select(AssessmentCandidate)).all()
        assert len(candidates) == 2 and all(row.status == "pendente" for row in candidates)
        assert len({row.version_id for row in candidates}) == 2
    response = api[0].get(f"/api/v1/syllabus/{sid}").json()
    assert len(response["candidates"]) == 1
    candidate = response["candidates"][0]
    assert candidate["suggestedDate"] == "2026-11-10" and candidate["suggestedTime"] == "14:00:00"
    assert candidate["startsAt"] is None  # Nenhum fuso ou instante é inferido.
