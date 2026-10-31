from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SyllabusUploadResponse(BaseModel):
    """Schema de resposta após upload bem-sucedido de plano de ensino."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

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

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

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



class SyllabusListResponse(BaseModel):
    items: list[SyllabusDetailResponse]
    total: int
