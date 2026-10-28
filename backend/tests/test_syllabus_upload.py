import io
from uuid import UUID, uuid4

import pypdf
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from src.database.models import Profile, Syllabus
from src.main import app
from src.middlewares.auth import CurrentUser, get_current_user
from src.services.storage import SupabaseStorageService, get_storage_service


BASE_VALID_PDF = b"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length 55 >> stream
BT
/F1 12 Tf
100 700 Td
(Plano de Ensino MDS 2026-2) Tj
ET
endstream endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000244 00000 n 
0000000350 00000 n 
trailer << /Size 6 /Root 1 0 R >>
startxref
432
%%EOF"""


def make_valid_pdf_bytes(pages: int = 1) -> bytes:
    if pages == 1:
        return BASE_VALID_PDF
    reader = pypdf.PdfReader(io.BytesIO(BASE_VALID_PDF))
    writer = pypdf.PdfWriter()
    for _ in range(pages):
        writer.add_page(reader.pages[0])
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_blank_pdf_bytes() -> bytes:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def make_encrypted_pdf_bytes() -> bytes:
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.encrypt("segredo123")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_upload_syllabus_success(api):
    client, TestSession, authenticated_user, _ = api
    user_id = authenticated_user["value"].id

    with TestSession() as session:
        session.add(Profile(id=user_id, papel="student", nome_completo="Aluno Teste"))
        session.commit()

    pdf_bytes = make_valid_pdf_bytes(pages=1)
    files = {
        "file": ("plano_de_ensino.pdf", io.BytesIO(pdf_bytes), "application/pdf")
    }
    data = {
        "disciplina": "Métodos de Desenvolvimento de Software",
        "turma": "01",
    }

    response = client.post("/api/v1/syllabus/upload", files=files, data=data)

    assert response.status_code == 202
    body = response.json()
    assert "id" in body
    assert body["status"] == "processing"
    assert body["fileName"] == "plano_de_ensino.pdf"
    assert str(user_id) in body["filePath"]
    assert body["fileType"] == "pdf"
    assert body["fileSize"] == len(pdf_bytes)

    # Verifica no banco se o registro foi salvo com status 'processing'
    with TestSession() as session:
        record = session.scalar(select(Syllabus).where(Syllabus.id == UUID(body["id"])))
        assert record is not None
        assert record.user_id == user_id
        assert record.status == "processing"
        assert record.file_name == "plano_de_ensino.pdf"
        assert record.disciplina == "Métodos de Desenvolvimento de Software"
        assert record.turma == "01"


def test_upload_syllabus_unauthenticated(api):
    client, _, _, _ = api

    def reject_auth():
        raise HTTPException(status_code=401, detail="Autenticação necessária")

    app.dependency_overrides[get_current_user] = reject_auth

    pdf_bytes = make_valid_pdf_bytes()
    files = {"file": ("plano.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/api/v1/syllabus/upload", files=files)
    assert response.status_code == 401


def test_upload_syllabus_invalid_extension(api):
    client, _, _, _ = api

    files = {"file": ("plano.docx", io.BytesIO(b"conteudo"), "application/pdf")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 400
    assert "Extensão de arquivo inválida" in response.json()["detail"]


def test_upload_syllabus_invalid_mime_type(api):
    client, _, _, _ = api

    files = {"file": ("plano.pdf", io.BytesIO(b"conteudo"), "text/plain")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 400
    assert "MIME Type inválido" in response.json()["detail"]


def test_upload_syllabus_empty_file(api):
    client, _, _, _ = api

    files = {"file": ("plano.pdf", io.BytesIO(b""), "application/pdf")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 400
    assert "vazio" in response.json()["detail"]


def test_upload_syllabus_invalid_magic_bytes(api):
    client, _, _, _ = api

    files = {"file": ("plano.pdf", io.BytesIO(b"NOT_A_PDF_STREAM_12345"), "application/pdf")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 400
    assert "Assinatura de arquivo inválida" in response.json()["detail"]


def test_upload_syllabus_corrupted_pdf(api):
    client, _, _, _ = api

    files = {"file": ("plano.pdf", io.BytesIO(b"%PDF-corrupted-broken-content-XYZ"), "application/pdf")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 400
    assert "corrompido ou malformado" in response.json()["detail"]


def test_upload_syllabus_encrypted_pdf(api):
    client, _, _, _ = api

    pdf_bytes = make_encrypted_pdf_bytes()
    files = {"file": ("plano.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 400
    assert "protegido por senha" in response.json()["detail"]


def test_upload_syllabus_without_selectable_text(api):
    client, _, _, _ = api

    pdf_bytes = make_blank_pdf_bytes()
    files = {"file": ("plano.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 400
    assert "texto selecionável legível" in response.json()["detail"]


def test_upload_syllabus_exceeds_max_pages(api):
    client, _, _, _ = api

    pdf_bytes = make_valid_pdf_bytes(pages=11)
    files = {"file": ("plano.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 400
    assert "ultrapassando o limite máximo" in response.json()["detail"]


def test_upload_syllabus_payload_too_large(api, monkeypatch):
    client, _, _, _ = api
    monkeypatch.setattr("src.modules.syllabus.services.MAX_FILE_SIZE_BYTES", 50)

    pdf_bytes = make_valid_pdf_bytes()
    files = {"file": ("plano.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    response = client.post("/api/v1/syllabus/upload", files=files)

    assert response.status_code == 413
    assert "excede o limite máximo permitido" in response.json()["detail"]


def test_upload_syllabus_storage_failure(api):
    client, _, authenticated_user, _ = api

    class FailingStorage(SupabaseStorageService):
        def upload_file(self, *args, **kwargs):
            raise HTTPException(
                status_code=502,
                detail="Erro ao salvar arquivo no bucket de armazenamento.",
            )

    app.dependency_overrides[get_storage_service] = lambda: FailingStorage()

    pdf_bytes = make_valid_pdf_bytes()
    files = {"file": ("plano.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    response = client.post("/api/v1/syllabus/upload", files=files)
    assert response.status_code == 502

    app.dependency_overrides.pop(get_storage_service, None)


def test_upload_syllabus_db_failure_compensates_storage(api, monkeypatch):
    client, _, authenticated_user, _ = api

    deleted_paths = []

    class MockStorage(SupabaseStorageService):
        def upload_file(self, path, content, *args, **kwargs):
            return f"syllabus_files/{path}"

        def delete_file(self, path, *args, **kwargs):
            deleted_paths.append(path)
            return True

    app.dependency_overrides[get_storage_service] = lambda: MockStorage()

    # Simular erro na transação do banco forçando exceção
    def failing_commit(*args, **kwargs):
        raise RuntimeError("DB Commit Failure")

    pdf_bytes = make_valid_pdf_bytes()
    files = {"file": ("plano.pdf", io.BytesIO(pdf_bytes), "application/pdf")}

    # Patch session commit
    monkeypatch.setattr("sqlalchemy.orm.Session.commit", failing_commit)

    response = client.post("/api/v1/syllabus/upload", files=files)
    assert response.status_code == 503
    assert "Falha ao registrar o envio do plano de ensino" in response.json()["detail"]

    # Verifica se a compensação no Storage foi executada
    assert len(deleted_paths) == 1
    assert str(authenticated_user["value"].id) in deleted_paths[0]

    app.dependency_overrides.pop(get_storage_service, None)


def test_get_syllabus_status(api):
    client, TestSession, authenticated_user, _ = api
    user_id = authenticated_user["value"].id

    with TestSession() as session:
        session.add(Profile(id=user_id, papel="student", nome_completo="Aluno Teste"))
        syllabus = Syllabus(
            id=uuid4(),
            user_id=user_id,
            professor_id=user_id,
            file_name="plano.pdf",
            file_path=f"syllabus_files/{user_id}/plano.pdf",
            file_size=1024,
            file_type="pdf",
            status="processing",
            disciplina="Cálculo 1",
            turma="A",
        )
        session.add(syllabus)
        session.commit()
        syllabus_id = syllabus.id

    response = client.get(f"/api/v1/syllabus/{syllabus_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(syllabus_id)
    assert body["status"] == "processing"
    assert body["fileName"] == "plano.pdf"
    assert body["disciplina"] == "Cálculo 1"


def test_get_syllabus_status_forbidden_for_other_user(api):
    client, TestSession, authenticated_user, _ = api
    other_user_id = uuid4()

    with TestSession() as session:
        syllabus = Syllabus(
            id=uuid4(),
            user_id=other_user_id,
            file_name="plano_outro_usuario.pdf",
            file_path=f"syllabus_files/{other_user_id}/plano.pdf",
            file_size=1024,
            file_type="pdf",
            status="processing",
        )
        session.add(syllabus)
        session.commit()
        syllabus_id = syllabus.id

    # O usuário logado atual tenta acessar o plano de outro usuário
    response = client.get(f"/api/v1/syllabus/{syllabus_id}")
    assert response.status_code == 404
