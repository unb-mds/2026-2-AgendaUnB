from datetime import date, datetime, time
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.modules.events.schemas import PersonalEventRead


class SyllabusUploadResponse(BaseModel):
    """Schema de resposta após upload bem-sucedido de plano de ensino."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: UUID
    offering_id: UUID | None = Field(default=None, alias="offeringId")
    user_id: UUID = Field(alias="userId")
    file_name: str = Field(alias="fileName")
    file_path: str | None = Field(default=None, alias="filePath")
    file_size: int | None = Field(default=None, alias="fileSize")
    file_type: str = Field(default="pdf", alias="fileType")
    status: str = Field(default="pendente")
    ano: int | None = None
    semestre: int | None = None
    created_at: datetime = Field(alias="createdAt")
    authorization_required: bool = Field(default=True, alias="authorizationRequired")
    prepared_text_available: bool = Field(default=False, alias="preparedTextAvailable")
    message: str = "Texto preparado. Revise e autorize o trecho antes de enviar ao Gemini."


class SyllabusListItem(BaseModel):
    """Dados do plano no histórico, inclusive de planos anteriores ao upload."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: UUID
    offering_id: UUID | None = Field(default=None, alias="offeringId")
    user_id: UUID = Field(alias="userId")
    file_name: str | None = Field(alias="fileName")
    file_path: str | None = Field(alias="filePath")
    file_size: int | None = Field(default=None, alias="fileSize")
    file_type: str = Field(default="pdf", alias="fileType")
    status: str

    authorization_required: bool = Field(default=False, alias="authorizationRequired")
    prepared_text_available: bool = Field(default=False, alias="preparedTextAvailable")
    extracted_events_count: int = Field(default=0, alias="extractedEventsCount")
    error_message: str | None = Field(default=None, alias="errorMessage")
    error_code: str | None = Field(default=None, alias="errorCode")
    page_count: int | None = Field(default=None, alias="pageCount")
    attempts: int = 0
    processing_started_at: datetime | None = Field(default=None, alias="processingStartedAt")
    processed_at: datetime | None = Field(default=None, alias="processedAt")
    processing_duration_ms: int | None = Field(default=None, alias="processingDurationMs")
    total_duration_ms: int | None = Field(default=None, alias="totalDurationMs")
    disciplina: str | None = None
    turma: str | None = None
    ano: int | None = None
    semestre: int | None = None
    created_at: datetime = Field(alias="createdAt")


class SyllabusCandidateRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    title: str
    kind: str | None = Field(default=None, alias="type")
    starts_at: datetime | None = Field(default=None, alias="startsAt")
    ambiguous: bool
    source_page: int | None = Field(default=None, alias="sourcePage")
    source_excerpt: str | None = Field(default=None, alias="sourceExcerpt")
    status: str

    suggested_date: date | None = Field(default=None, alias="suggestedDate")
    suggested_time: time | None = Field(default=None, alias="suggestedTime")
    ambiguous_fields: list[str] = Field(default_factory=list, alias="ambiguousFields")
    version_id: UUID | None = Field(default=None, alias="versionId")
    confirm_count: int = Field(default=0, alias="confirmCount")
    contest_count: int = Field(default=0, alias="contestCount")
    divergent: bool = False
    my_vote: str | None = Field(default=None, alias="myVote")



class SyllabusDetailResponse(SyllabusListItem):
    candidates: list[SyllabusCandidateRead] = Field(default_factory=list)
    authorization_required: bool = Field(default=True, alias="authorizationRequired")
    preparation_duration_ms: int | None = Field(default=None, alias="preparationDurationMs")
    review_duration_ms: int | None = Field(default=None, alias="reviewDurationMs")


class SyllabusListResponse(BaseModel):
    items: list[SyllabusListItem]
    total: int
    limit: int
    offset: int


class ConfirmCandidateInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    candidate_id: UUID = Field(alias="candidateId")
    title: str | None = Field(default=None, min_length=3, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    kind: str | None = Field(default=None, min_length=2, max_length=80, alias="type")
    starts_at: datetime | None = Field(default=None, alias="startsAt")
    all_day: bool = Field(default=False, alias="allDay")
    start_date: date | None = None
    end_date: date | None = None
    category: str | None = Field(default=None, min_length=2, max_length=80)

    @field_validator("starts_at")
    @classmethod
    def require_explicit_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Informe data e hora com fuso horário (ISO 8601)")
        return value

    @field_validator("description", "category", "kind", mode="before")
    @classmethod
    def empty_values_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def validate_all_day_dates(self):
        if self.all_day:
            if self.starts_at is not None:
                raise ValueError("Evento de dia inteiro não aceita startsAt.")
            if self.start_date is None:
                raise ValueError("Evento de dia inteiro exige start_date.")
            if self.end_date is not None and self.end_date <= self.start_date:
                raise ValueError("end_date deve ser posterior a start_date.")
        elif self.start_date is not None or self.end_date is not None:
            raise ValueError("start_date e end_date exigem all_day=true.")
        return self


class ConfirmSyllabusRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version_id: UUID | None = Field(default=None, alias="versionId")
    candidates: list[ConfirmCandidateInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def candidate_ids_must_be_unique(self):
        ids = [candidate.candidate_id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("Não repita o mesmo candidato na confirmação")
        return self


class RevisionCandidateInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    candidate_id: UUID | None = Field(default=None, alias="candidateId")
    title: str = Field(min_length=3, max_length=200)
    kind: str | None = Field(default=None, min_length=2, max_length=80, alias="type")
    starts_at: datetime | None = Field(default=None, alias="startsAt")
    suggested_date: date | None = Field(default=None, alias="suggestedDate")
    suggested_time: time | None = Field(default=None, alias="suggestedTime")
    source_page: int | None = Field(default=None, ge=1, alias="sourcePage")
    source_excerpt: str | None = Field(default=None, max_length=5000, alias="sourceExcerpt")
    ambiguous: bool = False
    ambiguous_fields: list[str] = Field(default_factory=list, alias="ambiguousFields")

    @field_validator("kind", "source_excerpt", mode="before")
    @classmethod
    def empty_revision_strings_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


class CreateRevisionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_version_id: UUID | None = Field(default=None, alias="sourceVersionId")
    candidates: list[RevisionCandidateInput] | None = Field(default=None, min_length=1, max_length=100)
    share: bool = False


class UpdateVersionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    candidates: list[RevisionCandidateInput] = Field(min_length=1, max_length=100)


class ValidateProvenanceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    institutional_source_url: str = Field(min_length=8, max_length=2048, alias="institutionalSourceUrl")


class VoteVersionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True)

    value: str = Field(pattern="^(confirm|contest|confirma|contesta)$")
    candidate_id: UUID | None = Field(default=None, alias="candidateId")


class CandidateVoteSummaryRead(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    candidate_id: UUID = Field(alias="candidateId")
    version_id: UUID = Field(alias="versionId")
    confirm_count: int = Field(alias="confirmCount")
    contest_count: int = Field(alias="contestCount")
    divergent: bool = False
    my_vote: str | None = Field(default=None, alias="myVote")


class VoteVersionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version_id: UUID = Field(alias="versionId")
    candidate_id: UUID | None = Field(default=None, alias="candidateId")
    confirm_count: int = Field(alias="confirmCount")
    contest_count: int = Field(alias="contestCount")
    divergent: bool = False
    my_vote: str = Field(alias="myVote")


class VersionVotesResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version_id: UUID = Field(alias="versionId")
    confirm_count: int = Field(alias="confirmCount")
    contest_count: int = Field(alias="contestCount")
    divergent: bool = False
    my_vote: str | None = Field(default=None, alias="myVote")
    items: list[CandidateVoteSummaryRead] = Field(default_factory=list)


class VersionStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    syllabus_id: UUID = Field(alias="syllabusId")
    offering_id: UUID | None = Field(default=None, alias="offeringId")
    number: int
    visibility: str
    author_id: UUID = Field(alias="authorId")
    author_role: str = Field(alias="authorRole")
    source_version_id: UUID | None = Field(default=None, alias="sourceVersionId")
    institutional_provenance: bool = Field(default=False, alias="institutionalProvenance")
    institutional_source_url: str | None = Field(default=None, alias="institutionalSourceUrl")
    shared_at: datetime | None = Field(default=None, alias="sharedAt")
    withdrawn_at: datetime | None = Field(default=None, alias="withdrawnAt")
    created_at: datetime | None = Field(default=None, alias="createdAt")
    membership_type: str = Field(default="autodeclarado", alias="membershipType")
    shared_content_notice: str = Field(alias="sharedContentNotice")
    candidates: list[SyllabusCandidateRead] = Field(default_factory=list)


class SyllabusVersionListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    syllabus_id: UUID = Field(alias="syllabusId")
    offering_id: UUID | None = Field(default=None, alias="offeringId")
    membership_type: str = Field(default="autodeclarado", alias="membershipType")
    shared_content_notice: str = Field(alias="sharedContentNotice")
    items: list[VersionStatusResponse] = Field(default_factory=list)
    total: int



class ConfirmItemResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    candidate_id: UUID = Field(alias="candidateId")
    event_id: UUID | None = Field(default=None, alias="eventId")
    result: str
    removed: bool = False
    kind: str | None = Field(default=None, alias="type")


class ConfirmSyllabusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    syllabus_id: UUID = Field(alias="syllabusId")
    operation_id: UUID = Field(alias="operationId")
    repeated: bool
    items: list[ConfirmItemResult]
    events: list[PersonalEventRead]
