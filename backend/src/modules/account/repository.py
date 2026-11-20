from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Uuid, column, delete, func, inspect, or_, select, table, text, update
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from src.database.models import (
    AccountDeletionRecord,
    AssessmentCandidate,
    ClassFollow,
    ClassOffering,
    Consent,
    GoogleCalendarConnection,
    GoogleCalendarOAuthState,
    ImportItem,
    ImportOperation,
    PersonalEvent,
    Profile,
    PublicEvent,
    SavedPublicEvent,
    Subject,
    Syllabus,
    SyllabusVersion,
    TermAcceptance,
)
from src.middlewares.auth import CurrentUser

CURRENT_LEGAL_VERSIONS: dict[str, str] = {
    "terms": "2026-11-20",
    "privacy": "2026-11-20",
}

CONFIRMATION_PHRASE = "EXCLUIR MINHA CONTA"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def get_legal_acceptances(db: Session, user_id: UUID) -> dict[str, TermAcceptance]:
    rows = db.scalars(
        select(TermAcceptance)
        .where(TermAcceptance.user_id == user_id)
        .order_by(TermAcceptance.accepted_at.desc(), TermAcceptance.version.desc())
    ).all()
    latest: dict[str, TermAcceptance] = {}
    for row in rows:
        if row.document not in latest:
            latest[row.document] = row
    return latest


def record_legal_acceptance(db: Session, user_id: UUID, document: str, version: str) -> None:
    existing = db.get(TermAcceptance, (user_id, document, version))
    if existing is None:
        try:
            with db.begin_nested():
                db.add(TermAcceptance(user_id=user_id, document=document, version=version))
                db.flush()
        except IntegrityError:
            # Inserção simultânea da mesma chave primária é idempotente.
            pass


def list_consents(db: Session, user_id: UUID) -> list[Consent]:
    return list(
        db.scalars(
            select(Consent)
            .where(Consent.user_id == user_id)
            .order_by(Consent.granted_at.desc(), Consent.id.desc())
        ).all()
    )


def upsert_active_consent(
    db: Session,
    *,
    user_id: UUID,
    purpose: str,
    reference_id: UUID | None = None,
    content_hash: str | None = None,
) -> Consent:
    active = db.scalar(
        select(Consent).where(
            Consent.user_id == user_id,
            Consent.purpose == purpose,
            Consent.revoked_at.is_(None),
        )
    )
    now = _utcnow()
    if active is not None:
        active.reference_id = reference_id
        active.content_hash = content_hash
        active.granted_at = now
        db.flush()
        return active
    consent = Consent(
        user_id=user_id,
        purpose=purpose,
        reference_id=reference_id,
        content_hash=content_hash,
        granted_at=now,
    )
    db.add(consent)
    db.flush()
    return consent


def revoke_active_consents(
    db: Session,
    user_id: UUID,
    purpose: str,
    now: datetime | None = None,
) -> int:
    revoked_at = now or _utcnow()
    result = db.execute(
        update(Consent)
        .where(
            Consent.user_id == user_id,
            Consent.purpose == purpose,
            Consent.revoked_at.is_(None),
        )
        .values(revoked_at=revoked_at)
    )
    db.flush()
    return int(result.rowcount or 0)


def _serialize_candidate(row: AssessmentCandidate) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "title": row.title,
        "type": row.kind,
        "starts_at": _iso(row.starts_at),
        "suggested_date": row.data_sugerida.isoformat() if row.data_sugerida else None,
        "suggested_time": row.hora_sugerida.isoformat() if row.hora_sugerida else None,
        "ambiguous": row.ambiguous,
        "ambiguous_fields": list(row.campos_ambiguos or []),
        "source_page": row.source_page,
        "source_excerpt": row.source_excerpt,
        "status": row.status,
        "version_id": _iso(row.version_id),
        "created_at": _iso(row.criado_em),
    }


def collect_user_export_data(db: Session, user: CurrentUser) -> dict[str, Any]:
    profile = db.get(Profile, user.id)
    profile_data = {
        "id": str(user.id),
        "email": user.email,
        "full_name": profile.nome_completo if profile else None,
        "role": profile.papel if profile else user.role,
        "avatar_url": profile.avatar_url if profile else None,
    }

    personal_rows = db.scalars(
        select(PersonalEvent)
        .where(PersonalEvent.user_id == user.id)
        .order_by(PersonalEvent.starts_at.asc(), PersonalEvent.id.asc())
    ).all()
    personal_events = [
        {
            "id": str(row.id),
            "title": row.title,
            "description": row.description,
            "starts_at": _iso(row.starts_at),
            "ends_at": _iso(row.ends_at),
            "all_day": row.all_day,
            "start_date": row.start_date.isoformat() if row.start_date else None,
            "end_date": row.end_date.isoformat() if row.end_date else None,
            "campus_id": _iso(row.campus_id),
            "category_id": _iso(row.category_id),
            "origin_syllabus_id": _iso(row.origin_syllabus_id),
            "origin_candidate_id": _iso(row.origin_candidate_id),
            "origin_version_id": _iso(row.origin_version_id),
            "origin_page": row.origin_page,
            "origin_excerpt": row.origin_excerpt,
            "created_at": _iso(row.created_at),
        }
        for row in personal_rows
    ]

    saved_rows = db.execute(
        select(SavedPublicEvent, PublicEvent)
        .join(PublicEvent, SavedPublicEvent.event_id == PublicEvent.id)
        .where(SavedPublicEvent.user_id == user.id)
        .order_by(SavedPublicEvent.created_at.desc(), SavedPublicEvent.event_id.asc())
    ).all()
    saved_events = [
        {
            "event_id": str(saved.event_id),
            "saved_at": _iso(saved.created_at),
            "title": event.title,
            "starts_at": _iso(event.starts_at),
        }
        for saved, event in saved_rows
    ]

    public_rows = db.scalars(
        select(PublicEvent)
        .where(PublicEvent.author_id == user.id)
        .order_by(PublicEvent.created_at.desc(), PublicEvent.id.asc())
    ).all()
    public_events = [
        {
            "id": str(row.id),
            "title": row.title,
            "description": row.description,
            "starts_at": _iso(row.starts_at),
            "ends_at": _iso(row.ends_at),
            "all_day": row.all_day,
            "start_date": row.start_date.isoformat() if row.start_date else None,
            "end_date": row.end_date.isoformat() if row.end_date else None,
            "location": row.location,
            "external_url": row.external_url,
            "status": row.status,
            "justificativa_recusa": row.justificativa_recusa,
            "created_at": _iso(row.created_at),
        }
        for row in public_rows
    ]

    follow_rows = db.execute(
        select(ClassFollow, ClassOffering, Subject)
        .join(ClassOffering, ClassFollow.offering_id == ClassOffering.id)
        .join(Subject, ClassOffering.subject_id == Subject.id)
        .where(ClassFollow.user_id == user.id)
        .order_by(ClassFollow.created_at.desc(), ClassFollow.offering_id.asc())
    ).all()
    followed_classes = [
        {
            "offering_id": str(follow.offering_id),
            "subject_code": subject.code,
            "subject_name": subject.name,
            "class_number": offering.class_number,
            "year": offering.year,
            "semester": offering.semester,
            "source": follow.source,
            "created_at": _iso(follow.created_at),
        }
        for follow, offering, subject in follow_rows
    ]

    syllabus_rows = db.scalars(
        select(Syllabus)
        .where(or_(Syllabus.user_id == user.id, Syllabus.professor_id == user.id))
        .order_by(Syllabus.created_at.desc(), Syllabus.id.asc())
    ).all()
    owned_syllabus_ids = [row.id for row in syllabus_rows]

    authored_versions = db.scalars(
        select(SyllabusVersion)
        .where(SyllabusVersion.author_id == user.id)
        .order_by(SyllabusVersion.created_at.asc(), SyllabusVersion.id.asc())
    ).all()
    authored_version_ids = [row.id for row in authored_versions]

    candidates_by_version: dict[UUID, list[dict[str, Any]]] = {}
    legacy_candidates_by_syllabus: dict[UUID, list[dict[str, Any]]] = {}
    if authored_version_ids or owned_syllabus_ids:
        filters = []
        if authored_version_ids:
            filters.append(AssessmentCandidate.version_id.in_(authored_version_ids))
        if owned_syllabus_ids:
            filters.append(
                AssessmentCandidate.syllabus_id.in_(owned_syllabus_ids)
                & AssessmentCandidate.version_id.is_(None)
            )
        candidate_rows = db.scalars(
            select(AssessmentCandidate)
            .where(or_(*filters))
            .order_by(AssessmentCandidate.order.asc(), AssessmentCandidate.id.asc())
        ).all()
        for candidate in candidate_rows:
            serialized = _serialize_candidate(candidate)
            if candidate.version_id is not None:
                candidates_by_version.setdefault(candidate.version_id, []).append(serialized)
            else:
                legacy_candidates_by_syllabus.setdefault(candidate.syllabus_id, []).append(serialized)

    authored_versions_by_syllabus: dict[UUID, list[dict[str, Any]]] = {}
    authored_plan_versions: list[dict[str, Any]] = []
    for version in authored_versions:
        version_payload = {
            "id": str(version.id),
            "syllabus_id": str(version.syllabus_id),
            "number": version.number,
            "author_role": version.author_role,
            "source_version_id": _iso(version.source_version_id),
            "institutional_provenance": version.institutional_provenance,
            "visibility": version.visibility,
            "shared_at": _iso(version.shared_at),
            "created_at": _iso(version.created_at),
            "candidates": candidates_by_version.get(version.id, []),
        }
        authored_plan_versions.append(version_payload)
        authored_versions_by_syllabus.setdefault(version.syllabus_id, []).append(version_payload)

    syllabi = [
        {
            "id": str(row.id),
            "offering_id": _iso(row.offering_id),
            "file_name": row.file_name,
            "file_size": row.file_size,
            "file_type": row.file_type,
            "status": row.status,
            "disciplina": row.disciplina,
            "turma": row.turma,
            "ano": row.ano,
            "semestre": row.semestre,
            "extracted_events_count": row.extracted_events_count,
            "prepared_pages": row.prepared_pages,
            "approved_pages": row.approved_pages,
            "authorized_at": _iso(row.authorized_at),
            "discarded_at": _iso(row.discarded_at),
            "created_at": _iso(row.created_at),
            "versions": authored_versions_by_syllabus.get(row.id, []),
            "legacy_candidates": legacy_candidates_by_syllabus.get(row.id, []),
        }
        for row in syllabus_rows
    ]

    operation_rows = db.scalars(
        select(ImportOperation)
        .where(ImportOperation.user_id == user.id)
        .order_by(ImportOperation.created_at.desc(), ImportOperation.id.asc())
    ).all()
    items_by_op: dict[UUID, list[dict[str, Any]]] = {}
    if operation_rows:
        op_ids = [op.id for op in operation_rows]
        item_rows = db.scalars(
            select(ImportItem)
            .where(ImportItem.operation_id.in_(op_ids))
            .order_by(ImportItem.operation_id.asc(), ImportItem.candidate_id.asc())
        ).all()
        for item in item_rows:
            items_by_op.setdefault(item.operation_id, []).append(
                {
                    "candidate_id": str(item.candidate_id),
                    "event_id": _iso(item.event_id),
                    "result": item.result,
                    "candidate_type": item.candidate_type,
                }
            )
    import_operations = [
        {
            "id": str(op.id),
            "version_id": _iso(op.version_id),
            "created_at": _iso(op.created_at),
            "items": items_by_op.get(op.id, []),
        }
        for op in operation_rows
    ]

    bind = db.get_bind()
    inspector = inspect(bind)
    schema = "public" if bind.dialect.name == "postgresql" else None

    votes: list[dict[str, Any]] = []
    if inspector.has_table("votos_avaliacao", schema=schema):
        votes_table = table(
            "votos_avaliacao",
            column("user_id", Uuid(as_uuid=True)),
            column("avaliacao_id", Uuid(as_uuid=True)),
            column("valor"),
            column("criado_em"),
            column("atualizado_em"),
            schema=schema,
        )
        vote_rows = db.execute(
            select(
                votes_table.c.avaliacao_id,
                votes_table.c.valor,
                votes_table.c.criado_em,
                votes_table.c.atualizado_em,
            )
            .where(votes_table.c.user_id == user.id)
            .order_by(votes_table.c.criado_em.desc())
        ).mappings().all()
        votes = [
            {
                "candidate_id": _iso(row["avaliacao_id"]),
                "value": row["valor"],
                "created_at": _iso(row["criado_em"]),
                "updated_at": _iso(row["atualizado_em"]),
            }
            for row in vote_rows
        ]

    notifications: list[dict[str, Any]] = []
    if inspector.has_table("notificacoes", schema=schema):
        notif_table = table(
            "notificacoes",
            column("id", Uuid(as_uuid=True)),
            column("usuario_id", Uuid(as_uuid=True)),
            column("evento_id", Uuid(as_uuid=True)),
            column("tipo"),
            column("titulo_evento"),
            column("justificativa"),
            column("criado_em"),
            column("lida_em"),
            schema=schema,
        )
        notif_rows = db.execute(
            select(
                notif_table.c.id,
                notif_table.c.evento_id,
                notif_table.c.tipo,
                notif_table.c.titulo_evento,
                notif_table.c.justificativa,
                notif_table.c.criado_em,
                notif_table.c.lida_em,
            )
            .where(notif_table.c.usuario_id == user.id)
            .order_by(notif_table.c.criado_em.desc())
        ).mappings().all()
        notifications = [
            {
                "id": _iso(row["id"]),
                "event_id": _iso(row["evento_id"]),
                "type": row["tipo"],
                "event_title": row["titulo_evento"],
                "justification": row["justificativa"],
                "created_at": _iso(row["criado_em"]),
                "read_at": _iso(row["lida_em"]),
            }
            for row in notif_rows
        ]

    acceptance_rows = db.scalars(
        select(TermAcceptance)
        .where(TermAcceptance.user_id == user.id)
        .order_by(TermAcceptance.accepted_at.desc(), TermAcceptance.document.asc())
    ).all()
    legal_acceptances = [
        {
            "document": row.document,
            "version": row.version,
            "accepted_at": _iso(row.accepted_at),
        }
        for row in acceptance_rows
    ]

    consent_rows = list_consents(db, user.id)
    consents = [
        {
            "id": str(row.id),
            "purpose": row.purpose,
            "active": row.revoked_at is None,
            "granted_at": _iso(row.granted_at),
            "revoked_at": _iso(row.revoked_at),
            "reference_id": _iso(row.reference_id),
        }
        for row in consent_rows
    ]

    gcal = db.get(GoogleCalendarConnection, user.id)
    google_calendar: dict[str, Any] | None = None
    if gcal is not None and (gcal.encrypted_refresh_token or gcal.calendar_id or gcal.granted_scope):
        google_calendar = {
            "connected": bool(gcal.encrypted_refresh_token and gcal.encrypted_access_token),
            "google_email": gcal.google_email,
            "calendar_id": gcal.calendar_id,
            "granted_scope": gcal.granted_scope,
            "created_at": _iso(gcal.created_at),
            "updated_at": _iso(gcal.updated_at),
        }

    return {
        "exported_at": _utcnow(),
        "profile": profile_data,
        "personal_events": personal_events,
        "saved_events": saved_events,
        "public_events": public_events,
        "followed_classes": followed_classes,
        "syllabi": syllabi,
        "authored_plan_versions": authored_plan_versions,
        "import_operations": import_operations,
        "votes": votes,
        "notifications": notifications,
        "legal_acceptances": legal_acceptances,
        "consents": consents,
        "google_calendar": google_calendar,
    }


def prepare_account_deletion(db: Session, user_id: UUID) -> tuple[UUID, list[str]]:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        try:
            row = db.execute(
                text("select exclusao_id, caminhos_arquivos from public.preparar_exclusao_conta(:user_id)"),
                {"user_id": user_id},
            ).one()
            db.commit()
            return row.exclusao_id, list(row.caminhos_arquivos or [])
        except DBAPIError as exc:
            db.rollback()
            sqlstate = getattr(exc.orig, "sqlstate", None)
            if sqlstate == "55000":
                raise HTTPException(
                    status_code=409,
                    detail="O último administrador não pode excluir a própria conta.",
                ) from None
            if sqlstate == "P0002":
                raise HTTPException(status_code=404, detail="Conta não encontrada.") from None
            raise

    profile = db.get(Profile, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    if profile.papel == "admin":
        other_admins = db.scalar(
            select(func.count())
            .select_from(Profile)
            .where(Profile.papel == "admin", Profile.id != user_id)
        )
        if not other_admins:
            raise HTTPException(
                status_code=409,
                detail="O último administrador não pode excluir a própria conta.",
            )

    syllabi_count = db.scalar(
        select(func.count())
        .select_from(Syllabus)
        .where(or_(Syllabus.user_id == user_id, Syllabus.professor_id == user_id))
    ) or 0
    personal_count = db.scalar(
        select(func.count()).select_from(PersonalEvent).where(PersonalEvent.user_id == user_id)
    ) or 0
    public_count = db.scalar(
        select(func.count()).select_from(PublicEvent).where(PublicEvent.author_id == user_id)
    ) or 0

    legacy_rows = db.scalars(
        select(Syllabus)
        .where(
            or_(Syllabus.user_id == user_id, Syllabus.professor_id == user_id),
            or_(Syllabus.file_path.is_not(None), Syllabus.arquivo_url.is_not(None)),
        )
        .order_by(Syllabus.created_at.asc(), Syllabus.id.asc())
    ).all()
    paths = [path for row in legacy_rows if (path := row.file_path or row.arquivo_url)]

    record = AccountDeletionRecord(
        status="iniciada",
        removed_syllabi=int(syllabi_count),
        removed_personal_events=int(personal_count),
        removed_public_events=int(public_count),
    )
    db.add(record)
    db.commit()
    return record.id, paths


def complete_account_deletion(
    db: Session,
    deletion_id: UUID,
    *,
    user_id: UUID,
    removed_storage_files: int = 0,
) -> None:
    dialect = db.get_bind().dialect.name
    if dialect == "postgresql":
        db.execute(
            text("select public.concluir_exclusao_conta(:deletion_id, :removed_files)"),
            {"deletion_id": deletion_id, "removed_files": max(0, removed_storage_files)},
        )
        db.commit()
        return

    # SQLite fallback: espelha o cascade do PostgreSQL preservando cópias de terceiros.
    owned_syllabus_ids = list(
        db.scalars(
            select(Syllabus.id).where(or_(Syllabus.user_id == user_id, Syllabus.professor_id == user_id))
        ).all()
    )
    version_filters = [SyllabusVersion.author_id == user_id]
    if owned_syllabus_ids:
        version_filters.append(SyllabusVersion.syllabus_id.in_(owned_syllabus_ids))
    user_version_ids = list(
        db.scalars(select(SyllabusVersion.id).where(or_(*version_filters))).all()
    )

    if user_version_ids:
        db.execute(
            update(PersonalEvent)
            .where(
                PersonalEvent.origin_version_id.in_(user_version_ids),
                PersonalEvent.user_id != user_id,
            )
            .values(origin_version_id=None)
        )
        db.execute(
            update(ImportOperation)
            .where(
                ImportOperation.version_id.in_(user_version_ids),
                ImportOperation.user_id != user_id,
            )
            .values(version_id=None)
        )

    op_ids = list(
        db.scalars(select(ImportOperation.id).where(ImportOperation.user_id == user_id)).all()
    )
    if op_ids:
        db.execute(delete(ImportItem).where(ImportItem.operation_id.in_(op_ids)))
        db.execute(delete(ImportOperation).where(ImportOperation.id.in_(op_ids)))

    candidate_filters = []
    if owned_syllabus_ids:
        candidate_filters.append(AssessmentCandidate.syllabus_id.in_(owned_syllabus_ids))
    if user_version_ids:
        candidate_filters.append(AssessmentCandidate.version_id.in_(user_version_ids))
    if candidate_filters:
        db.execute(delete(AssessmentCandidate).where(or_(*candidate_filters)))

    if owned_syllabus_ids:
        db.execute(
            update(Syllabus)
            .where(Syllabus.id.in_(owned_syllabus_ids))
            .values(approved_version_id=None)
        )
    if user_version_ids:
        db.execute(
            update(SyllabusVersion)
            .where(SyllabusVersion.source_version_id.in_(user_version_ids))
            .values(source_version_id=None)
        )
        db.execute(delete(SyllabusVersion).where(SyllabusVersion.id.in_(user_version_ids)))
    if owned_syllabus_ids:
        db.execute(delete(Syllabus).where(Syllabus.id.in_(owned_syllabus_ids)))

    db.execute(delete(PersonalEvent).where(PersonalEvent.user_id == user_id))
    db.execute(delete(SavedPublicEvent).where(SavedPublicEvent.user_id == user_id))
    authored_event_ids = list(
        db.scalars(select(PublicEvent.id).where(PublicEvent.author_id == user_id)).all()
    )
    if authored_event_ids:
        db.execute(
            update(PublicEvent)
            .where(PublicEvent.possible_duplicate_of.in_(authored_event_ids))
            .values(possible_duplicate_of=None)
        )
    db.execute(
        update(PublicEvent)
        .where(PublicEvent.moderated_by == user_id)
        .values(moderated_by=None)
    )
    db.execute(delete(PublicEvent).where(PublicEvent.author_id == user_id))
    db.execute(delete(ClassFollow).where(ClassFollow.user_id == user_id))
    db.execute(delete(GoogleCalendarOAuthState).where(GoogleCalendarOAuthState.user_id == user_id))
    db.execute(delete(GoogleCalendarConnection).where(GoogleCalendarConnection.user_id == user_id))
    db.execute(delete(TermAcceptance).where(TermAcceptance.user_id == user_id))
    db.execute(delete(Consent).where(Consent.user_id == user_id))
    db.execute(delete(Profile).where(Profile.id == user_id))

    record = db.get(AccountDeletionRecord, deletion_id)
    if record is not None:
        record.status = "concluida"
        record.completed_at = _utcnow()
        record.removed_storage_files = max(0, removed_storage_files)
    db.commit()
