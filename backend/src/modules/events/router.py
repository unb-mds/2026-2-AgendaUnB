from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import Event
from src.modules.events.schemas import EventRead

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
def list_events(
    campus: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    category: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    start_date: Annotated[datetime | None, Query(alias="startDate")] = None,
    end_date: Annotated[datetime | None, Query(alias="endDate")] = None,
    db: Session = Depends(get_db),
) -> list[EventRead]:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="startDate deve ser anterior ou igual a endDate",
        )

    statement: Select[tuple[Event]] = select(Event)
    if campus:
        statement = statement.where(Event.campus == campus)
    if category:
        statement = statement.where(Event.category == category)
    if start_date:
        statement = statement.where(Event.end_at >= start_date)
    if end_date:
        statement = statement.where(Event.start_at <= end_date)

    statement = statement.order_by(Event.start_at.asc())
    return list(db.scalars(statement).all())


@router.get("/{event_id}", response_model=EventRead)
def get_event(
    event_id: Annotated[int, Path(gt=0)],
    db: Session = Depends(get_db),
) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    return event
