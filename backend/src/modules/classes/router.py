import re
import unicodedata
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from src.database.connection import get_db
from src.database.models import CatalogSync, ClassFollow, ClassOffering, Subject, Syllabus, SyllabusVersion, SyllabusCandidate
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.classes.schemas import CatalogFilters, OfferingList, OfferingRead, FollowedList, SharedPlanList
from src.modules.classes.services import available_offering, metadata, offering_read, publication

def private_response(response: Response):
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(tags=["classes"], dependencies=[Depends(private_response)])


@router.get("/class-offerings/filters", response_model=CatalogFilters)
def filters(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    published = publication(db)
    return {"units": published.units, "periods": published.periods, **metadata(db, published)}


@router.get("/class-offerings", response_model=OfferingList)
def offerings(year: int | None = Query(None, ge=2000, le=2100),
              semester: int | None = Query(None, ge=1, le=2),
              unit: str | None = Query(None, min_length=1, max_length=100, pattern=r"^[^\x00-\x1f]+$"),
              subject_code: str | None = Query(None, min_length=1, max_length=30, pattern=r"^[A-Za-z0-9]+$"),
              q: str | None = Query(None, max_length=150, pattern=r"^[^\x00-\x1f]*$"),
              limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
              user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    published = publication(db)
    query = select(ClassOffering).join(Subject).where(ClassOffering.publication_id == published.id)
    if year is not None:
        query = query.where(ClassOffering.year == year)
    if semester is not None:
        query = query.where(ClassOffering.semester == semester)
    if unit:
        unit_ids = [str(u["id"]) for u in published.units if unit.strip().upper() in {str(u["id"]), (u.get("code") or "").upper()}]
        query = query.where(Subject.unit.in_(unit_ids))
    if subject_code:
        query = query.where(Subject.code == subject_code.upper())
    relevance = []
    if q and q.strip():
        needle = ''.join(c for c in unicodedata.normalize('NFD', q.strip()) if not unicodedata.combining(c)).lower()
        def folded(column):
            source = 'áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ'
            target = 'aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC'
            if db.bind.dialect.name == 'postgresql':
                return func.lower(func.translate(column, source, target))
            for old, new in zip(source, target):
                column = func.replace(column, old, new)
            return func.lower(column)
        columns = [folded(column) for column in (Subject.name, Subject.code, ClassOffering.teacher, ClassOffering.class_number)]
        terms = re.findall(r'[a-z0-9]+', needle)
        meaningful = [term for term in terms if term not in {'de', 'da', 'do', 'das', 'dos', 'e', 'a', 'o', 'em'}]
        for term in dict.fromkeys(meaningful or terms):
            # Radical leve: preserva códigos e números, mas aproxima singular/plural.
            stem = term[:-1] if len(term) > 4 and term.isalpha() and term.endswith('s') else term
            query = query.where(or_(*(column.contains(stem, autoescape=True) for column in columns)))
        if not terms:
            query = query.where(or_(*(column.contains(needle, autoescape=True) for column in columns)))
        relevance = [case(
            (columns[1] == needle, 0),
            (columns[0] == needle, 1),
            (columns[0].contains(needle, autoescape=True), 2),
            (columns[0].contains((meaningful or terms)[0] if terms else needle, autoescape=True), 3),
            else_=4)]
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    rows = db.scalars(query.options(joinedload(ClassOffering.subject)).order_by(
        *relevance, Subject.code, Subject.unit, ClassOffering.year.desc(), ClassOffering.semester.desc(), ClassOffering.class_number,
        ClassOffering.id).limit(limit).offset(offset)).all()
    return {"items": [offering_read(row, published.id) for row in rows], "total": total,
            "limit": limit, "offset": offset, **metadata(db, published)}


@router.get("/me/class-offerings", response_model=FollowedList)
def followed(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    published_id = db.scalar(select(CatalogSync.id).where(CatalogSync.status == "concluida").order_by(
        CatalogSync.completed_at.desc(), CatalogSync.id.desc()).limit(1))
    rows = db.scalars(select(ClassOffering).join(ClassFollow).where(ClassFollow.user_id == user.id)
        .options(joinedload(ClassOffering.subject)).order_by(ClassOffering.year.desc(), ClassOffering.semester.desc(), ClassOffering.id)).all()
    return {"items": [offering_read(row, published_id) for row in rows]}


@router.put("/me/class-offerings/{offering_id}", status_code=204)
def follow(offering_id: UUID, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    available_offering(db, offering_id)
    if db.get(ClassFollow, (user.id, offering_id)) is None:
        db.add(ClassFollow(user_id=user.id, offering_id=offering_id))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            if db.get(ClassFollow, (user.id, offering_id)) is None:
                raise
    return Response(status_code=204)


@router.delete("/me/class-offerings/{offering_id}", status_code=204)
def unfollow(offering_id: UUID, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    db.execute(delete(ClassFollow).where(ClassFollow.user_id == user.id, ClassFollow.offering_id == offering_id))
    db.commit()
    return Response(status_code=204)

@router.get("/class-offerings/{offering_id}", response_model=OfferingRead)
def offering(offering_id: UUID, user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(ClassOffering, offering_id)
    if row is None:
        raise HTTPException(404, "Oferta não encontrada.")
    published_id = db.scalar(select(CatalogSync.id).where(CatalogSync.status == "concluida").order_by(
        CatalogSync.completed_at.desc(), CatalogSync.id.desc()).limit(1))
    return offering_read(row, published_id)

@router.get("/class-offerings/{offering_id}/shared-plans", response_model=SharedPlanList)
def shared_plans(offering_id: UUID, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                 user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(ClassFollow, (user.id, offering_id)) is None:
        raise HTTPException(403, "Siga a turma para consultar os planos compartilhados.")
    query = select(SyllabusVersion).join(Syllabus, Syllabus.id == SyllabusVersion.syllabus_id).where(
        Syllabus.offering_id == offering_id, SyllabusVersion.visibility == "compartilhada")
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    versions = db.scalars(query.order_by(SyllabusVersion.shared_at.desc(), SyllabusVersion.id).limit(limit).offset(offset)).all()
    items = []
    for version in versions:
        candidates = db.scalars(select(SyllabusCandidate).where(SyllabusCandidate.version_id == version.id,
            SyllabusCandidate.status != "descartado").order_by(SyllabusCandidate.id)).all()
        items.append({"id": version.id, "number": version.number, "author_role": version.author_role,
            "institutional_provenance": version.institutional_provenance, "shared_at": version.shared_at,
            "candidates": [{"id": c.id, "title": c.title, "starts_at": c.starts_at,
                "suggested_date": c.data_sugerida, "ambiguous": c.ambiguous} for c in candidates]})
    return {"items": items, "total": total, "limit": limit, "offset": offset}
