from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EventCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=3, max_length=150)
    description: str | None = None
    campus: str = Field(min_length=2, max_length=80)
    category: str = Field(min_length=2, max_length=80)
    location: str | None = Field(default=None, max_length=150)
    start_at: datetime
    end_at: datetime

    @model_validator(mode="after")
    def validate_dates(self):
        if self.end_at <= self.start_at:
            raise ValueError("A data final deve ser posterior à data inicial")
        return self


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    campus: str
    category: str
    location: str | None
    start_at: datetime
    end_at: datetime

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Informe data e hora com fuso horário (ISO 8601)")
        return value
