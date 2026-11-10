from datetime import date, datetime, time
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, JSON, Numeric, SmallInteger, String, Text, Time, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, synonym


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
    # Nulo em evento coletado: quem o identifica é a fonte (S7-B05).
    author_id: Mapped[UUID | None] = mapped_column(
        "autor_id", Uuid(as_uuid=True), ForeignKey("profiles.id"), nullable=True
    )
    title: Mapped[str] = mapped_column("titulo", String, nullable=False)
    description: Mapped[str] = mapped_column("descricao", Text, nullable=False)
    # Todo evento aprovado tem início; só item coletado em revisão pode não ter.
    starts_at: Mapped[datetime | None] = mapped_column(
        "data_evento", DateTime(timezone=True), nullable=True, index=True
    )
    # ADR-011: fim exclusivo. Em dia inteiro, o banco preenche starts_at e
    # ends_at com a meia-noite de Brasília de start_date e end_date.
    ends_at: Mapped[datetime | None] = mapped_column("data_fim", DateTime(timezone=True), nullable=True)
    all_day: Mapped[bool] = mapped_column("dia_inteiro", Boolean, default=False, nullable=False)
    start_date: Mapped[date | None] = mapped_column("data_inicio_civil", Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column("data_fim_civil", Date, nullable=True)
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

    # Procedência da coleta (S7-B05). Só registrar_evento_coletado() preenche.
    source: Mapped[str | None] = mapped_column("fonte", String, nullable=True)
    source_id: Mapped[str | None] = mapped_column("fonte_id", String, nullable=True)
    source_url: Mapped[str | None] = mapped_column("fonte_url", String, nullable=True)
    source_kind: Mapped[str | None] = mapped_column("fonte_tipo", String, nullable=True)
    source_hash: Mapped[str | None] = mapped_column("fonte_hash", String, nullable=True)
    collected_at: Mapped[datetime | None] = mapped_column("coletado_em", DateTime(timezone=True), nullable=True)
    # Mantido pelo banco: campos alterados na plataforma, que a coleta não sobrescreve.
    edited_fields: Mapped[list[str]] = mapped_column(
        "campos_editados", JSON().with_variant(ARRAY(Text), "postgresql"), default=list, nullable=False
    )
    review_reason: Mapped[str | None] = mapped_column("motivo_revisao", String, nullable=True)
    possible_duplicate_of: Mapped[UUID | None] = mapped_column(
        "possivel_duplicata_de", Uuid(as_uuid=True), ForeignKey("eventos.id", ondelete="SET NULL"), nullable=True
    )
    moderated_by: Mapped[UUID | None] = mapped_column(
        "moderado_por", Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    moderated_at: Mapped[datetime | None] = mapped_column("moderado_em", DateTime(timezone=True), nullable=True)

    campus: Mapped[Campus | None] = relationship()
    category: Mapped[Category | None] = relationship()
    # foreign_keys: eventos também referencia profiles em moderado_por.
    author: Mapped[Profile | None] = relationship(foreign_keys=[author_id])


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
    # Um candidato gera no máximo um evento por usuário (S7-D01).
    __table_args__ = (
        UniqueConstraint("user_id", "origem_avaliacao_id", name="uq_eventos_pessoais_usuario_avaliacao"),
    )

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False, index=True)
    title: Mapped[str] = mapped_column("titulo", String, nullable=False)
    description: Mapped[str | None] = mapped_column("descricao", Text, nullable=True)
    starts_at: Mapped[datetime] = mapped_column(
        "data_hora", DateTime(timezone=True), nullable=False, index=True
    )
    # ADR-011: mesmas regras de PublicEvent (fim exclusivo, dia inteiro em data civil).
    ends_at: Mapped[datetime | None] = mapped_column("data_fim", DateTime(timezone=True), nullable=True)
    all_day: Mapped[bool] = mapped_column("dia_inteiro", Boolean, default=False, nullable=False)
    start_date: Mapped[date | None] = mapped_column("data_inicio_civil", Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column("data_fim_civil", Date, nullable=True)
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
        "origem_avaliacao_id", Uuid(as_uuid=True), nullable=True
    )
    origin_version_id: Mapped[UUID | None] = mapped_column(
        "origem_versao_id", Uuid(as_uuid=True), ForeignKey("versoes_plano.id", ondelete="SET NULL"), nullable=True
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
    offering_id: Mapped[UUID | None] = mapped_column(
        "oferta_id", Uuid(as_uuid=True), ForeignKey("ofertas_turma.id", ondelete="SET NULL"), nullable=True
    )
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
    prepared_pages: Mapped[list[dict] | None] = mapped_column("texto_preparado", JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql"))
    approved_pages: Mapped[list[dict] | None] = mapped_column("texto_aprovado", JSON(none_as_null=True).with_variant(JSONB(none_as_null=True), "postgresql"))
    approved_hash: Mapped[str | None] = mapped_column("hash_texto_aprovado", String(64))
    authorized_at: Mapped[datetime | None] = mapped_column("autorizado_em", DateTime(timezone=True))
    queued_at: Mapped[datetime | None] = mapped_column("enfileirado_em", DateTime(timezone=True))
    preparation_duration_ms: Mapped[int | None] = mapped_column("duracao_preparacao_ms", Integer)
    text_revision: Mapped[int] = mapped_column("versao_texto", Integer, default=0, nullable=False)
    approved_version_id: Mapped[UUID | None] = mapped_column(
        "versao_aprovada_id", Uuid(as_uuid=True), ForeignKey(
            "versoes_plano.id", ondelete="RESTRICT", use_alter=True,
            name="planos_versao_aprovada_fkey"
        )
    )


    @property
    def prepared_text_available(self) -> bool:
        return bool(self.prepared_pages)

    @property
    def authorization_required(self) -> bool:
        return self.prepared_pages is not None and self.authorized_at is None


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
    # No PostgreSQL é obrigatório; um trigger usa a versão mais recente do plano quando omitido.
    version_id: Mapped[UUID | None] = mapped_column(
        "versao_id", Uuid(as_uuid=True), ForeignKey("versoes_plano.id", ondelete="CASCADE"), nullable=True, index=True
    )
    order: Mapped[int | None] = mapped_column("ordem", SmallInteger, nullable=True)


    # Campos civis e rastreamento do extrator: nunca inferem um instante/fuso.
    execucao: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data_sugerida: Mapped[date | None] = mapped_column(Date)
    hora_sugerida: Mapped[time | None] = mapped_column(Time)
    campos_ambiguos: Mapped[list[str]] = mapped_column(JSON().with_variant(ARRAY(Text), "postgresql"), default=list)
    modelo_ia: Mapped[str | None] = mapped_column(String)
    revisado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Compatibilidade de nomes do extrator; uma única tabela física (S7-D01).
    plano_id = synonym("syllabus_id")
    titulo = synonym("title")
    tipo = synonym("kind")
    pagina_origem = synonym("source_page")
    trecho_origem = synonym("source_excerpt")
    provedor_ia = synonym("provider")
    versao_processamento = synonym("processing_version")
    ordem = synonym("order")
    ambiguo = synonym("ambiguous")


AssessmentCandidate = SyllabusCandidate


class Subject(Base):
    """Disciplina abstrata do catálogo público (sem semestre)."""

    __tablename__ = "disciplinas"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column("origem", String, default="followw", nullable=False)
    source_id: Mapped[str | None] = mapped_column("origem_id", String, nullable=True)
    code: Mapped[str] = mapped_column("codigo", String, nullable=False)
    name: Mapped[str] = mapped_column("nome", String, nullable=False)
    unit: Mapped[str | None] = mapped_column("unidade", String, nullable=True)
    level: Mapped[str | None] = mapped_column("nivel", String, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        "atualizado_na_origem_em", DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ClassOffering(Base):
    """Oferta de uma disciplina em um período: turma + ano + semestre."""

    __tablename__ = "ofertas_turma"
    __table_args__ = (
        UniqueConstraint("disciplina_id", "turma", "ano", "semestre", name="ofertas_turma_identidade"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        "disciplina_id", Uuid(as_uuid=True), ForeignKey("disciplinas.id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column("origem", String, default="followw", nullable=False)
    source_id: Mapped[str | None] = mapped_column("origem_id", String, nullable=True)
    class_number: Mapped[str] = mapped_column("turma", String, nullable=False)
    year: Mapped[int] = mapped_column("ano", SmallInteger, nullable=False)
    semester: Mapped[int] = mapped_column("semestre", SmallInteger, nullable=False)
    teacher: Mapped[str | None] = mapped_column("professor", String, nullable=True)
    schedule: Mapped[str | None] = mapped_column("horarios", String, nullable=True)
    source_updated_at: Mapped[datetime | None] = mapped_column(
        "atualizado_na_origem_em", DateTime(timezone=True), nullable=True
    )
    synced_at: Mapped[datetime | None] = mapped_column("sincronizado_em", DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    subject: Mapped[Subject] = relationship()


class ClassFollow(Base):
    """Vínculo autodeclarado entre usuário e oferta; único por par."""

    __tablename__ = "vinculos_turma"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    offering_id: Mapped[UUID] = mapped_column(
        "oferta_id", Uuid(as_uuid=True), ForeignKey("ofertas_turma.id", ondelete="RESTRICT"), primary_key=True
    )
    source: Mapped[str] = mapped_column("origem", String, default="autodeclarado", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SyllabusVersion(Base):
    """Versão de um plano. Privada por padrão; compartilhar registra a data."""

    __tablename__ = "versoes_plano"
    __table_args__ = (
        UniqueConstraint("plano_id", "numero", name="versoes_plano_numero_unico"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    syllabus_id: Mapped[UUID] = mapped_column(
        "plano_id", Uuid(as_uuid=True), ForeignKey("planos_ensino.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column("numero", SmallInteger, nullable=False)
    author_id: Mapped[UUID] = mapped_column(
        "autor_id", Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    author_role: Mapped[str] = mapped_column("autor_papel", String, default="student", nullable=False)
    source_version_id: Mapped[UUID | None] = mapped_column(
        "versao_origem_id", Uuid(as_uuid=True), ForeignKey("versoes_plano.id", ondelete="SET NULL"), nullable=True
    )
    institutional_provenance: Mapped[bool] = mapped_column(
        "procedencia_institucional", Boolean, default=False, nullable=False
    )
    visibility: Mapped[str] = mapped_column("visibilidade", String, default="privada", nullable=False)
    shared_at: Mapped[datetime | None] = mapped_column("compartilhada_em", DateTime(timezone=True), nullable=True)
    # Evidência pública oficial, validada por admin. Papel do autor não a substitui.
    institutional_source_url: Mapped[str | None] = mapped_column("fonte_institucional_url", String, nullable=True)
    provenance_validated_by: Mapped[UUID | None] = mapped_column(
        "procedencia_validada_por", Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    provenance_validated_at: Mapped[datetime | None] = mapped_column(
        "procedencia_validada_em", DateTime(timezone=True), nullable=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column("retirada_em", DateTime(timezone=True), nullable=True)
    withdrawn_by: Mapped[UUID | None] = mapped_column(
        "retirada_por", Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class EventCollectionRun(Base):
    """Uma execução do coletor de eventos (S7-B05)."""

    __tablename__ = "coletas_eventos"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column("fonte", String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="executando", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        "iniciada_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column("concluida_em", DateTime(timezone=True), nullable=True)
    items_read: Mapped[int] = mapped_column("itens_lidos", Integer, default=0, nullable=False)
    created: Mapped[int] = mapped_column("criados", Integer, default=0, nullable=False)
    updated: Mapped[int] = mapped_column("atualizados", Integer, default=0, nullable=False)
    unchanged: Mapped[int] = mapped_column("inalterados", Integer, default=0, nullable=False)
    reconciled: Mapped[int] = mapped_column("conciliados", Integer, default=0, nullable=False)
    sent_to_review: Mapped[int] = mapped_column("para_revisao", Integer, default=0, nullable=False)
    # Código curto (http_503, timeout). Nunca HTML ou conteúdo da fonte.
    error_code: Mapped[str | None] = mapped_column("erro_codigo", String, nullable=True)


class ImportOperation(Base):
    """Ação de confirmação identificada pela Idempotency-Key (ADR-010). Gravada por confirmar_importacao()."""

    __tablename__ = "operacoes_importacao"
    __table_args__ = (
        UniqueConstraint("user_id", "chave", name="operacoes_importacao_chave_unica"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column("chave", String, nullable=False)
    version_id: Mapped[UUID | None] = mapped_column(
        "versao_id", Uuid(as_uuid=True), ForeignKey("versoes_plano.id", ondelete="SET NULL"), nullable=True
    )
    content_hash: Mapped[str] = mapped_column("conteudo_hash", String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ImportItem(Base):
    """Item de uma operação. event_id fica nulo quando a pessoa apaga o evento."""

    __tablename__ = "itens_importacao"

    operation_id: Mapped[UUID] = mapped_column(
        "operacao_id", Uuid(as_uuid=True), ForeignKey("operacoes_importacao.id", ondelete="CASCADE"), primary_key=True
    )
    candidate_id: Mapped[UUID] = mapped_column("avaliacao_id", Uuid(as_uuid=True), primary_key=True)
    event_id: Mapped[UUID | None] = mapped_column(
        "evento_pessoal_id", Uuid(as_uuid=True), ForeignKey("eventos_pessoais.id", ondelete="SET NULL"), nullable=True
    )
    result: Mapped[str] = mapped_column("resultado", String, nullable=False)  # criado | ja_importado


class CandidateVote(Base):
    """Voto de um seguidor sobre um candidato compartilhado (S8-B01). Gravado por votar_avaliacao()."""

    __tablename__ = "votos_avaliacao"

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    candidate_id: Mapped[UUID] = mapped_column(
        "avaliacao_id", Uuid(as_uuid=True), ForeignKey("avaliacoes.id", ondelete="CASCADE"), primary_key=True
    )
    value: Mapped[str] = mapped_column("valor", String, nullable=False)  # confirma | contesta
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        "atualizado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Reminder(Base):
    """Aviso na plataforma 24 h antes do início (S8-B03).

    O banco agenda, troca e cancela os avisos por triggers; a aplicação só
    lê os disparados e marca a leitura.
    """

    __tablename__ = "lembretes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_kind: Mapped[str] = mapped_column("tipo_evento", String, nullable=False)
    personal_event_id: Mapped[UUID | None] = mapped_column(
        "evento_pessoal_id", Uuid(as_uuid=True), ForeignKey("eventos_pessoais.id", ondelete="CASCADE"), nullable=True
    )
    public_event_id: Mapped[UUID | None] = mapped_column(
        "evento_id", Uuid(as_uuid=True), ForeignKey("eventos.id", ondelete="CASCADE"), nullable=True
    )
    event_starts_at: Mapped[datetime] = mapped_column("inicio_referencia", DateTime(timezone=True), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column("agendado_para", DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String, default="pendente", nullable=False)
    fired_at: Mapped[datetime | None] = mapped_column("disparado_em", DateTime(timezone=True), nullable=True)
    read_at: Mapped[datetime | None] = mapped_column("lido_em", DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "criado_em", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
