from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    func,
    text,
)
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


class CourseOffer(Base):
    """Oferta de uma disciplina em uma turma e período acadêmico específicos."""

    __tablename__ = "ofertas_turma"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(
        "origem", String, nullable=False, default="sigaa", server_default="sigaa"
    )
    source_offer_id: Mapped[str | None] = mapped_column("id_origem", String, nullable=True)
    course_code: Mapped[str | None] = mapped_column("codigo_disciplina", String, nullable=True)
    course_name: Mapped[str] = mapped_column("nome_disciplina", String, nullable=False)
    class_number: Mapped[str] = mapped_column("numero_turma", String, nullable=False)
    period: Mapped[str] = mapped_column("periodo", String, nullable=False)
    unit: Mapped[str | None] = mapped_column("unidade", String, nullable=True)
    level: Mapped[str | None] = mapped_column("nivel", String, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "uq_ofertas_turma_origem_id_periodo",
            "origem", "id_origem", "periodo", unique=True,
            postgresql_where=text("id_origem is not null"),
            sqlite_where=text("id_origem is not null"),
        ),
        Index(
            "uq_ofertas_turma_chave_composta",
            func.lower(func.trim(text("origem"))),
            func.lower(
                func.trim(
                    func.coalesce(
                        func.nullif(func.trim(text("codigo_disciplina")), text("''")),
                        text("nome_disciplina"),
                    )
                )
            ),
            func.lower(func.trim(text("numero_turma"))),
            func.lower(func.trim(text("periodo"))),
            func.lower(func.trim(func.coalesce(text("unidade"), text("''")))),
            func.lower(func.trim(func.coalesce(text("nivel"), text("''")))),
            unique=True,
            postgresql_where=text("id_origem is null"),
            sqlite_where=text("id_origem is null"),
        ),
        CheckConstraint(
            "id_origem is null or length(trim(id_origem)) > 0",
            name="ck_ofertas_turma_id_origem_nao_vazio",
        ),
        Index("idx_ofertas_turma_periodo_codigo", "periodo", "codigo_disciplina"),
    )


class CourseEnrollment(Base):
    """Vínculo único de um usuário com uma oferta acadêmica."""

    __tablename__ = "vinculos_turma"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    offer_id: Mapped[UUID] = mapped_column(
        "oferta_id", Uuid(as_uuid=True), ForeignKey("ofertas_turma.id", ondelete="CASCADE"), primary_key=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    offer: Mapped[CourseOffer] = relationship()


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
    author_id: Mapped[UUID | None] = mapped_column(
        "autor_id", Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    offer_id: Mapped[UUID | None] = mapped_column(
        "oferta_id", Uuid(as_uuid=True), ForeignKey("ofertas_turma.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version: Mapped[int] = mapped_column(
        "versao", Integer, nullable=False, default=1, server_default="1"
    )
    visibility: Mapped[str] = mapped_column(
        "visibilidade", String, nullable=False, default="privado", server_default="privado"
    )
    file_name: Mapped[str] = mapped_column("nome_arquivo", String, nullable=False)
    file_path: Mapped[str] = mapped_column("caminho_arquivo", String, nullable=False)
    arquivo_url: Mapped[str | None] = mapped_column("arquivo_url", String, nullable=True)
    file_size: Mapped[int | None] = mapped_column("tamanho_bytes", BigInteger, nullable=True)
    file_type: Mapped[str] = mapped_column("tipo_arquivo", String, default="pdf", nullable=False)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="processing"
    )
    extracted_events_count: Mapped[int] = mapped_column("quantidade_eventos", Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column("erro", Text, nullable=True)
    disciplina: Mapped[str | None] = mapped_column(String, nullable=True)
    turma: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[Profile] = relationship(foreign_keys=[user_id])
    author: Mapped[Profile | None] = relationship(foreign_keys=[author_id])
    offer: Mapped[CourseOffer | None] = relationship()

    __table_args__ = (
        CheckConstraint("versao > 0", name="ck_planos_ensino_versao_positiva"),
        CheckConstraint(
            "visibilidade in ('privado', 'compartilhado')",
            name="ck_planos_ensino_visibilidade",
        ),
        Index("idx_planos_ensino_user_oferta_versao", "user_id", "oferta_id", "versao"),
        Index(
            "uq_planos_ensino_oferta_autor_versao",
            "oferta_id", "autor_id", "versao", unique=True,
            postgresql_where=text("oferta_id is not null and autor_id is not null"),
            sqlite_where=text("oferta_id is not null and autor_id is not null"),
        ),
    )


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
