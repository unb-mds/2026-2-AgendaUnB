from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

BRASILIA_TZ = timezone(timedelta(hours=-3))


def _require_tz(value: datetime | None, label: str) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{label} deve incluir fuso horário (ISO 8601)")
    return value


class EventInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    all_day: bool = False
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    start_date: date | None = None
    end_date: date | None = None
    campus: str | None = Field(default=None, min_length=2, max_length=120)
    category: str | None = Field(default=None, min_length=2, max_length=80)
    location: str | None = Field(default=None, max_length=250)

    @field_validator("campus", "category", "location", "description", mode="before")
    @classmethod
    def empty_str_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("starts_at")
    @classmethod
    def require_starts_at_timezone(cls, value: datetime | None) -> datetime | None:
        return _require_tz(value, "Informe data e hora")

    @field_validator("ends_at")
    @classmethod
    def require_ends_at_timezone(cls, value: datetime | None) -> datetime | None:
        return _require_tz(value, "Horário de término")

    @model_validator(mode="after")
    def validate_date_mode(self) -> "EventInput":
        if self.all_day:
            if self.starts_at is not None or self.ends_at is not None:
                raise ValueError(
                    "Eventos de dia inteiro devem informar start_date e end_date, sem starts_at ou ends_at"
                )
            if self.start_date is None:
                raise ValueError("Informe a data inicial (start_date) para evento de dia inteiro")
            if self.end_date is None:
                self.end_date = self.start_date + timedelta(days=1)
            elif self.end_date <= self.start_date:
                raise ValueError("A data final (end_date exclusivo) deve ser posterior à data inicial")
            self.starts_at = datetime.combine(self.start_date, time.min, tzinfo=BRASILIA_TZ)
            self.ends_at = datetime.combine(self.end_date, time.min, tzinfo=BRASILIA_TZ)
        else:
            if self.start_date is not None or self.end_date is not None:
                raise ValueError(
                    "Eventos com horário devem informar starts_at (e ends_at opcional), sem start_date ou end_date"
                )
            if self.starts_at is None:
                raise ValueError("Informe data e hora com fuso horário (ISO 8601)")
            if self.ends_at is not None and self.ends_at <= self.starts_at:
                raise ValueError("O horário de término deve ser posterior ao início")
        return self


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
    ends_at: datetime | None = None
    all_day: bool = False
    start_date: date | None = None
    end_date: date | None = None
    campus: str | None
    category: str | None
    location: str | None
    external_url: str | None = None
    organizer_name: str | None = None
    organizer_avatar: str | None = None
    source: str | None = None
    source_url: str | None = None


class SavedEventStatus(BaseModel):
    saved: bool


class PersonalEventOriginRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    syllabus_id: UUID = Field(alias="syllabusId")
    candidate_id: UUID = Field(alias="candidateId")
    page: int | None = None
    excerpt: str | None = None


class PersonalEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    starts_at: datetime
    ends_at: datetime | None = None
    all_day: bool = False
    start_date: date | None = None
    end_date: date | None = None
    campus: str | None
    category: str | None
    location: str | None = None
    origin: PersonalEventOriginRead | None = None


class PersonalEventCreate(EventInput):
    pass


class PersonalEventUpdate(EventInput):
    pass
