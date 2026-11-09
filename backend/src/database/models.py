from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, JSON, Numeric, SmallInteger, String, Text, Time, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Campus(Base):
    __tablename__ = "campus"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class Profile(Base):
    """Campos usados pela API na tabela profiles que já existe no Supabase."""

    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    papel: Mapped[str] = mapped_column(String, nullable=False)
    nome_completo: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String, nullable=True)


class PublicEvent(Base):
    __tablename__ = "eventos"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    author_id: Mapped[UUID] = mapped_column(
        "autor_id", Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    title: Mapped[str] = mapped_column("titulo", String, nullable=False)
    description: Mapped[str] = mapped_column("descricao", Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(
        "data_evento", DateTime(timezone=True), nullable=False, index=True
    )
    location: Mapped[str | None] = mapped_column("localizacao", String, nullable=True)
    external_url: Mapped[str | None] = mapped_column("link_externo", String, nullable=True)
    campus_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campus.id"), nullable=True
    )
    category_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pendente")
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    justificativa_recusa: Mapped[str | None] = mapped_column(Text, nullable=True)

    campus: Mapped[Campus | None] = relationship()
    category: Mapped[Category | None] = relationship()
    author: Mapped[Profile] = relationship()


class SavedPublicEvent(Base):
    __tablename__ = "eventos_salvos"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    event_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("eventos.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PersonalEvent(Base):
    __tablename__ = "eventos_pessoais"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column("titulo", String, nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(
        "data_hora", DateTime(timezone=True), nullable=False, index=True
    )
    campus_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("campus.id"), nullable=True
    )
    category_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    origin_syllabus_id: Mapped[UUID | None] = mapped_column(
        "origem_plano_id", Uuid(as_uuid=True), nullable=True
    )
    origin_candidate_id: Mapped[UUID | None] = mapped_column(
        "origem_avaliacao_id", Uuid(as_uuid=True), nullable=True, unique=True
    )
    origin_page: Mapped[int | None] = mapped_column("origem_pagina", Integer, nullable=True)
    origin_excerpt: Mapped[str | None] = mapped_column("origem_trecho", Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campus: Mapped[Campus | None] = relationship()
    category: Mapped[Category | None] = relationship()


class Syllabus(Base):
    """Modelo para rastreamento de upload e processamento de planos de ensino."""

    __tablename__ = "planos_ensino"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(
        "user_id", Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    professor_id: Mapped[UUID | None] = mapped_column(
        "professor_id", Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True
    )
    file_name: Mapped[str | None] = mapped_column("nome_arquivo", String, nullable=True)
    file_path: Mapped[str | None] = mapped_column("caminho_arquivo", String, nullable=True)
    arquivo_url: Mapped[str | None] = mapped_column("arquivo_url", String, nullable=True)
    file_size: Mapped[int | None] = mapped_column("tamanho_bytes", BigInteger, nullable=True)
    file_type: Mapped[str] = mapped_column("tipo_arquivo", String, default="pdf", nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pendente"
    )
    extracted_events_count: Mapped[int] = mapped_column("quantidade_eventos", Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column("erro", Text, nullable=True)
    disciplina: Mapped[str | None] = mapped_column(String, nullable=True)
    turma: Mapped[str | None] = mapped_column(String, nullable=True)
    ano: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    semestre: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[Profile] = relationship(foreign_keys=[user_id])
    tipo: Mapped[str] = mapped_column(String, default="particular", nullable=False)
    paginas: Mapped[int | None] = mapped_column(Integer)
    execucao_atual: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    provedor_ia: Mapped[str | None] = mapped_column(String)
    modelo_ia: Mapped[str | None] = mapped_column(String)
    versao_processamento: Mapped[str | None] = mapped_column(String)
    erro_codigo: Mapped[str | None] = mapped_column(String)
    processamento_iniciado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processing_token: Mapped[UUID | None] = mapped_column("token_processamento", Uuid(as_uuid=True))
    next_attempt_at: Mapped[datetime | None] = mapped_column("proxima_tentativa_em", DateTime(timezone=True))
    cost_reserved_usd: Mapped[Decimal] = mapped_column("custo_reservado_usd", Numeric(12, 6), default=0, nullable=False)
    processing_duration_ms: Mapped[int | None] = mapped_column("duracao_processamento_ms", Integer)


class AssessmentCandidate(Base):
    """Sugestões privadas; o worker nunca grava eventos_pessoais ou avaliacoes."""

    __tablename__ = "candidatos_avaliacao"
    __table_args__ = (UniqueConstraint("plano_id", "execucao", "ordem"),)

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    plano_id: Mapped[UUID] = mapped_column(ForeignKey("planos_ensino.id", ondelete="CASCADE"))
    execucao: Mapped[int] = mapped_column(Integer)
    ordem: Mapped[int] = mapped_column(Integer)
    titulo: Mapped[str] = mapped_column(String)
    tipo: Mapped[str] = mapped_column(String)
    data_sugerida: Mapped[date | None] = mapped_column(Date)
    hora_sugerida: Mapped[time | None] = mapped_column(Time)
    campos_ambiguos: Mapped[list[str]] = mapped_column(JSON().with_variant(ARRAY(Text), "postgresql"), default=list)
    pagina_origem: Mapped[int] = mapped_column(Integer)
    trecho_origem: Mapped[str] = mapped_column(Text)
    provedor_ia: Mapped[str] = mapped_column(String)
    modelo_ia: Mapped[str] = mapped_column(String)
    versao_processamento: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pendente")
    revisado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evento_pessoal_id: Mapped[UUID | None] = mapped_column(ForeignKey("eventos_pessoais.id", ondelete="SET NULL"), unique=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def ambiguo(self) -> bool:
        return bool(self.campos_ambiguos)


class SyllabusCandidate(Base):
    """Avaliação extraída de um plano, ainda sujeita à revisão do estudante."""

    __tablename__ = "avaliacoes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    syllabus_id: Mapped[UUID] = mapped_column(
        "plano_id", Uuid(as_uuid=True), ForeignKey("planos_ensino.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column("titulo", String, nullable=False)
    starts_at: Mapped[datetime | None] = mapped_column(
        "data_avaliacao", DateTime(timezone=True), nullable=True
    )
    kind: Mapped[str | None] = mapped_column("tipo", String, nullable=True)
    ambiguous: Mapped[bool] = mapped_column("ambiguo", default=False, nullable=False)
    source_page: Mapped[int | None] = mapped_column("pagina_origem", Integer, nullable=True)
    source_excerpt: Mapped[str | None] = mapped_column("trecho_origem", Text, nullable=True)
    status: Mapped[str] = mapped_column("status", String, default="pendente", nullable=False)
    processing_version: Mapped[str | None] = mapped_column("versao_processamento", String, nullable=True)
    provider: Mapped[str | None] = mapped_column("provedor", String, nullable=True)
