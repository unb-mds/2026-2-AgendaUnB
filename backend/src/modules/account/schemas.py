from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

LegalDocumentKey = Literal["terms", "privacy"]
ConsentPurpose = Literal["google_agenda"]


class LegalDocumentStatus(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    current_version: str = Field(alias="currentVersion")
    accepted_version: str | None = Field(default=None, alias="acceptedVersion")
    accepted_at: datetime | None = Field(default=None, alias="acceptedAt")
    pending: bool


class LegalDocumentsResponse(BaseModel):
    terms: LegalDocumentStatus
    privacy: LegalDocumentStatus


class LegalAcceptanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    version: str = Field(min_length=4, max_length=32)


class ConsentRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    purpose: str
    active: bool
    granted_at: datetime = Field(alias="grantedAt")
    revoked_at: datetime | None = Field(default=None, alias="revokedAt")
    reference_id: UUID | None = Field(default=None, alias="referenceId")


class ConsentsResponse(BaseModel):
    items: list[ConsentRead]


class AccountDeleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    confirmation: str = Field(min_length=1, max_length=64)


class DataExportResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    exported_at: datetime = Field(alias="exportedAt")
    profile: dict[str, Any]
    personal_events: list[dict[str, Any]] = Field(alias="personalEvents")
    saved_events: list[dict[str, Any]] = Field(alias="savedEvents")
    public_events: list[dict[str, Any]] = Field(alias="publicEvents")
    followed_classes: list[dict[str, Any]] = Field(alias="followedClasses")
    syllabi: list[dict[str, Any]]
    authored_plan_versions: list[dict[str, Any]] = Field(alias="authoredPlanVersions")
    import_operations: list[dict[str, Any]] = Field(alias="importOperations")
    votes: list[dict[str, Any]]
    notifications: list[dict[str, Any]]
    reminders: list[dict[str, Any]]
    legal_acceptances: list[dict[str, Any]] = Field(alias="legalAcceptances")
    consents: list[dict[str, Any]]
    google_calendar: dict[str, Any] | None = Field(default=None, alias="googleCalendar")
    google_calendar_exports: list[dict[str, Any]] = Field(alias="googleCalendarExports")
