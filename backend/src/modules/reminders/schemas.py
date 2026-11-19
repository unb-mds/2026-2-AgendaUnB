from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class ReminderRead(BaseModel):
    id: UUID
    event_kind: Literal["personal", "saved_public"]
    event_id: UUID
    title: str | None
    starts_at: datetime
    scheduled_at: datetime
    read_at: datetime | None


class ReminderReadStatus(BaseModel):
    id: UUID
    read_at: datetime
