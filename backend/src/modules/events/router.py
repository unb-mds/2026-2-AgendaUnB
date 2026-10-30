from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from src.database.connection import get_db
from src.database.models import Campus, Category, PersonalEvent, PublicEvent, SavedPublicEvent
from src.middlewares.auth import CurrentUser, get_current_user, require_event_manager
from src.modules.events.schemas import (
    EventCreate,
    EventRead,
    EventUpdate,
    PersonalEventCreate,
    PersonalEventRead,
    PersonalEventOriginRead,
    PersonalEventUpdate,
    SavedEventStatus,
)

router = APIRouter(tags=["events"])


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


def _public_read(event: PublicEvent) -> EventRead:
    return EventRead(
        id=event.id,
        title=event.title,
        description=event.description,
        starts_at=event.starts_at,
        campus=event.campus.nome if event.campus else None,
        category=event.category.nome if event.category else None,
        location=event.location,
        external_url=event.external_url,
        organizer_name=event.author.nome_completo if event.author else None,
        organizer_avatar=event.author.avatar_url if event.author else None,
    )


def _personal_read(event: PersonalEvent) -> PersonalEventRead:
    return PersonalEventRead(
        id=event.id,
        title=event.title,
        description=event.description,
        starts_at=event.starts_at,
        campus=event.campus.nome if event.campus else None,
        category=event.category.nome if event.category else None,
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


@router.get("/events", response_model=list[EventRead])
def list_public_events(
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
        statement = statement.where(PublicEvent.starts_at >= start_date)
    if end_date:
        statement = statement.where(PublicEvent.starts_at <= end_date)
    if search:
        statement = statement.where(PublicEvent.title.ilike(f"%{search.strip()}%"))

    events = db.scalars(
        statement.order_by(PublicEvent.starts_at.asc()).limit(limit).offset(offset)
    ).all()
    return [_public_read(event) for event in events]


@router.get("/events/{event_id}", response_model=EventRead)
def get_public_event(
    event_id: UUID,
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
    return _public_read(event)


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


@router.delete("/events/{event_id}", status_code=204)
def delete_public_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    _current_user: CurrentUser = Depends(require_event_manager),
) -> Response:
    event = db.get(PublicEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Evento não encontrado")
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
    event = PublicEvent(
        author_id=current_user.id,
        title=payload.title,
        description=payload.description or "",
        starts_at=payload.starts_at,
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
        campus_id=_campus_id(db, payload.campus),
        category_id=_category_id(db, payload.category),
    )
    db.add(event)
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
    event.campus_id = _campus_id(db, payload.campus)
    event.category_id = _category_id(db, payload.category)
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
    db.delete(event)
    db.commit()
    return Response(status_code=204)
