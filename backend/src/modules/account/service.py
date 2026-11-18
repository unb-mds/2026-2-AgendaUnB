import logging
import os
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.middlewares.auth import CurrentUser
from src.modules.account import repository
from src.modules.account.schemas import (
    AccountDeleteRequest,
    ConsentRead,
    ConsentsResponse,
    LegalAcceptanceInput,
    LegalDocumentsResponse,
    LegalDocumentStatus,
)
from src.modules.google_calendar import service as google_calendar_service
from src.services.storage import SupabaseStorageService

logger = logging.getLogger("agenda_unb.account")


class SupabaseAuthAdminClient:
    """Executa exclusão administrativa de contas no Supabase Auth sem expor identificadores em logs."""

    def __init__(
        self,
        supabase_url: str | None = None,
        service_role_key: str | None = None,
    ):
        self.supabase_url = (
            supabase_url if supabase_url is not None else os.getenv("SUPABASE_URL", "")
        ).rstrip("/")
        self.service_role_key = (
            service_role_key if service_role_key is not None else os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        )

    def delete_user(self, user_id: UUID) -> None:
        if not self.supabase_url or not self.service_role_key:
            raise HTTPException(
                status_code=503,
                detail="Serviço de autenticação não configurado no backend.",
            )
        url = f"{self.supabase_url}/auth/v1/admin/users/{user_id}"
        headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
        }
        try:
            response = httpx.delete(url, headers=headers, timeout=10.0)
        except httpx.RequestError as exc:
            logger.warning("Falha de conexão no Auth Admin (%s).", type(exc).__name__)
            raise HTTPException(
                status_code=503,
                detail="O serviço de autenticação está indisponível no momento.",
            ) from exc

        if response.status_code in (200, 204, 404):
            return
        logger.warning("Auth Admin recusou exclusão de conta (HTTP %s).", response.status_code)
        raise HTTPException(
            status_code=502,
            detail="Não foi possível concluir a exclusão da conta.",
        )


def get_auth_admin_client() -> SupabaseAuthAdminClient:
    return SupabaseAuthAdminClient()


def get_legal_documents(db: Session, user: CurrentUser) -> LegalDocumentsResponse:
    acceptances = repository.get_legal_acceptances(db, user.id)
    statuses: dict[str, LegalDocumentStatus] = {}
    for document, current_version in repository.CURRENT_LEGAL_VERSIONS.items():
        latest = acceptances.get(document)
        accepted_version = latest.version if latest else None
        accepted_at = latest.accepted_at if latest else None
        statuses[document] = LegalDocumentStatus(
            current_version=current_version,
            accepted_version=accepted_version,
            accepted_at=accepted_at,
            pending=(accepted_version != current_version),
        )
    return LegalDocumentsResponse(terms=statuses["terms"], privacy=statuses["privacy"])


def accept_legal_document(
    db: Session,
    user: CurrentUser,
    document: str,
    payload: LegalAcceptanceInput,
) -> None:
    current_version = repository.CURRENT_LEGAL_VERSIONS[document]
    if payload.version != current_version:
        raise HTTPException(
            status_code=409,
            detail="A versão informada não corresponde ao documento vigente.",
        )
    repository.record_legal_acceptance(db, user.id, document, payload.version)
    db.commit()


def get_consents(db: Session, user: CurrentUser) -> ConsentsResponse:
    rows = repository.list_consents(db, user.id)
    items = [
        ConsentRead(
            id=row.id,
            purpose=row.purpose,
            active=row.revoked_at is None,
            granted_at=row.granted_at,
            revoked_at=row.revoked_at,
            reference_id=row.reference_id,
        )
        for row in rows
    ]
    return ConsentsResponse(items=items)


def revoke_consent(db: Session, user: CurrentUser, purpose: str) -> None:
    if purpose == "google_agenda":
        google_calendar_service.disconnect(db, user)
    repository.revoke_active_consents(db, user.id, purpose)
    db.commit()


def export_user_data(db: Session, user: CurrentUser) -> dict:
    return repository.collect_user_export_data(db, user)


def delete_account(
    db: Session,
    user: CurrentUser,
    payload: AccountDeleteRequest,
    storage: SupabaseStorageService,
    auth_admin: SupabaseAuthAdminClient,
) -> None:
    if payload.confirmation != repository.CONFIRMATION_PHRASE:
        raise HTTPException(
            status_code=422,
            detail="Digite exatamente 'EXCLUIR MINHA CONTA' para confirmar a exclusão.",
        )

    deletion_id, db_paths = repository.prepare_account_deletion(db, user.id)

    # Revoga tokens e consentimentos externos enquanto os registros locais ainda existem.
    google_calendar_service.disconnect(db, user)

    # Remove todos os objetos no Storage antes de remover o usuário no Auth.
    listed_paths = storage.list_prefix(f"{user.id}/")
    removed_files = storage.delete_objects_strict([*db_paths, *listed_paths])

    auth_admin.delete_user(user.id)

    repository.complete_account_deletion(
        db,
        deletion_id,
        user_id=user.id,
        removed_storage_files=removed_files,
    )
