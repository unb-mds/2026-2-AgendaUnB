"""Testes unitários e de contrato para o módulo account, descarte de PDFs e sanitização de logs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from scripts.descartar_pdfs import discard_legacy_pdfs
from src.database.models import (
    AccountDeletionRecord,
    AssessmentCandidate,
    ClassFollow,
    ClassOffering,
    Consent,
    GoogleCalendarConnection,
    GoogleCalendarEventExport,
    ImportItem,
    ImportOperation,
    PersonalEvent,
    Profile,
    PublicEvent,
    Reminder,
    SavedPublicEvent,
    Subject,
    Syllabus,
    SyllabusVersion,
    TermAcceptance,
)
from src.main import app
from src.middlewares.auth import CurrentUser
from src.modules.account import repository as account_repository
from src.modules.account import service as account_service
from src.modules.google_calendar import service as gcal_service
from src.modules.syllabus.extraction import CandidateData, ExtractionResult
from src.modules.syllabus.processing_config import ProcessingConfig, ProcessingError
from src.modules.syllabus.processing_task import DocumentResult
from src.modules.syllabus.worker import SyllabusWorker
from src.services.storage import SupabaseStorageService, get_storage_service
from syllabus_samples import approved_source


def _make_user(role: str = "student", email: str = "ana@unb.br") -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        role=role,
        access_token="user-jwt-secret-token",
        email=email,
        email_confirmed=True,
    )


def _seed_profile(SessionLocal, user: CurrentUser, name: str = "Ana Teste") -> None:
    with SessionLocal() as db:
        db.add(Profile(id=user.id, papel=user.role, nome_completo=name))
        db.commit()


def test_legal_documents_reports_pending_and_accept_updates_state(api):
    client, SessionLocal, auth_state, _ = api
    user = _make_user()
    auth_state["value"] = user
    _seed_profile(SessionLocal, user)

    res = client.get("/api/v1/me/legal-documents")
    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-store"
    body = res.json()
    assert body["terms"]["currentVersion"] == account_repository.CURRENT_LEGAL_VERSIONS["terms"]
    assert body["terms"]["acceptedVersion"] is None
    assert body["terms"]["acceptedAt"] is None
    assert body["terms"]["pending"] is True
    assert body["privacy"]["pending"] is True

    put_terms = client.put(
        "/api/v1/me/legal-acceptances/terms",
        json={"version": account_repository.CURRENT_LEGAL_VERSIONS["terms"]},
    )
    assert put_terms.status_code == 204
    assert put_terms.headers["cache-control"] == "no-store"

    # Reenvio idempotente continua retornando 204.
    put_terms_again = client.put(
        "/api/v1/me/legal-acceptances/terms",
        json={"version": account_repository.CURRENT_LEGAL_VERSIONS["terms"]},
    )
    assert put_terms_again.status_code == 204

    after_terms = client.get("/api/v1/me/legal-documents").json()
    assert after_terms["terms"]["pending"] is False
    assert after_terms["terms"]["acceptedVersion"] == account_repository.CURRENT_LEGAL_VERSIONS["terms"]
    assert after_terms["terms"]["acceptedAt"] is not None
    assert after_terms["privacy"]["pending"] is True

    put_privacy = client.put(
        "/api/v1/me/legal-acceptances/privacy",
        json={"version": account_repository.CURRENT_LEGAL_VERSIONS["privacy"]},
    )
    assert put_privacy.status_code == 204
    after_all = client.get("/api/v1/me/legal-documents").json()
    assert after_all["terms"]["pending"] is False
    assert after_all["privacy"]["pending"] is False


def test_legal_acceptance_rejects_stale_version_with_409_and_invalid_doc_with_422(api):
    client, SessionLocal, auth_state, _ = api
    user = _make_user()
    auth_state["value"] = user
    _seed_profile(SessionLocal, user)

    stale = client.put("/api/v1/me/legal-acceptances/terms", json={"version": "2020-01-01"})
    assert stale.status_code == 409

    invalid_doc = client.put(
        "/api/v1/me/legal-acceptances/cookies",
        json={"version": account_repository.CURRENT_LEGAL_VERSIONS["terms"]},
    )
    assert invalid_doc.status_code == 422

    extra_field = client.put(
        "/api/v1/me/legal-acceptances/terms",
        json={"version": account_repository.CURRENT_LEGAL_VERSIONS["terms"], "extra": "x"},
    )
    assert extra_field.status_code == 422


def test_google_calendar_callback_records_consent_and_delete_consent_revokes_token(api, monkeypatch):
    client, SessionLocal, auth_state, _ = api
    user = _make_user()
    auth_state["value"] = user
    _seed_profile(SessionLocal, user)

    assert client.put(
        "/api/v1/me/legal-acceptances/terms",
        json={"version": account_repository.CURRENT_LEGAL_VERSIONS["terms"]},
    ).status_code == 204

    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_SECRET", "google-secret")
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_CALENDAR_REDIRECT_URI", "https://api.example.edu/api/v1/me/google-calendar/callback")
    monkeypatch.setenv("GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI", "https://app.example.edu/eventos?aba=meus")
    monkeypatch.setattr(gcal_service, "confirmed_agenda_email", lambda db, uid: user.email)

    auth_res = client.post("/api/v1/me/google-calendar/authorization")
    assert auth_res.status_code == 200
    state = parse_qs(urlsplit(auth_res.json()["authorization_url"]).query)["state"][0]

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: httpx.Response(
            200,
            json={
                "access_token": "provider-access-secret",
                "refresh_token": "provider-refresh-secret",
                "expires_in": 3600,
                "scope": gcal_service.CALENDAR_SCOPE,
            },
        ),
    )
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: httpx.Response(
            200,
            json={"email": user.email, "email_verified": True, "sub": "google-ana-sub"},
        ),
    )
    cb = client.post(
        "/api/v1/me/google-calendar/callback",
        data={"state": state, "code": "oauth-code"},
        follow_redirects=False,
    )
    assert cb.status_code == 303

    consents_res = client.get("/api/v1/me/consents")
    assert consents_res.status_code == 200
    assert consents_res.headers["cache-control"] == "no-store"
    items = consents_res.json()["items"]
    assert len(items) == 1
    assert items[0]["purpose"] == "google_agenda"
    assert items[0]["active"] is True
    assert items[0]["revokedAt"] is None

    revoked_tokens = []

    def fake_revoke(url, **kwargs):
        assert url == gcal_service.REVOCATION_ENDPOINT
        revoked_tokens.append(kwargs["data"]["token"])
        return httpx.Response(200)

    monkeypatch.setattr(httpx, "post", fake_revoke)
    del_consent = client.delete("/api/v1/me/consents/google_agenda")
    assert del_consent.status_code == 204
    assert revoked_tokens == ["provider-refresh-secret"]

    after_consents = client.get("/api/v1/me/consents").json()["items"]
    assert len(after_consents) == 1
    assert after_consents[0]["active"] is False
    assert after_consents[0]["revokedAt"] is not None

    with SessionLocal() as db:
        conn = db.get(GoogleCalendarConnection, user.id)
        assert conn is not None
        assert conn.encrypted_access_token is None
        assert conn.encrypted_refresh_token is None

    # Aceite de termos permanece independente do consentimento revogado.
    assert client.get("/api/v1/me/legal-documents").json()["terms"]["pending"] is False
    assert client.delete("/api/v1/me/consents/envio_texto_ia").status_code == 422


def test_export_is_a_private_download(api):
    client, SessionLocal, auth_state, _ = api
    user = _make_user()
    auth_state["value"] = user
    _seed_profile(SessionLocal, user)

    res = client.get("/api/v1/me/data-export")
    assert res.status_code == 200
    assert res.headers["cache-control"] == "no-store"
    assert res.headers["content-disposition"] == 'attachment; filename="agenda-unb-dados.json"'


def test_export_contains_the_account_data_and_nobody_elses(api):
    client, SessionLocal, auth_state, ids = api
    ana = _make_user(email="ana@unb.br")
    bruno = _make_user(email="bruno@unb.br")
    auth_state["value"] = ana

    with SessionLocal() as db:
        db.add_all([
            Profile(id=ana.id, papel="student", nome_completo="Ana Silva"),
            Profile(id=bruno.id, papel="student", nome_completo="Bruno Outro"),
        ])
        subject = Subject(code="CIC0004", name="Algoritmos", unit="673")
        db.add(subject)
        db.flush()
        offering = ClassOffering(subject_id=subject.id, class_number="01", year=2026, semester=2)
        db.add(offering)
        db.flush()
        db.add_all([
            ClassFollow(user_id=ana.id, offering_id=offering.id),
            ClassFollow(user_id=bruno.id, offering_id=offering.id),
        ])

        ana_pub = PublicEvent(
            author_id=ana.id,
            title="Semana da Computação Ana",
            description="Evento público de Ana",
            starts_at=datetime(2026, 11, 20, 14, tzinfo=timezone.utc),
            campus_id=ids["campus"],
            category_id=ids["category"],
            status="aprovado",
        )
        bruno_pub = PublicEvent(
            author_id=bruno.id,
            title="Evento Privado Bruno Pendente",
            description="Segredo de Bruno",
            starts_at=datetime(2026, 11, 21, 14, tzinfo=timezone.utc),
            status="pendente",
        )
        db.add_all([ana_pub, bruno_pub])
        db.flush()
        db.add_all([
            SavedPublicEvent(user_id=ana.id, event_id=ana_pub.id),
            SavedPublicEvent(user_id=bruno.id, event_id=bruno_pub.id),
        ])
        db.add_all([
            PersonalEvent(
                user_id=ana.id,
                title="Prova de Ana",
                description="Capítulos 1 a 3",
                starts_at=datetime(2026, 11, 22, 14, tzinfo=timezone.utc),
            ),
            PersonalEvent(
                user_id=bruno.id,
                title="Prova de Bruno",
                description="Segredo acadêmico Bruno",
                starts_at=datetime(2026, 11, 22, 16, tzinfo=timezone.utc),
            ),
        ])

        ana_syl = Syllabus(
            user_id=ana.id,
            file_name="plano_ana.pdf",
            file_path=f"syllabus_files/{ana.id}/segredo_interno.pdf",
            status="concluido",
            prepared_pages=[{"pagina": 1, "texto": "Texto preparado Ana"}],
            approved_pages=[{"pagina": 1, "texto": "Texto aprovado Ana"}],
            approved_hash="a" * 64,
            processing_token=uuid4(),
        )
        bruno_syl = Syllabus(
            user_id=bruno.id,
            file_name="plano_bruno.pdf",
            file_path=f"syllabus_files/{bruno.id}/segredo_bruno.pdf",
            status="concluido",
        )
        db.add_all([ana_syl, bruno_syl])
        db.flush()

        ana_ver = SyllabusVersion(syllabus_id=ana_syl.id, number=1, author_id=ana.id, visibility="privada")
        bruno_rev_on_ana = SyllabusVersion(
            syllabus_id=ana_syl.id, number=2, author_id=bruno.id, visibility="privada"
        )
        db.add_all([ana_ver, bruno_rev_on_ana])
        db.flush()

        ana_cand = AssessmentCandidate(
            syllabus_id=ana_syl.id, version_id=ana_ver.id, title="P1 Ana", status="pendente"
        )
        bruno_cand_on_ana = AssessmentCandidate(
            syllabus_id=ana_syl.id, version_id=bruno_rev_on_ana.id, title="Rascunho Privado Bruno", status="pendente"
        )
        db.add_all([ana_cand, bruno_cand_on_ana])
        db.flush()
        ana_cand_id = str(ana_cand.id)

        op_ana = ImportOperation(
            user_id=ana.id,
            idempotency_key="key-ana",
            version_id=ana_ver.id,
            content_hash="b" * 64,
        )
        op_bruno = ImportOperation(
            user_id=bruno.id,
            idempotency_key="key-bruno",
            version_id=bruno_rev_on_ana.id,
            content_hash="c" * 64,
        )
        db.add_all([op_ana, op_bruno])
        db.flush()
        db.add(
            ImportItem(
                operation_id=op_ana.id,
                candidate_id=ana_cand.id,
                result="criado",
                candidate_type="prova",
            )
        )
        db.add_all([
            TermAcceptance(user_id=ana.id, document="terms", version="2026-11-18"),
            TermAcceptance(user_id=bruno.id, document="terms", version="2026-11-18"),
            Consent(user_id=ana.id, purpose="google_agenda"),
            Consent(user_id=bruno.id, purpose="google_agenda"),
            Reminder(user_id=ana.id, event_kind="publico_salvo", public_event_id=ana_pub.id,
                     event_starts_at=ana_pub.starts_at, scheduled_for=datetime(2026, 11, 19, 14, tzinfo=timezone.utc)),
            Reminder(user_id=bruno.id, event_kind="publico_salvo", public_event_id=bruno_pub.id,
                     event_starts_at=bruno_pub.starts_at, scheduled_for=datetime(2026, 11, 20, 14, tzinfo=timezone.utc)),
            GoogleCalendarEventExport(user_id=ana.id, event_kind="saved", local_event_id=ana_pub.id,
                                      calendar_id="cal-ana", google_event_id="agenda-event-ana",
                                      exported_version="d" * 64, last_idempotency_key="private-export-key"),
            GoogleCalendarEventExport(user_id=bruno.id, event_kind="saved", local_event_id=bruno_pub.id,
                                      calendar_id="cal-bruno", google_event_id="agenda-event-bruno",
                                      exported_version="e" * 64),
            GoogleCalendarConnection(
                user_id=ana.id,
                google_sub="secret-google-sub-ana",
                google_email="ana@unb.br",
                calendar_id="cal-ana",
                encrypted_access_token="encrypted-access-secret",
                encrypted_refresh_token="encrypted-refresh-secret",
                granted_scope=gcal_service.CALENDAR_SCOPE,
            ),
            GoogleCalendarConnection(
                user_id=bruno.id,
                google_sub="secret-google-sub-bruno",
                google_email="bruno@unb.br",
                calendar_id="cal-bruno",
                encrypted_access_token="encrypted-bruno",
                encrypted_refresh_token="encrypted-bruno-refresh",
                granted_scope=gcal_service.CALENDAR_SCOPE,
            ),
        ])
        db.commit()

    res = client.get("/api/v1/me/data-export")
    assert res.status_code == 200
    raw = res.text
    data = res.json()

    assert data["profile"]["email"] == "ana@unb.br"
    assert [e["title"] for e in data["personalEvents"]] == ["Prova de Ana"]
    assert [e["title"] for e in data["publicEvents"]] == ["Semana da Computação Ana"]
    assert [s["file_name"] for s in data["syllabi"]] == ["plano_ana.pdf"]
    assert [v["candidates"][0]["title"] for v in data["authoredPlanVersions"]] == ["P1 Ana"]
    assert len(data["importOperations"]) == 1
    assert data["votes"] == []
    assert data["googleCalendar"]["calendar_id"] == "cal-ana"
    public_event_id = data["publicEvents"][0]["id"]
    assert [(row["public_event_id"], row["status"]) for row in data["reminders"]] == [(public_event_id, "pendente")]
    assert [(row["local_event_id"], row["google_event_id"]) for row in data["googleCalendarExports"]] == [
        (public_event_id, "agenda-event-ana")
    ]

    # Nenhum dado de outro usuário ou segredo interno aparece na exportação.
    for forbidden in (
        "Bruno",
        "bruno@unb.br",
        "Rascunho Privado Bruno",
        "segredo_interno.pdf",
        "encrypted-access-secret",
        "encrypted-refresh-secret",
        "secret-google-sub-ana",
        "agenda-event-bruno",
        "private-export-key",
        "d" * 64,
        "a" * 64,
    ):
        assert forbidden not in raw

    # Exportação inclui votos quando registrados em votos_avaliacao.
    with SessionLocal() as db:
        db.execute(
            text(
                "insert into votos_avaliacao (user_id, avaliacao_id, valor, criado_em, atualizado_em) "
                "values (:uid, :cid, 'confirma', '2026-11-18T00:00:00Z', '2026-11-18T00:00:00Z')"
            ),
            {"uid": ana.id.hex, "cid": ana_cand_id},
        )
        db.commit()
    res_with_votes = client.get("/api/v1/me/data-export")
    assert res_with_votes.status_code == 200
    assert len(res_with_votes.json()["votes"]) == 1


def test_delete_requires_explicit_confirmation_and_removes_files_first(api, monkeypatch):
    client, SessionLocal, auth_state, _ = api
    ana = _make_user(email="ana@unb.br")
    auth_state["value"] = ana

    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_ID", "google-client")
    monkeypatch.setenv("GOOGLE_CALENDAR_CLIENT_SECRET", "google-secret")
    monkeypatch.setenv("GOOGLE_TOKEN_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setenv("GOOGLE_CALENDAR_REDIRECT_URI", "https://api.example.edu/api/v1/me/google-calendar/callback")
    monkeypatch.setenv("GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI", "https://app.example.edu/eventos?aba=meus")
    cipher = gcal_service.GoogleOAuthSettings.from_env().cipher

    with SessionLocal() as db:
        db.add(Profile(id=ana.id, papel="student", nome_completo="Ana"))
        db.add(PersonalEvent(user_id=ana.id, title="Compromisso", starts_at=datetime.now(timezone.utc)))
        db.add(PublicEvent(author_id=ana.id, title="Evento Ana", description="Desc", starts_at=datetime.now(timezone.utc)))
        db.add(
            Syllabus(
                user_id=ana.id,
                file_name="legacy.pdf",
                file_path=f"syllabus_files/{ana.id}/legacy.pdf",
                status="concluido",
            )
        )
        db.add(
            GoogleCalendarConnection(
                user_id=ana.id,
                google_sub="g-sub",
                google_email="ana@unb.br",
                encrypted_access_token=cipher.encrypt(b"acc").decode(),
                encrypted_refresh_token=cipher.encrypt(b"ref-secret").decode(),
                access_token_expires_at=datetime.now(timezone.utc),
                granted_scope=gcal_service.CALENDAR_SCOPE,
            )
        )
        db.add(Consent(user_id=ana.id, purpose="google_agenda"))
        db.add(TermAcceptance(user_id=ana.id, document="terms", version="2026-11-18"))
        db.commit()

    # Confirmação inválida retorna 422.
    bad_confirm = client.request("DELETE", "/api/v1/me", json={"confirmation": "excluir"})
    assert bad_confirm.status_code == 422

    events: list[tuple[str, object]] = []

    class FakeStorage(SupabaseStorageService):
        def __init__(self, *, fail_delete: bool = False):
            super().__init__(supabase_url="https://storage.test", supabase_key="srv-key")
            self.fail_delete = fail_delete

        def list_prefix(self, prefix: str, *, page_size: int = 100) -> list[str]:
            events.append(("storage_list", prefix))
            return [f"{ana.id}/legacy.pdf"]

        def delete_objects_strict(self, paths) -> int:
            normalized = list(dict.fromkeys(self.normalize_path(p) for p in paths if self.normalize_path(p)))
            events.append(("storage_delete", normalized))
            if self.fail_delete:
                raise HTTPException(status_code=503, detail="Storage indisponível")
            return len(normalized)

    class FakeAuthAdmin(account_service.SupabaseAuthAdminClient):
        def delete_user(self, user_id: UUID) -> None:
            events.append(("auth_delete", user_id))

    monkeypatch.setattr(
        httpx,
        "post",
        lambda url, **kwargs: events.append(("google_revoke", kwargs["data"]["token"])) or httpx.Response(200),
    )

    app.dependency_overrides[get_storage_service] = lambda: FakeStorage(fail_delete=True)
    app.dependency_overrides[account_service.get_auth_admin_client] = lambda: FakeAuthAdmin()

    failed = client.request("DELETE", "/api/v1/me", json={"confirmation": "EXCLUIR MINHA CONTA"})
    assert failed.status_code == 503
    assert all(ev[0] != "auth_delete" for ev in events)
    with SessionLocal() as db:
        assert db.get(Profile, ana.id) is not None

    # Restaura refresh token para verificar ordenação completa no retry.
    with SessionLocal() as db:
        conn = db.get(GoogleCalendarConnection, ana.id)
        conn.encrypted_refresh_token = cipher.encrypt(b"ref-secret-2").decode()
        db.commit()

    events.clear()
    app.dependency_overrides[get_storage_service] = lambda: FakeStorage(fail_delete=False)
    ok = client.request("DELETE", "/api/v1/me", json={"confirmation": "EXCLUIR MINHA CONTA"})
    assert ok.status_code == 204
    assert [ev[0] for ev in events] == ["google_revoke", "storage_list", "storage_delete", "auth_delete"]
    assert events[2][1] == [f"{ana.id}/legacy.pdf"]

    with SessionLocal() as db:
        assert db.get(Profile, ana.id) is None
        assert db.query(PersonalEvent).filter_by(user_id=ana.id).count() == 0
        assert db.query(Syllabus).filter_by(user_id=ana.id).count() == 0
        records = db.query(AccountDeletionRecord).filter_by(status="concluida").all()
        assert len(records) >= 1
        latest = records[-1]
        assert latest.removed_syllabi == 1
        assert latest.removed_personal_events == 1
        assert latest.removed_public_events == 1
        assert latest.removed_storage_files == 1


def test_last_admin_cannot_delete_account_but_second_admin_can(api):
    client, SessionLocal, auth_state, _ = api
    admin1 = _make_user(role="admin", email="admin1@unb.br")
    admin2 = _make_user(role="admin", email="admin2@unb.br")
    auth_state["value"] = admin1
    _seed_profile(SessionLocal, admin1, "Admin 1")

    auth_calls = []

    class FakeAuthAdmin(account_service.SupabaseAuthAdminClient):
        def delete_user(self, user_id: UUID) -> None:
            auth_calls.append(user_id)

    app.dependency_overrides[account_service.get_auth_admin_client] = lambda: FakeAuthAdmin()

    blocked = client.request("DELETE", "/api/v1/me", json={"confirmation": "EXCLUIR MINHA CONTA"})
    assert blocked.status_code == 409
    assert auth_calls == []

    _seed_profile(SessionLocal, admin2, "Admin 2")
    allowed = client.request("DELETE", "/api/v1/me", json={"confirmation": "EXCLUIR MINHA CONTA"})
    assert allowed.status_code == 204
    assert auth_calls == [admin1.id]


def test_account_deletion_mid_job_and_classmate_copies_safe(api):
    client, SessionLocal, auth_state, _ = api
    ana = _make_user(email="ana@unb.br")
    bruno = _make_user(email="bruno@unb.br")
    auth_state["value"] = ana
    snap = approved_source("Prova 1 em 10/11/2026")

    with SessionLocal() as db:
        db.add_all([
            Profile(id=ana.id, papel="student", nome_completo="Ana"),
            Profile(id=bruno.id, papel="student", nome_completo="Bruno"),
        ])
        syl = Syllabus(
            user_id=ana.id,
            file_name="plano.pdf",
            status="pendente",
            prepared_pages=snap["approved_pages"],
            approved_pages=snap["approved_pages"],
            approved_hash=snap["approved_hash"],
            authorized_at=datetime.now(timezone.utc),
            queued_at=datetime.now(timezone.utc),
            text_revision=1,
        )
        db.add(syl)
        db.flush()
        ver = SyllabusVersion(syllabus_id=syl.id, number=1, author_id=ana.id, visibility="compartilhada")
        db.add(ver)
        db.flush()
        syl.approved_version_id = ver.id
        db.add(
            PersonalEvent(
                user_id=bruno.id,
                title="Cópia importada de Bruno",
                starts_at=datetime(2026, 11, 10, 17, tzinfo=timezone.utc),
                origin_syllabus_id=syl.id,
                origin_version_id=ver.id,
                origin_candidate_id=uuid4(),
                origin_excerpt="Prova 1 em 10/11/2026",
            )
        )
        db.commit()
        syl_id = syl.id

    class FakeAuthAdmin(account_service.SupabaseAuthAdminClient):
        def delete_user(self, user_id: UUID) -> None:
            pass

    app.dependency_overrides[account_service.get_auth_admin_client] = lambda: FakeAuthAdmin()

    cfg = ProcessingConfig(
        provider_terms_ready=True,
        api_key="fake",
        model="gemini-test",
        lease_seconds=300,
        max_attempts=3,
        retry_delay_seconds=30,
        rate_limit_delay_seconds=60,
        min_interval_seconds=0,
    )
    worker = SyllabusWorker(SessionLocal, None, None, cfg)
    lease = worker.claim()
    assert lease is not None and lease.id == syl_id

    # Conta excluída enquanto a extração está em andamento.
    del_res = client.request("DELETE", "/api/v1/me", json={"confirmation": "EXCLUIR MINHA CONTA"})
    assert del_res.status_code == 204

    # Conclusão/falha do worker não gera exceção nem recria registros órfãos.
    worker.fail(lease, ProcessingError("erro_interno", retryable=True), 10)
    with SessionLocal() as db:
        assert db.get(Syllabus, syl_id) is None
        bruno_events = db.query(PersonalEvent).filter_by(user_id=bruno.id).all()
        assert len(bruno_events) == 1
        assert bruno_events[0].title == "Cópia importada de Bruno"
        assert bruno_events[0].origin_version_id is None
        assert bruno_events[0].origin_syllabus_id == syl_id


def test_descartar_pdfs_dry_run_and_execute_skips_pending_and_is_idempotent(api, monkeypatch):
    _, SessionLocal, _, _ = api
    uid = uuid4()
    with SessionLocal() as db:
        db.add(Profile(id=uid, papel="student", nome_completo="Ana"))
        db.add_all([
            Syllabus(
                user_id=uid,
                file_name="a.pdf",
                file_path=f"syllabus_files/{uid}/a.pdf",
                status="concluido",
            ),
            Syllabus(
                user_id=uid,
                file_name="b.pdf",
                arquivo_url=f"syllabus_files/{uid}/b.pdf",
                status="falha",
            ),
            Syllabus(
                user_id=uid,
                file_name="c.pdf",
                file_path=f"syllabus_files/{uid}/c.pdf",
                status="pendente",
            ),
            Syllabus(
                user_id=uid,
                file_name="d.pdf",
                file_path=f"syllabus_files/{uid}/d.pdf",
                status="processando",
            ),
        ])
        db.commit()

    storage = SupabaseStorageService(supabase_url="https://storage.test", supabase_key="srv-key")
    called_deletes: list[str] = []

    def fake_delete(url, **kwargs):
        called_deletes.append(url)
        if url.endswith("/b.pdf"):
            return httpx.Response(404)
        return httpx.Response(204)

    monkeypatch.setattr(httpx, "delete", fake_delete)

    with SessionLocal() as db:
        dry = discard_legacy_pdfs(db, storage, execute=False, batch_size=1)
        assert dry == {"dry_run": True, "eligible": 2, "discarded": 0, "failed": 0}
        assert called_deletes == []

        executed = discard_legacy_pdfs(db, storage, execute=True, batch_size=1)
        assert executed == {"dry_run": False, "eligible": 2, "discarded": 2, "failed": 0}
        assert set(called_deletes) == {
            f"https://storage.test/storage/v1/object/syllabus_files/{uid}/a.pdf",
            f"https://storage.test/storage/v1/object/syllabus_files/{uid}/b.pdf",
        }
        assert len(called_deletes) == 2

        rows = {row.file_name: row for row in db.query(Syllabus).all()}
        assert rows["a.pdf"].file_path is None and rows["a.pdf"].discarded_at is not None
        assert rows["b.pdf"].arquivo_url is None and rows["b.pdf"].discarded_at is not None
        assert rows["c.pdf"].file_path is not None and rows["c.pdf"].discarded_at is None
        assert rows["d.pdf"].file_path is not None and rows["d.pdf"].discarded_at is None

        rerun = discard_legacy_pdfs(db, storage, execute=False)
        assert rerun == {"dry_run": True, "eligible": 0, "discarded": 0, "failed": 0}

    # Falha parcial no Storage preserva o registro no banco para nova tentativa.
    with SessionLocal() as db:
        db.add(
            Syllabus(
                user_id=uid,
                file_name="e.pdf",
                file_path=f"syllabus_files/{uid}/e.pdf",
                status="concluido",
            )
        )
        db.commit()
    monkeypatch.setattr(httpx, "delete", lambda *args, **kwargs: httpx.Response(503))
    with SessionLocal() as db:
        failed_run = discard_legacy_pdfs(db, storage, execute=True)
        assert failed_run == {"dry_run": False, "eligible": 1, "discarded": 0, "failed": 1}
        still_there = db.query(Syllabus).filter_by(file_name="e.pdf").one()
        assert still_there.file_path == f"syllabus_files/{uid}/e.pdf"
        assert still_there.discarded_at is None


def test_descartar_pdfs_deletes_both_distinct_paths_and_retries_cleanly(api, monkeypatch):
    _, SessionLocal, _, _ = api
    uid = uuid4()
    with SessionLocal() as db:
        db.add(Profile(id=uid, papel="student", nome_completo="Ana"))
        db.add(
            Syllabus(
                user_id=uid,
                file_name="dual.pdf",
                file_path=f"syllabus_files/{uid}/primary.pdf",
                arquivo_url=f"syllabus_files/{uid}/secondary.pdf",
                status="concluido",
            )
        )
        db.commit()

    storage = SupabaseStorageService(supabase_url="https://storage.test", supabase_key="srv-key")
    called_deletes: list[str] = []
    fail_secondary = {"value": True}

    def fake_delete(url, **kwargs):
        called_deletes.append(url)
        if fail_secondary["value"] and url.endswith("/secondary.pdf"):
            return httpx.Response(503)
        if not fail_secondary["value"] and url.endswith("/primary.pdf"):
            return httpx.Response(404)
        return httpx.Response(204)

    monkeypatch.setattr(httpx, "delete", fake_delete)

    with SessionLocal() as db:
        first_run = discard_legacy_pdfs(db, storage, execute=True)
        assert first_run == {"dry_run": False, "eligible": 1, "discarded": 0, "failed": 1}
        assert called_deletes == [
            f"https://storage.test/storage/v1/object/syllabus_files/{uid}/primary.pdf",
            f"https://storage.test/storage/v1/object/syllabus_files/{uid}/secondary.pdf",
        ]
        row = db.query(Syllabus).filter_by(file_name="dual.pdf").one()
        assert row.file_path == f"syllabus_files/{uid}/primary.pdf"
        assert row.arquivo_url == f"syllabus_files/{uid}/secondary.pdf"
        assert row.discarded_at is None

        fail_secondary["value"] = False
        called_deletes.clear()
        retry_run = discard_legacy_pdfs(db, storage, execute=True)
        assert retry_run == {"dry_run": False, "eligible": 1, "discarded": 1, "failed": 0}
        assert called_deletes == [
            f"https://storage.test/storage/v1/object/syllabus_files/{uid}/primary.pdf",
            f"https://storage.test/storage/v1/object/syllabus_files/{uid}/secondary.pdf",
        ]
        db.refresh(row)
        assert row.file_path is None
        assert row.arquivo_url is None
        assert row.discarded_at is not None


def test_record_legal_acceptance_handles_concurrent_duplicate_insert(api, monkeypatch):
    client, SessionLocal, auth_state, _ = api
    user = _make_user()
    auth_state["value"] = user
    _seed_profile(SessionLocal, user)
    version = account_repository.CURRENT_LEGAL_VERSIONS["terms"]

    with SessionLocal() as db:
        db.add(TermAcceptance(user_id=user.id, document="terms", version=version))
        db.commit()

    # Simula corrida: db.get retorna None na segunda requisição, mas o INSERT colide na PK.
    with SessionLocal() as db:
        monkeypatch.setattr(db, "get", lambda *args, **kwargs: None)
        account_repository.record_legal_acceptance(db, user.id, "terms", version)
        db.commit()

    status_res = client.get("/api/v1/me/legal-documents")
    assert status_res.status_code == 200
    assert status_res.json()["terms"]["pending"] is False


def test_sqlite_deletion_nullifies_public_event_moderation_and_duplicate_refs(api):
    client, SessionLocal, auth_state, _ = api
    ana = _make_user(role="admin", email="ana.mod@unb.br")
    bruno = _make_user(role="admin", email="bruno.autor@unb.br")
    auth_state["value"] = ana

    with SessionLocal() as db:
        db.add_all([
            Profile(id=ana.id, papel="admin", nome_completo="Ana Mod"),
            Profile(id=bruno.id, papel="admin", nome_completo="Bruno Autor"),
        ])
        ev_ana = PublicEvent(
            author_id=ana.id,
            title="Evento original Ana",
            description="Descrição",
            status="aprovado",
        )
        db.add(ev_ana)
        db.flush()
        ev_bruno = PublicEvent(
            author_id=bruno.id,
            title="Evento Bruno",
            description="Descrição",
            status="aprovado",
            moderated_by=ana.id,
            possible_duplicate_of=ev_ana.id,
        )
        db.add(ev_bruno)
        db.commit()
        ev_bruno_id = ev_bruno.id

    class FakeAuthAdmin(account_service.SupabaseAuthAdminClient):
        def delete_user(self, user_id: UUID) -> None:
            pass

    app.dependency_overrides[account_service.get_auth_admin_client] = lambda: FakeAuthAdmin()
    res = client.request("DELETE", "/api/v1/me", json={"confirmation": "EXCLUIR MINHA CONTA"})
    assert res.status_code == 204

    with SessionLocal() as db:
        remaining = db.get(PublicEvent, ev_bruno_id)
        assert remaining is not None
        assert remaining.moderated_by is None
        assert remaining.possible_duplicate_of is None


def test_database_errors_are_logged_without_row_content(api, monkeypatch, caplog):
    client, SessionLocal, auth_state, _ = api
    user = _make_user()
    auth_state["value"] = user
    _seed_profile(SessionLocal, user)

    def raise_sql(*args, **kwargs):
        raise SQLAlchemyError(f"CONTEUDO_ACADEMICO_SECRETO user_id={user.id}")

    monkeypatch.setattr(account_service, "export_user_data", raise_sql)
    with caplog.at_level(logging.INFO):
        res = client.get("/api/v1/me/data-export")
    assert res.status_code == 503
    assert "CONTEUDO_ACADEMICO_SECRETO" not in caplog.text
    assert str(user.id) not in caplog.text


def test_unhandled_exception_returns_500_without_leaking_secrets(api, monkeypatch, caplog):
    _, SessionLocal, auth_state, _ = api
    user = _make_user()
    auth_state["value"] = user
    _seed_profile(SessionLocal, user)

    def raise_unexpected(*args, **kwargs):
        raise RuntimeError("TOKEN_SECRETO_123 texto academico confidencial")

    monkeypatch.setattr(account_service, "get_legal_documents", raise_unexpected)
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        with caplog.at_level(logging.INFO):
            res = safe_client.get("/api/v1/me/legal-documents")
    assert res.status_code == 500
    assert res.json() == {"detail": "Erro interno inesperado. Tente novamente."}
    assert "TOKEN_SECRETO_123" not in caplog.text
    assert "texto academico confidencial" not in caplog.text
    assert "Traceback" not in caplog.text


def test_supabase_admin_calls_never_log_identifiers(api, monkeypatch, caplog):
    client, SessionLocal, auth_state, _ = api
    user = _make_user(email="sigilosa@unb.br")
    auth_state["value"] = user
    secret_key = "service-role-super-secret-key"

    with SessionLocal() as db:
        db.add(Profile(id=user.id, papel="student", nome_completo="Sigilosa"))
        db.add(
            PersonalEvent(
                user_id=user.id,
                title="Conteúdo acadêmico confidencial",
                starts_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            Syllabus(
                user_id=user.id,
                file_name="legacy_segredo.pdf",
                file_path=f"syllabus_files/{user.id}/legacy_segredo.pdf",
                status="concluido",
            )
        )
        db.commit()

    storage = SupabaseStorageService(supabase_url="https://supabase.test", supabase_key=secret_key)
    auth_admin = account_service.SupabaseAuthAdminClient(
        supabase_url="https://supabase.test",
        service_role_key=secret_key,
    )
    app.dependency_overrides[get_storage_service] = lambda: storage
    app.dependency_overrides[account_service.get_auth_admin_client] = lambda: auth_admin

    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: httpx.Response(200, json=[]))
    monkeypatch.setattr(httpx, "delete", lambda *args, **kwargs: httpx.Response(503))

    with caplog.at_level(logging.INFO):
        assert client.get("/api/v1/me/data-export").status_code == 200
        assert client.request("DELETE", "/api/v1/me", json={"confirmation": "EXCLUIR MINHA CONTA"}).status_code == 503
        with SessionLocal() as db:
            discard_legacy_pdfs(db, storage, execute=True)

        # Exercita também falha no Auth Admin para garantir que user.id e chave não vazem.
        monkeypatch.setattr(httpx, "delete", lambda url, **kwargs: httpx.Response(502 if "/auth/v1/admin/" in url else 204))
        assert client.request("DELETE", "/api/v1/me", json={"confirmation": "EXCLUIR MINHA CONTA"}).status_code == 502

    for sensitive in (
        secret_key,
        user.access_token,
        str(user.id),
        user.email,
        "legacy_segredo.pdf",
        "Conteúdo acadêmico confidencial",
    ):
        assert sensitive not in caplog.text
