from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


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
    error_code: str | None = Field(default=None, alias="errorCode")
    page_count: int | None = Field(default=None, alias="pageCount")
    attempts: int = 0
    processing_started_at: datetime | None = Field(default=None, alias="processingStartedAt")
    processed_at: datetime | None = Field(default=None, alias="processedAt")
    processing_duration_ms: int | None = Field(default=None, alias="processingDurationMs")
    total_duration_ms: int | None = Field(default=None, alias="totalDurationMs")
    disciplina: str | None = None
    turma: str | None = None
    created_at: datetime = Field(alias="createdAt")

