from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.account import service
from src.modules.account.schemas import (
    AccountDeleteRequest,
    ConsentPurpose,
    ConsentsResponse,
    DataExportResponse,
    LegalAcceptanceInput,
    LegalDocumentKey,
    LegalDocumentsResponse,
)
from src.services.storage import SupabaseStorageService, get_storage_service

router = APIRouter(prefix="/me", tags=["account"])


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


@router.get("/legal-documents", response_model=LegalDocumentsResponse)
def get_legal_documents(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LegalDocumentsResponse:
    _no_store(response)
    return service.get_legal_documents(db, user)


@router.put("/legal-acceptances/{document}", status_code=status.HTTP_204_NO_CONTENT)
def accept_legal_document(
    document: LegalDocumentKey,
    payload: LegalAcceptanceInput,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service.accept_legal_document(db, user, document, payload)
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.get("/consents", response_model=ConsentsResponse)
def get_consents(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConsentsResponse:
    _no_store(response)
    return service.get_consents(db, user)


@router.delete("/consents/{purpose}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_consent(
    purpose: ConsentPurpose,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    service.revoke_consent(db, user, purpose)
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )


@router.get("/data-export", response_model=DataExportResponse)
def export_my_data(
    response: Response,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DataExportResponse:
    _no_store(response)
    response.headers["Content-Disposition"] = 'attachment; filename="agenda-unb-dados.json"'
    return DataExportResponse(**service.export_user_data(db, user))


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    payload: AccountDeleteRequest,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: SupabaseStorageService = Depends(get_storage_service),
    auth_admin: service.SupabaseAuthAdminClient = Depends(service.get_auth_admin_client),
) -> Response:
    service.delete_account(db, user, payload, storage, auth_admin)
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"Cache-Control": "no-store", "Pragma": "no-cache"},
    )
