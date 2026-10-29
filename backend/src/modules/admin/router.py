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
