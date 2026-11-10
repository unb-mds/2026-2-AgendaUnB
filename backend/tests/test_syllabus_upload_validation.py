"""Prazos reais do parser e responsividade da API, sem rede ou documentos reais."""
import asyncio
import multiprocessing
import threading
import time

import httpx
import pytest
from sqlalchemy import select

from src.database.models import Profile, Syllabus
from src.main import app
from src.modules.syllabus import services
from src.modules.syllabus.upload_validation import PdfValidationError, validate_pdf_structure
from src.services.storage import get_storage_service
from syllabus_samples import make_pdf
from syllabus_validation_stubs import StalledInspector, failing_inspector, invalid_inspector


def test_parser_deadline_terminates_child():
    reached = multiprocessing.get_context("spawn").Event()
    before = {child.pid for child in multiprocessing.active_children()}
    started = time.monotonic()
    with pytest.raises(PdfValidationError) as caught:
        validate_pdf_structure(b"%PDF-synthetic", 10, 3, _inspector=StalledInspector(reached))
    assert reached.is_set(), "O parser precisa ter iniciado antes do timeout"
    assert caught.value.code == "timeout"
    assert time.monotonic() - started < 6
    assert {child.pid for child in multiprocessing.active_children()} <= before


@pytest.mark.parametrize("inspector", [failing_inspector, invalid_inspector])
def test_parser_failure_is_sanitized(inspector, capfd):
    with pytest.raises(PdfValidationError) as caught:
        validate_pdf_structure(b"%PDF-PRIVATE_PDF_CONTENT_NEVER_LOG", 10, 8, _inspector=inspector)
    assert caught.value.code == "unavailable"
    assert "PRIVATE_PDF" not in str(caught.value) + str(capfd.readouterr())


@pytest.mark.parametrize("code,status", [("timeout", 422), ("unavailable", 503)])
def test_validation_failure_does_not_store_pdf_or_job(api, monkeypatch, code, status):
    client, TestSession, _, _ = api

    def reject(*args):
        raise PdfValidationError(code)

    def unexpected_upload(*args, **kwargs):
        pytest.fail("Não deve acessar Storage ou persistir um PDF sem validação")

    monkeypatch.setattr(services, "validate_pdf_structure", reject)
    monkeypatch.setattr("src.modules.syllabus.router.process_syllabus_upload", unexpected_upload)
    response = client.post("/api/v1/syllabus/upload", files={
        "file": ("sintetico.pdf", make_pdf(["Cronograma sintetico"]), "application/pdf")
    })
    assert response.status_code == status
    assert response.json()["detail"] == services.PDF_VALIDATION_MESSAGES[code]
    with TestSession() as session:
        assert session.scalar(select(Syllabus)) is None


@pytest.mark.parametrize("stage", ["validation", "preparation"])
def test_health_responds_during_slow_upload(api, monkeypatch, stage):
    _, TestSession, authenticated_user, _ = api
    with TestSession() as session:
        session.add(Profile(id=authenticated_user["value"].id, papel="student", nome_completo="Teste sintetico"))
        session.commit()

    entered, release = threading.Event(), threading.Event()

    def slow_operation():
        entered.set()
        assert release.wait(5), "O teste deve liberar a operação depois da resposta de /health"

    def validate(*args):
        if stage == "validation":
            slow_operation()

    def extract(*args):
        if stage == "preparation":
            slow_operation()
        return [{"pagina": 1, "texto": "Cronograma sintetico"}]

    monkeypatch.setattr(services, "validate_pdf_structure", validate)
    monkeypatch.setattr("src.modules.syllabus.router.extract_pdf_isolated", extract)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://test") as client:
            started = time.monotonic()
            upload = asyncio.create_task(client.post("/api/v1/syllabus/upload", files={
                "file": ("sintetico.pdf", make_pdf(["Cronograma sintetico"]), "application/pdf")
            }))
            try:
                assert await asyncio.to_thread(entered.wait, 3)
                health = await asyncio.wait_for(client.get("/health"), timeout=1)
                assert health.status_code == 200
                assert time.monotonic() - started < 2
                assert not upload.done(), "O upload deve continuar aguardando a operação lenta"
            finally:
                release.set()
                response = await upload
            assert response.status_code == 202

    asyncio.run(scenario())
