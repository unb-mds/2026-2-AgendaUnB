import re
import unicodedata
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload
from src.database.connection import get_db
from src.database.models import (
    CandidateVote,
    CatalogSync,
    ClassFollow,
    ClassOffering,
    PersonalEvent,
    Profile,
    Subject,
    Syllabus,
    SyllabusCandidate,
    SyllabusVersion,
)
from src.middlewares.auth import CurrentUser, get_current_user
from src.modules.classes.schemas import CatalogFilters, OfferingList, OfferingRead, FollowedList, SharedPlanList
from src.modules.classes.services import available_offering, metadata, offering_read, publication
from src.modules.syllabus.versions import SHARED_CONTENT_NOTICE, summarize_version_votes, utc_timestamp

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
            return func.lower(func.translate(column, source, target))
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

def _dt_key(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.astimezone(timezone.utc).isoformat()


def _candidate_changed(candidate: SyllabusCandidate, origin_candidate: SyllabusCandidate | None, event: PersonalEvent) -> bool:
    if origin_candidate is not None:
        return (
            (candidate.title or "").strip() != (origin_candidate.title or "").strip()
            or candidate.kind != origin_candidate.kind
            or candidate.data_sugerida != origin_candidate.data_sugerida
            or candidate.hora_sugerida != origin_candidate.hora_sugerida
            or _dt_key(candidate.starts_at) != _dt_key(origin_candidate.starts_at)
        )
    return (candidate.title or "").strip() != (event.title or "").strip()


@router.get("/class-offerings/{offering_id}/shared-plans", response_model=SharedPlanList)
def shared_plans(offering_id: UUID, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0),
                 user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.get(ClassFollow, (user.id, offering_id)) is None:
        raise HTTPException(403, "Siga a turma para consultar os planos compartilhados.")
    versions = db.scalars(
        select(SyllabusVersion)
        .join(Syllabus, Syllabus.id == SyllabusVersion.syllabus_id)
        .where(Syllabus.offering_id == offering_id, SyllabusVersion.visibility == "compartilhada")
    ).all()
    total = len(versions)
    if not versions:
        return {
            "membership_type": "autodeclarado",
            "shared_content_notice": SHARED_CONTENT_NOTICE,
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }

    version_ids = [v.id for v in versions]
    syllabus_ids = list({v.syllabus_id for v in versions})
    author_ids = list({v.author_id for v in versions})
    source_ids = [v.source_version_id for v in versions if v.source_version_id is not None]

    profiles = db.scalars(select(Profile).where(Profile.id.in_(author_ids))).all()
    author_names = {p.id: p.nome_completo for p in profiles}

    ref_version_ids = list({*version_ids, *source_ids})
    user_events = db.scalars(
        select(PersonalEvent).where(
            PersonalEvent.user_id == user.id,
            PersonalEvent.origin_syllabus_id.in_(syllabus_ids),
        )
    ).all()
    origin_candidate_ids = [ev.origin_candidate_id for ev in user_events if ev.origin_candidate_id is not None]
    for ev in user_events:
        if ev.origin_version_id is not None:
            ref_version_ids.append(ev.origin_version_id)
    ref_versions = db.scalars(select(SyllabusVersion).where(SyllabusVersion.id.in_(set(ref_version_ids)))).all()
    version_numbers = {v.id: v.number for v in ref_versions}

    origin_candidates = (
        db.scalars(select(SyllabusCandidate).where(SyllabusCandidate.id.in_(origin_candidate_ids))).all()
        if origin_candidate_ids else []
    )
    origin_candidates_by_id = {c.id: c for c in origin_candidates}

    candidates = db.scalars(
        select(SyllabusCandidate)
        .where(SyllabusCandidate.version_id.in_(version_ids), SyllabusCandidate.status != "descartado")
        .order_by(
            SyllabusCandidate.order.asc().nulls_last(),
            SyllabusCandidate.source_page.asc().nulls_last(),
            SyllabusCandidate.id.asc(),
        )
    ).all()
    candidates_by_version: dict[UUID, list[SyllabusCandidate]] = {}
    candidate_ids = []
    for c in candidates:
        candidates_by_version.setdefault(c.version_id, []).append(c)
        candidate_ids.append(c.id)

    votes = (
        db.scalars(select(CandidateVote).where(CandidateVote.candidate_id.in_(candidate_ids))).all()
        if candidate_ids else []
    )
    votes_by_candidate: dict[UUID, list[CandidateVote]] = {}
    for vote in votes:
        votes_by_candidate.setdefault(vote.candidate_id, []).append(vote)

    events_by_syllabus: dict[UUID, list[PersonalEvent]] = {}
    for ev in user_events:
        if ev.origin_syllabus_id is not None:
            events_by_syllabus.setdefault(ev.origin_syllabus_id, []).append(ev)

    built = []
    for version in versions:
        v_candidates = candidates_by_version.get(version.id, [])
        v_candidate_ids = [c.id for c in v_candidates]
        confirm_count, contest_count, my_vote = summarize_version_votes(v_candidate_ids, votes_by_candidate, user.id)

        syllabus_events = events_by_syllabus.get(version.syllabus_id, [])
        events_by_candidate = {ev.origin_candidate_id: ev for ev in syllabus_events if ev.origin_candidate_id is not None}
        events_by_order: dict[int, tuple[PersonalEvent, SyllabusCandidate]] = {}
        for ev in syllabus_events:
            orig_c = origin_candidates_by_id.get(ev.origin_candidate_id) if ev.origin_candidate_id else None
            if orig_c is not None and orig_c.order is not None:
                events_by_order[orig_c.order] = (ev, orig_c)

        candidate_reads = []
        any_modified = False
        present_orders = set()
        for c in v_candidates:
            if c.order is not None:
                present_orders.add(c.order)
            c_votes = votes_by_candidate.get(c.id, [])
            c_confirm = sum(1 for vote in c_votes if vote.value == "confirma")
            c_contest = sum(1 for vote in c_votes if vote.value == "contesta")
            c_my_vote = next((vote.value for vote in c_votes if vote.user_id == user.id), None)

            imported = False
            modified_since_import = False
            if c.id in events_by_candidate:
                imported = True
            elif c.order is not None and c.order in events_by_order:
                matched_event, origin_cand = events_by_order[c.order]
                if matched_event.origin_version_id == version.id:
                    imported = True
                else:
                    changed = _candidate_changed(c, origin_cand, matched_event)
                    modified_since_import = changed
                    imported = not changed
                    if changed:
                        any_modified = True

            candidate_reads.append({
                "id": c.id,
                "title": c.title,
                "type": c.kind,
                "starts_at": c.starts_at,
                "suggested_date": c.data_sugerida,
                "suggested_time": c.hora_sugerida,
                "ambiguous": c.ambiguous,
                "ambiguous_fields": list(c.campos_ambiguos or []),
                "source_page": c.source_page,
                "source_excerpt": c.source_excerpt,
                "order": c.order,
                "imported": imported,
                "modified_since_import": modified_since_import,
                "confirm_count": c_confirm,
                "contest_count": c_contest,
                "divergent": c_contest > 0,
                "my_vote": c_my_vote,
            })

        imported_versions = {ev.origin_version_id for ev in syllabus_events if ev.origin_version_id is not None}
        imported_from_version_number = (
            max((version_numbers.get(vid, 0) for vid in imported_versions), default=0)
            if imported_versions else None
        )
        any_removed = any(order not in present_orders for order in events_by_order)
        has_imported_update = bool(
            imported_versions
            and version.id not in imported_versions
            and version.number > (imported_from_version_number or 0)
            and (any_modified or any_removed)
        )

        updated_at = version.shared_at or version.created_at
        built.append({
            "id": version.id,
            "syllabus_id": version.syllabus_id,
            "offering_id": offering_id,
            "number": version.number,
            "author_id": version.author_id,
            "author_name": author_names.get(version.author_id),
            "author_role": version.author_role,
            "source_version_id": version.source_version_id,
            "source_version_number": version_numbers.get(version.source_version_id) if version.source_version_id else None,
            "institutional_provenance": version.institutional_provenance,
            "institutional_source_url": version.institutional_source_url,
            "created_at": version.created_at,
            "shared_at": version.shared_at,
            "updated_at": updated_at,
            "confirm_count": confirm_count,
            "contest_count": contest_count,
            "divergent": contest_count > 0,
            "my_vote": my_vote,
            "is_default": False,
            "can_withdraw": version.author_id == user.id or user.role == "admin",
            "can_edit": True,
            "has_imported_update": has_imported_update,
            "imported_from_version_number": imported_from_version_number if has_imported_update else None,
            "candidates": candidate_reads,
        })

    built.sort(
        key=lambda item: (
            -item["confirm_count"],
            -utc_timestamp(item["updated_at"]),
            -item["number"],
            str(item["id"]),
        )
    )
    if built:
        built[0]["is_default"] = True

    return {
        "membership_type": "autodeclarado",
        "shared_content_notice": SHARED_CONTENT_NOTICE,
        "items": built[offset : offset + limit],
        "total": total,
        "limit": limit,
        "offset": offset,
    }
