from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session

from src.database.connection import get_db
from src.database.models import PersonalEvent, PublicEvent, Reminder
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.reminders.schemas import ReminderRead, ReminderReadStatus

router = APIRouter(prefix="/me/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderRead])
def list_reminders(
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0, le=2_147_483_647)] = 0,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReminderRead]:
    reminders = db.execute(
        select(Reminder, func.coalesce(PersonalEvent.title, PublicEvent.title))
        .outerjoin(PersonalEvent, and_(
            PersonalEvent.id == Reminder.personal_event_id,
            PersonalEvent.user_id == current_user.id,
        ))
        .outerjoin(PublicEvent, and_(
            PublicEvent.id == Reminder.public_event_id,
            PublicEvent.status == "aprovado",
        ))
        .where(Reminder.user_id == current_user.id, Reminder.status == "disparado")
        .order_by(Reminder.fired_at.desc(), Reminder.id.desc())
        .limit(limit)
        .offset(offset)
    )
    response.headers["Cache-Control"] = "no-store"
    return [
        ReminderRead(
            id=reminder.id,
            event_kind="personal" if reminder.event_kind == "pessoal" else "saved_public",
            event_id=reminder.personal_event_id or reminder.public_event_id,
            title=title,
            starts_at=reminder.event_starts_at,
            scheduled_at=reminder.scheduled_for,
            read_at=reminder.read_at,
        )
        for reminder, title in reminders
    ]


@router.put("/{reminder_id}/read", response_model=ReminderReadStatus)
def mark_reminder_read(
    reminder_id: UUID,
    response: Response,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReminderReadStatus:
    read_at = db.scalar(
        update(Reminder)
        .where(
            Reminder.id == reminder_id,
            Reminder.user_id == current_user.id,
            Reminder.status == "disparado",
        )
        .values(read_at=func.coalesce(Reminder.read_at, func.now()))
        .returning(Reminder.read_at)
    )
    if read_at is None:
        raise HTTPException(status_code=404, detail="Lembrete não encontrado")
    db.commit()
    response.headers["Cache-Control"] = "no-store"
    return ReminderReadStatus(id=reminder_id, read_at=read_at)
