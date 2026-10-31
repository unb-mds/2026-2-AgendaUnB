from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.modules.events.schemas import PersonalEventRead


class SyllabusUploadResponse(BaseModel):
    """Schema de resposta após upload bem-sucedido de plano de ensino."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    user_id: UUID = Field(alias="userId")
    file_name: str = Field(alias="fileName")
    file_path: str = Field(alias="filePath")
    file_size: int | None = Field(default=None, alias="fileSize")
    file_type: str = Field(default="pdf", alias="fileType")
    status: str = Field(default="pendente")
    created_at: datetime = Field(alias="createdAt")
    message: str = "Plano de ensino recebido com sucesso e direcionado para processamento."


class SyllabusDetailResponse(BaseModel):
    """Schema para consulta de status de processamento do plano."""

    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    user_id: UUID = Field(alias="userId")
    file_name: str = Field(alias="fileName")
    file_path: str = Field(alias="filePath")
    file_size: int | None = Field(default=None, alias="fileSize")
    file_type: str = Field(default="pdf", alias="fileType")
    status: str
    extracted_events_count: int = Field(default=0, alias="extractedEventsCount")
    error_message: str | None = Field(default=None, alias="errorMessage")
    disciplina: str | None = None
    turma: str | None = None
    created_at: datetime = Field(alias="createdAt")
    candidates: list["SyllabusCandidateRead"] = Field(default_factory=list)


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


class SyllabusListItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: UUID
    file_name: str = Field(alias="fileName")
    file_size: int | None = Field(alias="fileSize")
    status: str
    extracted_events_count: int = Field(alias="extractedEventsCount")
    error_message: str | None = Field(alias="errorMessage")
    disciplina: str | None = None
    turma: str | None = None
    created_at: datetime = Field(alias="createdAt")


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
    starts_at: datetime | None = Field(default=None, alias="startsAt")
    category: str | None = Field(default=None, min_length=2, max_length=80)

    @field_validator("starts_at")
    @classmethod
    def require_explicit_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Informe data e hora com fuso horário (ISO 8601)")
        return value

    @field_validator("description", "category", mode="before")
    @classmethod
    def empty_values_to_none(cls, value):
        if isinstance(value, str) and not value.strip():
            return None
        return value


class ConfirmSyllabusRequest(BaseModel):
    candidates: list[ConfirmCandidateInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def candidate_ids_must_be_unique(self):
        ids = [candidate.candidate_id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("Não repita o mesmo candidato na confirmação")
        return self


class ConfirmSyllabusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    syllabus_id: UUID = Field(alias="syllabusId")
    events: list[PersonalEventRead]

