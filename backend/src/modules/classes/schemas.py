from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel


class OfferingRead(BaseModel):
    id: UUID
    subject_name: str
    subject_code: str
    class_number: str
    year: int
    semester: int
    unit_name: str | None = None
    unit_code: str | None = None
    unit: str | None
    level: str | None
    teacher: str | None
    schedule: str | None
    available: bool


class CatalogMetadata(BaseModel):
    source_updated_at: datetime
    stale: bool


class OfferingList(CatalogMetadata):
    items: list[OfferingRead]
    total: int
    limit: int
    offset: int


class UnitRead(BaseModel):
    id: int
    code: str | None
    name: str


class CatalogFilters(CatalogMetadata):
    units: list[UnitRead]
    periods: list[str]


class FollowedList(BaseModel):
    items: list[OfferingRead]


class SharedCandidateRead(BaseModel):
    id: UUID
    title: str
    starts_at: datetime | None
    suggested_date: date | None
    ambiguous: bool


class SharedPlanRead(BaseModel):
    id: UUID
    number: int
    author_role: str
    institutional_provenance: bool
    shared_at: datetime | None
    candidates: list[SharedCandidateRead]


class SharedPlanList(BaseModel):
    items: list[SharedPlanRead]
    total: int
    limit: int
    offset: int
