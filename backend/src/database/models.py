from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid, func
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
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    campus: Mapped[Campus | None] = relationship()
    category: Mapped[Category | None] = relationship()
