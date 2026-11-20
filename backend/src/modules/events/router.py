from datetime import datetime, timedelta, timezone
from typing import Annotated
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, or_, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.database.connection import get_db
from src.database.models import (
    Campus,
    Category,
    EventClick,
    PersonalEvent,
    PublicEvent,
    Reminder,
    SavedPublicEvent,
)
from src.middlewares.auth import CurrentUser, get_current_user, require_admin, require_event_manager
from src.middlewares.security import escape_like
from src.modules.events.schemas import (
    CategoryCreate,
    CategoryRead,
    EventCreate,
    EventRead,
    EventUpdate,
    OutboundClickCreate,
    OutboundClickRead,
    PersonalEventCreate,
    PersonalEventOriginRead,
    PersonalEventRead,
    PersonalEventUpdate,
    SavedEventStatus,
)

router = APIRouter(tags=["events"])
PUBLIC_EVENTS_CACHE_CONTROL = "public, max-age=60, s-maxage=300, stale-while-revalidate=600"

# Cada sugestão ocupa a fila de moderação e gera notificação. O teto impede
# que uma única conta inunde a fila; decididas as pendentes, a conta volta a sugerir.
MAX_PENDING_SUGGESTIONS = 10


def _category_id(db: Session, name: str | None) -> UUID | None:
    if name is None:
        return None
    category_id = db.scalar(
        select(Category.id).where(func.lower(Category.nome) == name.strip().lower())
    )
    if category_id is None:
        raise HTTPException(status_code=422, detail="Categoria não encontrada")
    return category_id


def _campus_id(db: Session, name: str | None) -> UUID | None:
    if name is None:
        return None
    campus_id = db.scalar(
        select(Campus.id).where(func.lower(Campus.nome) == name.strip().lower())
    )
    if campus_id is None:
        raise HTTPException(status_code=422, detail="Campus não encontrado")
    return campus_id


def _check_date_range(start_date: datetime | None, end_date: datetime | None) -> None:
    for name, value in (("startDate", start_date), ("endDate", end_date)):
        if value and (value.tzinfo is None or value.utcoffset() is None):
            raise HTTPException(
                status_code=422,
                detail=f"{name} deve incluir fuso horário (ISO 8601)",
            )
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail="startDate deve ser anterior ou igual a endDate",
        )


def _is_valid_http_url(url: str | None) -> bool:
    if not url or not url.strip():
        return False
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _sync_sqlite_reminder(
    db: Session,
    *,
    user_id: UUID,
    personal_event_id: UUID | None = None,
    public_event_id: UUID | None = None,
    starts_at: datetime | None = None,
) -> None:
    if db.get_bind().dialect.name == "postgresql":
        return

    filters = [
        Reminder.user_id == user_id,
        Reminder.status == "pendente",
        Reminder.personal_event_id == personal_event_id,
        Reminder.public_event_id == public_event_id,
    ]
    start_utc = _as_utc(starts_at)
    if start_utc is None:
        db.execute(delete(Reminder).where(*filters))
        return

    db.execute(delete(Reminder).where(*filters, Reminder.event_starts_at != starts_at))
    scheduled_for = start_utc - timedelta(hours=24)
    if scheduled_for <= datetime.now(timezone.utc):
        db.execute(delete(Reminder).where(*filters))
        return

    existing = db.scalar(select(Reminder).where(*filters, Reminder.event_starts_at == starts_at))
    if existing is None:
        db.add(
            Reminder(
                user_id=user_id,
                event_kind="pessoal" if personal_event_id is not None else "publico_salvo",
                personal_event_id=personal_event_id,
                public_event_id=public_event_id,
                event_starts_at=starts_at,
                scheduled_for=starts_at - timedelta(hours=24),
                status="pendente",
            )
        )


def _cancel_sqlite_pending_reminders(
    db: Session,
    *,
    user_id: UUID | None = None,
    personal_event_id: UUID | None = None,
    public_event_id: UUID | None = None,
) -> None:
    if db.get_bind().dialect.name == "postgresql":
        return
    filters = [Reminder.status == "pendente"]
    if user_id is not None:
        filters.append(Reminder.user_id == user_id)
    if personal_event_id is not None:
        filters.append(Reminder.personal_event_id == personal_event_id)
    if public_event_id is not None:
        filters.append(Reminder.public_event_id == public_event_id)
    db.execute(delete(Reminder).where(*filters))


def _public_read(event: PublicEvent) -> EventRead:
    return EventRead(
        id=event.id,
        title=event.title,
        description=event.description,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        all_day=event.all_day,
        start_date=event.start_date,
        end_date=event.end_date,
        campus=event.campus.nome if event.campus else None,
        category=event.category.nome if event.category else None,
        location=event.location,
        external_url=event.external_url,
        organizer_name=event.author.nome_completo if event.author else None,
        organizer_avatar=event.author.avatar_url if event.author else None,
        source=event.source,
        source_url=event.source_url,
        outbound_clicks_count=event.outbound_clicks_count or 0,
    )


def _personal_read(event: PersonalEvent) -> PersonalEventRead:
    return PersonalEventRead(
        id=event.id,
        title=event.title,
        description=event.description,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        all_day=event.all_day,
        start_date=event.start_date,
        end_date=event.end_date,
        campus=event.campus.nome if event.campus else None,
        category=event.category.nome if event.category else None,
        location=event.location,
        origin=(
            PersonalEventOriginRead(
                syllabusId=event.origin_syllabus_id,
                candidateId=event.origin_candidate_id,
                page=event.origin_page,
                excerpt=event.origin_excerpt,
            )
            if event.origin_syllabus_id and event.origin_candidate_id
            else None
        ),
    )


def _category_read(category: Category) -> CategoryRead:
    return CategoryRead(
        id=category.id,
        name=category.nome,
        color=category.cor or "#008bff",
    )


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryRead]:
    categories = db.scalars(
        select(Category).order_by(func.lower(Category.nome).asc(), Category.id.asc())
    ).all()
    return [_category_read(category) for category in categories]


@router.post("/categories", response_model=CategoryRead, status_code=201)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> CategoryRead:
    existing = db.scalar(
        select(Category.id).where(func.lower(Category.nome) == payload.name.strip().lower())
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Já existe uma categoria com este nome")
    category = Category(nome=payload.name.strip(), cor=payload.color)
    db.add(category)
    db.commit()
    db.refresh(category)
    return _category_read(category)


@router.delete("/categories/{category_id}", status_code=204)
def delete_category(
    category_id: UUID,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
) -> Response:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    in_use_public = db.scalar(
        select(PublicEvent.id).where(PublicEvent.category_id == category_id).limit(1)
    )
    in_use_personal = db.scalar(
        select(PersonalEvent.id).where(PersonalEvent.category_id == category_id).limit(1)
    )
    if in_use_public is not None or in_use_personal is not None:
        raise HTTPException(
            status_code=409,
            detail="Não é possível excluir uma categoria vinculada a eventos existentes",
        )
    db.delete(category)
    db.commit()
    return Response(status_code=204)


@router.get("/events", response_model=list[EventRead])
def list_public_events(
    response: Response,
    campus: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
    category: Annotated[str | None, Query(min_length=2, max_length=80)] = None,
    start_date: Annotated[datetime | None, Query(alias="startDate")] = None,
    end_date: Annotated[datetime | None, Query(alias="endDate")] = None,
    search: Annotated[str | None, Query(alias="q", min_length=1, max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
) -> list[EventRead]:
    _check_date_range(start_date, end_date)
    response.headers["Cache-Control"] = PUBLIC_EVENTS_CACHE_CONTROL
    statement = (
        select(PublicEvent)
        .where(PublicEvent.status == "aprovado")
        .options(
            joinedload(PublicEvent.campus),
            joinedload(PublicEvent.category),
            joinedload(PublicEvent.author),
        )
    )
    if campus:
        statement = statement.join(PublicEvent.campus).where(
            func.lower(Campus.nome) == campus.strip().lower()
        )
    if category:
        statement = statement.join(PublicEvent.category).where(
            func.lower(Category.nome) == category.strip().lower()
        )
    if start_date:
        # Fim exclusivo: um intervalo intersecta [start_date, ...] se ends_at > start_date;
        # sem ends_at, vale starts_at >= start_date (ADR-011).
        statement = statement.where(
            or_(
                (PublicEvent.ends_at.is_not(None)) & (PublicEvent.ends_at > start_date),
                (PublicEvent.ends_at.is_(None)) & (PublicEvent.starts_at >= start_date),
            )
        )
    if end_date:
        statement = statement.where(PublicEvent.starts_at <= end_date)
    if search:
        statement = statement.where(
            PublicEvent.title.ilike(f"%{escape_like(search.strip())}%", escape="\\")
        )

    events = db.scalars(
        statement.order_by(PublicEvent.starts_at.asc(), PublicEvent.id.asc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [_public_read(event) for event in events]


@router.get("/events/{event_id}", response_model=EventRead)
def get_public_event(
    event_id: UUID,
    response: Response,
    db: Session = Depends(get_db),
) -> EventRead:
    event = db.scalar(
        select(PublicEvent)
        .where(PublicEvent.id == event_id, PublicEvent.status == "aprovado")
        .options(
            joinedload(PublicEvent.campus),
            joinedload(PublicEvent.category),
            joinedload(PublicEvent.author),
        )
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    response.headers["Cache-Control"] = PUBLIC_EVENTS_CACHE_CONTROL
    return _public_read(event)


@router.post("/events/{event_id}/outbound-clicks", response_model=OutboundClickRead)
def register_outbound_click(
    event_id: UUID,
    payload: OutboundClickCreate,
    db: Session = Depends(get_db),
) -> OutboundClickRead:
    if db.get_bind().dialect.name == "postgresql":
        try:
            data = db.execute(
                text("select public.registrar_redirecionamento_evento(:e, :c)"),
                {"e": event_id, "c": payload.click_id},
            ).scalar_one()
            db.commit()
        except DBAPIError as exc:
            db.rollback()
            sqlstate = getattr(exc.orig, "sqlstate", None)
            if sqlstate == "P0002":
                raise HTTPException(status_code=404, detail="Evento não encontrado") from None
            if sqlstate == "22023":
                raise HTTPException(
                    status_code=422,
                    detail="Este evento não possui link oficial disponível",
                ) from None
            raise
        return OutboundClickRead(
            external_url=data["external_url"],
            outbound_clicks_count=int(data.get("outbound_clicks_count") or 0),
            incremented=bool(data.get("incremented")),
        )

    event = db.scalar(
        select(PublicEvent).where(
            PublicEvent.id == event_id,
            PublicEvent.status == "aprovado",
        )
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    if not _is_valid_http_url(event.external_url):
        raise HTTPException(
            status_code=422,
            detail="Este evento não possui link oficial disponível",
        )

    key = (event_id, payload.click_id)
    incremented = False
    if db.get(EventClick, key) is None:
        db.add(EventClick(event_id=event_id, click_id=payload.click_id))
        event.outbound_clicks_count = (event.outbound_clicks_count or 0) + 1
        try:
            db.commit()
            incremented = True
        except IntegrityError:
            db.rollback()
            event = db.scalar(
                select(PublicEvent).where(
                    PublicEvent.id == event_id,
                    PublicEvent.status == "aprovado",
                )
            )
            if event is None:
                raise HTTPException(status_code=404, detail="Evento não encontrado")

    return OutboundClickRead(
        external_url=event.external_url.strip(),
        outbound_clicks_count=event.outbound_clicks_count or 0,
        incremented=incremented,
    )


@router.post("/events", response_model=EventRead, status_code=201)
def create_public_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_event_manager),
) -> EventRead:
    event = PublicEvent(
        author_id=current_user.id,
        title=payload.title,
        description=payload.description or "",
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        all_day=payload.all_day,
        start_date=payload.start_date if payload.all_day else None,
        end_date=payload.end_date if payload.all_day else None,
        location=payload.location,
        external_url=str(payload.external_url) if payload.external_url else None,
        campus_id=_campus_id(db, payload.campus),
        category_id=_category_id(db, payload.category),
        status="aprovado",
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _public_read(event)


@router.put("/events/{event_id}", response_model=EventRead)
def update_public_event(
    event_id: UUID,
    payload: EventUpdate,
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(require_event_manager),
) -> EventRead:
    event = db.scalar(
        select(PublicEvent)
        .where(PublicEvent.id == event_id, PublicEvent.status == "aprovado")
        .options(
            joinedload(PublicEvent.campus),
            joinedload(PublicEvent.category),
            joinedload(PublicEvent.author),
        )
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")

    event.title = payload.title
    event.description = payload.description or ""
    event.starts_at = payload.starts_at
    event.ends_at = payload.ends_at
    event.all_day = payload.all_day
    event.start_date = payload.start_date if payload.all_day else None
    event.end_date = payload.end_date if payload.all_day else None
    event.location = payload.location
    event.external_url = str(payload.external_url) if payload.external_url else None
    event.campus_id = _campus_id(db, payload.campus)
    event.category_id = _category_id(db, payload.category)
    if db.get_bind().dialect.name != "postgresql":
        saved_user_ids = db.scalars(
            select(SavedPublicEvent.user_id).where(SavedPublicEvent.event_id == event_id)
        ).all()
        for uid in saved_user_ids:
            _sync_sqlite_reminder(db, user_id=uid, public_event_id=event_id, starts_at=event.starts_at)
    db.commit()
    db.expire(event, ["campus", "category"])
    updated = db.scalar(
        select(PublicEvent)
        .where(PublicEvent.id == event_id)
        .options(
            joinedload(PublicEvent.campus),
            joinedload(PublicEvent.category),
            joinedload(PublicEvent.author),
        )
    )
    return _public_read(updated)


@router.delete("/events/{event_id}", status_code=204)
def delete_public_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_event_manager),
) -> Response:
    event = db.get(PublicEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    if current_user.role != "admin" and event.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o autor ou um administrador pode excluir este evento")
    _cancel_sqlite_pending_reminders(db, public_event_id=event_id)
    db.delete(event)
    db.commit()
    return Response(status_code=204)


@router.post("/suggestions", response_model=EventRead, status_code=201)
def suggest_event(
    payload: EventCreate,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> EventRead:
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Apenas estudantes enviam sugestões")
    pending = db.scalar(
        select(func.count()).select_from(PublicEvent).where(
            PublicEvent.author_id == current_user.id, PublicEvent.status == "pendente"
        )
    ) or 0
    if pending >= MAX_PENDING_SUGGESTIONS:
        raise HTTPException(
            status_code=429,
            detail="Você já tem muitas sugestões aguardando análise. Aguarde a moderação para enviar novas.",
        )
    event = PublicEvent(
        author_id=current_user.id,
        title=payload.title,
        description=payload.description or "",
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        all_day=payload.all_day,
        start_date=payload.start_date if payload.all_day else None,
        end_date=payload.end_date if payload.all_day else None,
        location=payload.location,
        external_url=str(payload.external_url) if payload.external_url else None,
        campus_id=_campus_id(db, payload.campus),
        category_id=_category_id(db, payload.category),
        status="pendente",
    )
    # O trigger do banco registra a notificação na mesma transação.
    db.add(event)
    db.commit()
    db.refresh(event)
    return _public_read(event)


@router.get("/me/saved-events", response_model=list[EventRead])
def list_saved_events(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[EventRead]:
    events = db.scalars(
        select(PublicEvent)
        .join(SavedPublicEvent, SavedPublicEvent.event_id == PublicEvent.id)
        .where(SavedPublicEvent.user_id == current_user.id, PublicEvent.status == "aprovado")
        .options(joinedload(PublicEvent.campus), joinedload(PublicEvent.category), joinedload(PublicEvent.author))
        .order_by(PublicEvent.starts_at.asc(), PublicEvent.id.asc())
    ).all()
    return [_public_read(event) for event in events]


@router.get("/me/saved-events/{event_id}", response_model=SavedEventStatus)
def get_saved_event_status(
    event_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedEventStatus:
    saved = db.scalar(
        select(SavedPublicEvent)
        .join(PublicEvent, PublicEvent.id == SavedPublicEvent.event_id)
        .where(SavedPublicEvent.user_id == current_user.id,
               SavedPublicEvent.event_id == event_id, PublicEvent.status == "aprovado")
    )
    return SavedEventStatus(saved=saved is not None)


@router.put("/me/saved-events/{event_id}", response_model=SavedEventStatus)
def save_public_event(
    event_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedEventStatus:
    event = db.scalar(select(PublicEvent).where(
        PublicEvent.id == event_id, PublicEvent.status == "aprovado"
    ))
    if event is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
    key = (current_user.id, event_id)
    if db.get(SavedPublicEvent, key) is None:
        db.add(SavedPublicEvent(user_id=current_user.id, event_id=event_id))
        _sync_sqlite_reminder(
            db,
            user_id=current_user.id,
            public_event_id=event_id,
            starts_at=event.starts_at,
        )
        try:
            db.commit()
        except IntegrityError:
            # Duas solicitações simultâneas podem tentar inserir o mesmo vínculo.
            db.rollback()
            if db.get(SavedPublicEvent, key) is None:
                raise
    return SavedEventStatus(saved=True)


@router.delete("/me/saved-events/{event_id}", status_code=204)
def remove_saved_event(
    event_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    saved = db.get(SavedPublicEvent, (current_user.id, event_id))
    if saved is not None:
        db.delete(saved)
        _cancel_sqlite_pending_reminders(
            db,
            user_id=current_user.id,
            public_event_id=event_id,
        )
        db.commit()
    return Response(status_code=204)


@router.get("/me/events", response_model=list[PersonalEventRead])
def list_personal_events(
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PersonalEventRead]:
    events = db.scalars(
        select(PersonalEvent)
        .where(PersonalEvent.user_id == current_user.id)
        .options(joinedload(PersonalEvent.campus), joinedload(PersonalEvent.category))
        .order_by(PersonalEvent.starts_at.asc())
    ).all()
    return [_personal_read(event) for event in events]


@router.get("/me/events/{event_id}", response_model=PersonalEventRead)
def get_personal_event(
    event_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonalEventRead:
    event = db.scalar(
        select(PersonalEvent)
        .where(
            PersonalEvent.id == event_id,
            PersonalEvent.user_id == current_user.id,
        )
        .options(joinedload(PersonalEvent.campus), joinedload(PersonalEvent.category))
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Evento pessoal não encontrado")
    return _personal_read(event)


@router.post("/me/events", response_model=PersonalEventRead, status_code=201)
def create_personal_event(
    payload: PersonalEventCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonalEventRead:
    event = PersonalEvent(
        user_id=current_user.id,
        title=payload.title,
        description=payload.description,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        all_day=payload.all_day,
        start_date=payload.start_date if payload.all_day else None,
        end_date=payload.end_date if payload.all_day else None,
        location=payload.location,
        campus_id=_campus_id(db, payload.campus),
        category_id=_category_id(db, payload.category),
    )
    db.add(event)
    db.flush()
    _sync_sqlite_reminder(
        db,
        user_id=current_user.id,
        personal_event_id=event.id,
        starts_at=event.starts_at,
    )
    db.commit()
    db.refresh(event)
    return _personal_read(event)


@router.put("/me/events/{event_id}", response_model=PersonalEventRead)
def update_personal_event(
    event_id: UUID,
    payload: PersonalEventUpdate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonalEventRead:
    event = db.scalar(
        select(PersonalEvent).where(
            PersonalEvent.id == event_id,
            PersonalEvent.user_id == current_user.id,
        )
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Evento pessoal não encontrado")

    event.title = payload.title
    event.description = payload.description
    event.starts_at = payload.starts_at
    event.ends_at = payload.ends_at
    event.all_day = payload.all_day
    event.start_date = payload.start_date if payload.all_day else None
    event.end_date = payload.end_date if payload.all_day else None
    event.location = payload.location
    event.campus_id = _campus_id(db, payload.campus)
    event.category_id = _category_id(db, payload.category)
    _sync_sqlite_reminder(
        db,
        user_id=current_user.id,
        personal_event_id=event.id,
        starts_at=event.starts_at,
    )
    db.commit()
    db.refresh(event)
    return _personal_read(event)


@router.delete("/me/events/{event_id}", status_code=204)
def delete_personal_event(
    event_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    event = db.scalar(
        select(PersonalEvent).where(
            PersonalEvent.id == event_id,
            PersonalEvent.user_id == current_user.id,
        )
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Evento pessoal não encontrado")
    _cancel_sqlite_pending_reminders(
        db,
        user_id=current_user.id,
        personal_event_id=event.id,
    )
    db.delete(event)
    db.commit()
    return Response(status_code=204)
