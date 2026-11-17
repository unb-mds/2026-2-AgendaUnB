from datetime import date, datetime, time
from uuid import UUID
from pydantic import BaseModel, Field


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
    type: str | None = None
    starts_at: datetime | None = None
    suggested_date: date | None = None
    suggested_time: time | None = None
    ambiguous: bool
    ambiguous_fields: list[str] = Field(default_factory=list)
    source_page: int | None = None
    source_excerpt: str | None = None
    order: int | None = None
    imported: bool = False
    modified_since_import: bool = False
    confirm_count: int = 0
    contest_count: int = 0
    my_vote: str | None = None


class SharedPlanRead(BaseModel):
    id: UUID
    syllabus_id: UUID
    offering_id: UUID | None = None
    number: int
    author_id: UUID
    author_name: str | None = None
    author_role: str
    source_version_id: UUID | None = None
    source_version_number: int | None = None
    institutional_provenance: bool
    institutional_source_url: str | None = None
    created_at: datetime | None = None
    shared_at: datetime | None = None
    updated_at: datetime | None = None
    confirm_count: int = 0
    contest_count: int = 0
    my_vote: str | None = None
    is_default: bool = False
    can_withdraw: bool = False
    can_edit: bool = True
    has_imported_update: bool = False
    imported_from_version_number: int | None = None
    candidates: list[SharedCandidateRead]


class SharedPlanList(BaseModel):
    items: list[SharedPlanRead]
    total: int
    limit: int
    offset: int
