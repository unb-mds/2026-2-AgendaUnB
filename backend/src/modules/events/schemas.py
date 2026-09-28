from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class EventInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    starts_at: datetime
    campus: str | None = Field(default=None, min_length=2, max_length=120)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    location: str | None = Field(default=None, max_length=250)

    @field_validator("starts_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Informe data e hora com fuso horário (ISO 8601)")
        return value


class EventCreate(EventInput):
    external_url: HttpUrl | None = None


class EventUpdate(EventInput):
    external_url: HttpUrl | None = None


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    starts_at: datetime
    campus: str | None
    category: str | None
    location: str | None
    external_url: str | None = None
    organizer_name: str | None = None
    organizer_avatar: str | None = None


class PersonalEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    starts_at: datetime
    campus: str | None
    category: str | None
    location: str | None = None


class PersonalEventCreate(EventInput):
    pass


class PersonalEventUpdate(EventInput):
    pass
