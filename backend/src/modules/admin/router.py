from fastapi import APIRouter, Depends
from src.middlewares.auth import require_admin

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

from uuid import UUID
from datetime import datetime
from fastapi import Query, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from src.database.connection import get_db
from src.database.models import PublicEvent

class AdminEvent(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    title: str
    description: str
    starts_at: datetime
    status: str
    author_id: UUID

@router.get("/events/pending", response_model=list[AdminEvent])
def pending(db: Session = Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    return db.scalars(select(PublicEvent).where(PublicEvent.status == "pendente").order_by(PublicEvent.created_at, PublicEvent.id).offset(offset).limit(limit)).all()

from typing import Literal
from pydantic import Field
import logging
from src.middlewares.auth import CurrentUser

logger = logging.getLogger("agenda_unb.admin")

class ReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: Literal["aprovado", "rejeitado"]
    justificativa_recusa: str | None = Field(None, max_length=2000)

class ReviewResult(BaseModel):
    id: UUID
    status: str
    justificativa_recusa: str | None

@router.patch("/events/{id}/review", response_model=ReviewResult)
def review(id: UUID, body: ReviewInput, db: Session = Depends(get_db), actor: CurrentUser = Depends(require_admin)):
    if body.status == "rejeitado" and not body.justificativa_recusa:
        raise HTTPException(422, "Informe a justificativa da recusa")
    reason = body.justificativa_recusa if body.status == "rejeitado" else None
    result = db.execute(update(PublicEvent).where(PublicEvent.id == id, PublicEvent.status == "pendente").values(status=body.status, justificativa_recusa=reason))
    if result.rowcount != 1:
        exists = db.scalar(select(PublicEvent.id).where(PublicEvent.id == id))
        raise HTTPException(409 if exists else 404, "Evento ja revisado" if exists else "Evento inexistente")
    db.commit()
    logger.info("review actor=%s target=%s status=%s result=success", actor.id, id, body.status)
    return ReviewResult(id=id, status=body.status, justificativa_recusa=reason)

from sqlalchemy import text

class AdminUser(BaseModel):
    id: UUID
    email: str | None
    nome_completo: str | None
    papel: Literal["student", "professor", "admin"]
    criado_em: datetime
    ultimo_login: datetime | None
    email_confirmado: bool

class UsersPage(BaseModel):
    items: list[AdminUser]
    total: int
    all: int
    unconfirmed: int

@router.get("/users", response_model=UsersPage)
def users(busca: str = Query("", max_length=200), papel: Literal["", "student", "professor", "admin"] = "", confirmado: Literal["", "sim", "nao"] = "", offset: int = Query(0, ge=0), db: Session = Depends(get_db), actor: CurrentUser = Depends(require_admin)):
    # Transaction-local identity for the existing security-definer RPC.
    db.execute(text("select set_config('request.jwt.claim.sub', :actor, true)"), {"actor": str(actor.id)})
    return db.execute(text("select public.admin_buscar_usuarios(:busca, :papel, :confirmado, :offset)"), {"busca": busca, "papel": papel, "confirmado": confirmado, "offset": offset}).scalar_one()
