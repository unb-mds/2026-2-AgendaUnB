"""Direitos do titular: documentos legais, exportação e exclusão (S8-D01, #83)."""
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.account import repository
from src.modules.account.services import SupabaseAccountAdmin, get_account_admin

router = APIRouter(prefix="/me", tags=["account"])

DOCUMENTS = {"terms": "termos_de_uso", "privacy": "politica_de_privacidade"}
DELETE_CONFIRMATION = "EXCLUIR MINHA CONTA"
STATUS_BY_SQLSTATE = {"P0002": 404, "55000": 409, "22023": 422, "42501": 403}


def _translate(exc: DBAPIError) -> HTTPException | None:
    status = STATUS_BY_SQLSTATE.get(getattr(exc.orig, "sqlstate", None))
    if status is None:
        return None
    return HTTPException(status_code=status, detail=str(exc.orig).splitlines()[0])


class LegalDocumentStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    document: Literal["terms", "privacy"]
    current_version: str = Field(alias="currentVersion")
    accepted_version: str | None = Field(alias="acceptedVersion")
    pending: bool


class LegalAcceptanceRequest(BaseModel):
    version: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")


class DeleteAccountRequest(BaseModel):
    confirmation: str


@router.get(
    "/legal-documents",
    response_model=list[LegalDocumentStatus],
    response_model_by_alias=True,
    summary="Versões vigentes dos documentos legais e o que a conta já aceitou",
)
def list_legal_documents(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LegalDocumentStatus]:
    accepted = repository.list_acceptances(db, current_user.id)
    return [
        LegalDocumentStatus(
            document=name,
            current_version=repository.CURRENT_LEGAL_VERSIONS[stored],
            accepted_version=accepted.get(stored),
            pending=accepted.get(stored) != repository.CURRENT_LEGAL_VERSIONS[stored],
        )
        for name, stored in DOCUMENTS.items()
    ]


@router.put(
    "/legal-acceptances/{document}",
    status_code=204,
    summary="Registra que a conta leu a versão vigente do documento",
)
def accept_legal_document(
    document: Literal["terms", "privacy"],
    payload: LegalAcceptanceRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    stored = DOCUMENTS[document]
    # Só a versão vigente pode ser aceita: evita registrar aceite de um texto
    # que a pessoa não viu.
    if payload.version != repository.CURRENT_LEGAL_VERSIONS[stored]:
        raise HTTPException(status_code=409, detail="O documento foi atualizado. Recarregue e leia a versão vigente.")
    repository.accept_document(db, current_user.id, stored, payload.version)
    return Response(status_code=204)


@router.get("/data-export", summary="Exporta os dados que a plataforma guarda sobre a conta")
def export_my_data(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> JSONResponse:
    try:
        data = repository.export_account(db, current_user.id)
    except DBAPIError as exc:
        db.rollback()
        raise _translate(exc) or exc
    filename = f"agenda-unb-meus-dados-{datetime.now(timezone.utc):%Y%m%d}.json"
    return JSONResponse(
        content=data,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.delete("", status_code=204, summary="Exclui a conta e os dados associados")
def delete_my_account(
    payload: DeleteAccountRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    admin: SupabaseAccountAdmin = Depends(get_account_admin),
) -> Response:
    if payload.confirmation != DELETE_CONFIRMATION:
        raise HTTPException(status_code=422, detail=f'Digite "{DELETE_CONFIRMATION}" para confirmar.')

    try:
        plan = repository.prepare_deletion(db, current_user.id)
    except DBAPIError as exc:
        db.rollback()
        raise _translate(exc) or exc

    # Ordem: arquivos primeiro, conta depois. Se algo falhar, a conta ainda
    # existe e a pessoa pode repetir o pedido; nunca sobra arquivo sem dono.
    admin.delete_files(plan["arquivos"])
    admin.delete_user(current_user.id)
    repository.finish_deletion(db, plan["registro_id"])
    return Response(status_code=204)
