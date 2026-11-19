import hashlib
import io
import json
from dataclasses import replace
from uuid import UUID

import pytest

pytestmark = pytest.mark.usefixtures("published_offering")
from sqlalchemy import select

from src.database.models import AssessmentCandidate, PersonalEvent, Profile, Syllabus
from src.modules.syllabus.extraction import TextPage, validate_candidates
from src.modules.syllabus.preparation import minimize, text_hash
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
    response = client.post("/api/v1/syllabus/text", json={**({"text": text}), "offering_id": "70000000-0000-4000-8000-000000000071"})
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
    response = client.post("/api/v1/syllabus/upload", data={"offering_id": "70000000-0000-4000-8000-000000000071"}, files={
        "file": ("sintetico.pdf", make_pdf([TEXT, "Trabalho final - data a definir."]), "application/pdf")})
    assert response.status_code == 202
    assert response.json()["filePath"] is None
    preview = client.get(f"/api/v1/syllabus/{response.json()['id']}/text").json()
    assert [page["pagina"] for page in preview["pages"]] == [1, 2]
    with sessions() as db:
        assert db.get(Syllabus, UUID(response.json()["id"])).file_path is None


@pytest.mark.parametrize("source_type", ["text", "pdf"])
def test_review_and_private_snapshot_use_the_same_sanitized_academic_text(api, source_type):
    raw = "Disciplina: Estrutura de Dados 1 | Prof. Pessoa Exemplo | CPF: 000.000.000-00"
    redacted = ("Disciplina: Estrutura de Dados 1 | Prof. [identificador removido] "
                "| CPF: [identificador removido]")
    if source_type == "text":
        sid, preview = prepare(api, raw + "\n" + TEXT)
        expected = [{"pagina": None, "texto": redacted + "\n" + TEXT}]
    else:
        response = api[0].post("/api/v1/syllabus/upload",
            data={"offering_id": "70000000-0000-4000-8000-000000000071"},
            files={"file": ("sintetico.pdf", make_pdf([raw, TEXT]), "application/pdf")})
        assert response.status_code == 202
        sid = response.json()["id"]
        preview = api[0].get(f"/api/v1/syllabus/{sid}/text").json()
        expected = [{"pagina": 1, "texto": redacted + "\n"}, {"pagina": 2, "texto": TEXT + "\n"}]

    assert preview["pages"] == expected
    assert preview["textHash"] == text_hash(expected)
    assert preview["redactedCount"] == 2
    assert preview["authorizationRequired"] is True
    with api[1]() as db:
        plan = db.get(Syllabus, UUID(sid))
        assert plan.prepared_pages == expected
        assert plan.redacted_count == 2
        assert plan.approved_pages is None


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


def test_historic_approved_snapshot_is_blocked_without_mutating_it(api, monkeypatch, caplog):
    monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY", "true")
    sid, preview = prepare(api)
    response = api[0].post(f"/api/v1/syllabus/{sid}/extractions", json=approval(preview))
    assert response.status_code == 202

    # Simula autorização anterior à cobertura de RG, com hash válido para aquele texto.
    sensitive = "12.345.678-X"
    historic = [{"pagina": None, "texto": f"RG: {sensitive}\n{TEXT}"}]
    with api[1]() as db:
        plan = db.get(Syllabus, UUID(sid))
        plan.approved_pages = historic
        plan.approved_hash = text_hash(historic)
        db.commit()

    calls = []

    def provider_runner(*args):
        calls.append(args)
        return process_document(*args)

    worker = SyllabusWorker(api[1], None, None, ProcessingConfig(), runner=provider_runner)
    with caplog.at_level("INFO", logger="agenda_unb.syllabus.worker"):
        assert worker.run_once()
    assert calls == []
    assert "texto_com_dados_pessoais" in caplog.text
    assert sensitive not in caplog.text
    with api[1]() as db:
        plan = db.get(Syllabus, UUID(sid))
        assert plan.status == "falha"
        assert plan.erro_codigo == "texto_com_dados_pessoais"
        assert plan.approved_pages == historic
        assert not db.scalars(select(AssessmentCandidate)).all()
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions",
                       json=approval(preview, reprocess=True)).status_code == 202


@pytest.mark.parametrize("page", [1, None])
def test_minimization_preserves_assessment_extraction(page):
    exam = "Prova 1 | 10/11/2026 | 14:30 | Sala 204"
    assignment = "Trabalho Final | 2026-11-24 | 10h00 | Auditório Central"
    raw = f"Disciplina: Cálculo Diferencial e Integral II\n{exam} | Prof. Ana Silva\n{assignment} | RG: 12.345.678-X"
    mock_response = json.dumps({"candidatos": [
        {"titulo": "Prova 1", "tipo": "prova", "data_sugerida": "2026-11-10",
         "hora_sugerida": "14:30", "pagina_origem": page, "trecho_origem": exam},
        {"titulo": "Trabalho Final", "tipo": "trabalho", "data_sugerida": "2026-11-24",
         "hora_sugerida": "10:00", "pagina_origem": page, "trecho_origem": assignment},
    ]})
    baseline = validate_candidates(mock_response, [TextPage(page, raw)])
    sanitized = validate_candidates(mock_response, [TextPage(page, minimize(raw))])
    assert sanitized == baseline
    assert sanitized.unsupported_dates == 0
    assert [(item.titulo, str(item.data_sugerida), str(item.hora_sugerida),
             item.pagina_origem, item.trecho_origem) for item in sanitized.candidates] == [
        ("Prova 1", "2026-11-10", "14:30:00", page, exam),
        ("Trabalho Final", "2026-11-24", "10:00:00", page, assignment),
    ]


def test_personal_data_reintroduced_by_edit_is_rejected_even_with_correct_hash(api, monkeypatch):
    monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY", "true")
    sid, preview = prepare(api)
    sensitive = "pessoa@example.test"
    edited = [{"pagina": None, "texto": f"{TEXT} | Contato: {sensitive}"}]
    response = api[0].post(f"/api/v1/syllabus/{sid}/extractions",
                           json=approval(preview, pages=edited, textHash=text_hash(edited)))
    assert response.status_code == 422
    assert "Remova os identificadores detectados" in response.json()["detail"]
    assert sensitive not in response.text
    assert api[0].get(f"/api/v1/syllabus/{sid}/text").json() == preview
    assert not SyllabusWorker(api[1], None, None, ProcessingConfig()).claim()


def test_redacted_count_distinguishes_old_records_from_zero_and_survives_edit(api, monkeypatch):
    monkeypatch.setenv("SYLLABUS_PROVIDER_TERMS_READY", "true")
    sid, preview = prepare(api, f"Prof. Pessoa Exemplo | {TEXT}")
    assert preview["redactedCount"] == 1
    edited = [{"pagina": None, "texto": TEXT}]
    assert api[0].post(f"/api/v1/syllabus/{sid}/extractions",
                       json=approval(preview, pages=edited, textHash=text_hash(edited))).status_code == 202
    reviewed = api[0].get(f"/api/v1/syllabus/{sid}/text").json()
    assert reviewed["redactedCount"] == 1 and reviewed["pages"] == edited

    old_sid, clean = prepare(api, f"[identificador removido]\n{TEXT}")
    assert clean["redactedCount"] == 0
    with api[1]() as db:
        db.get(Syllabus, UUID(old_sid)).redacted_count = None
        db.commit()
    assert api[0].get(f"/api/v1/syllabus/{old_sid}/text").json()["redactedCount"] is None


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
    assert api[0].post("/api/v1/syllabus/text", json={**({"text": "é" * 20001}), "offering_id": "70000000-0000-4000-8000-000000000071"}).status_code == 413


def test_text_preview_is_not_cacheable(api):
    sid, _ = prepare(api)
    assert api[0].get(f"/api/v1/syllabus/{sid}/text").headers["cache-control"] == "no-store"


@pytest.mark.parametrize("text", ["invalid\x00text", " ", "\n\t"])
def test_invalid_or_blank_text_is_rejected(api, text):
    assert api[0].post("/api/v1/syllabus/text", json={**({"text": text}), "offering_id": "70000000-0000-4000-8000-000000000071"}).status_code == 422


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
    response = api[0].post("/api/v1/syllabus/upload", data={"offering_id": "70000000-0000-4000-8000-000000000071"}, files={
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
    response = api[0].post("/api/v1/syllabus/upload", data={"offering_id": "70000000-0000-4000-8000-000000000071"}, files={
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
