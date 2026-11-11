"""Leituras locais do catálogo; nenhuma chamada à origem no ciclo HTTP."""
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from sqlalchemy import select, text
from src.database.models import CatalogSync, ClassOffering


def publication(db):
    if db.bind.dialect.name == "postgresql":
        db.execute(text("select pg_advisory_xact_lock_shared(708072)"))
    result = db.scalar(select(CatalogSync).where(CatalogSync.status == "concluida").order_by(
        CatalogSync.completed_at.desc(), CatalogSync.id.desc()).limit(1))
    if result is None:
        raise HTTPException(503, "O catálogo ainda não está disponível. Cadastre um compromisso manualmente.")
    return result


def metadata(db, published):
    if db.bind.dialect.name == "postgresql":
        state = db.scalar(text("select public.estado_catalogo()"))
        return {"source_updated_at": state["atualizado_em"], "stale": state["desatualizado"]}
    latest = db.scalar(select(CatalogSync).where(CatalogSync.status != "executando").order_by(
        CatalogSync.started_at.desc(), CatalogSync.id.desc()).limit(1))
    date = published.completed_at
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    return {"source_updated_at": date, "stale": latest.status == "falha" or date < datetime.now(timezone.utc)-timedelta(hours=24)}


def available_offering(db, offering_id):
    published = publication(db)
    offer = db.scalar(select(ClassOffering).where(ClassOffering.id == offering_id,
        ClassOffering.publication_id == published.id))
    if offer is None:
        raise HTTPException(409, "Selecione uma oferta disponível no catálogo para continuar.")
    return offer


def offering_read(offer, published_id=None):
    from sqlalchemy.orm import object_session
    db = object_session(offer)
    run = db.get(CatalogSync, published_id or offer.publication_id) if db and (published_id or offer.publication_id) else None
    unit = next((u for u in (run.units if run else []) if str(u['id']) == offer.subject.unit), {})
    return {"id": offer.id, "subject_name": offer.subject.name, "subject_code": offer.subject.code,
        "class_number": offer.class_number, "year": offer.year, "semester": offer.semester,
        "unit": offer.subject.unit, "unit_name": unit.get("name"), "unit_code": unit.get("code"), "level": offer.subject.level, "teacher": offer.teacher,
        "schedule": offer.schedule, "available": offer.publication_id == published_id}
