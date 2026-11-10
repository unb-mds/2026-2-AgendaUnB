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
