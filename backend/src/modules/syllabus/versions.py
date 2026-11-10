"""Versões privadas para o snapshot autorizado, sob lock do plano."""
from sqlalchemy import select

from src.database.models import Profile, SyllabusCandidate, SyllabusVersion


def private_version(db, plan, *, new_analysis=False):
    latest = db.scalar(select(SyllabusVersion).where(
        SyllabusVersion.syllabus_id == plan.id
    ).order_by(SyllabusVersion.number.desc()).limit(1))
    occupied = latest is not None and db.scalar(select(SyllabusCandidate.id).where(
        SyllabusCandidate.version_id == latest.id).limit(1)) is not None
    if latest is None or new_analysis or occupied or latest.visibility != "privada":
        latest = SyllabusVersion(
            syllabus_id=plan.id, number=(latest.number + 1 if latest else 1),
            author_id=plan.user_id,
            author_role=db.scalar(select(Profile.papel).where(Profile.id == plan.user_id)) or "student",
            visibility="privada", institutional_provenance=False,
        )
        db.add(latest)
        db.flush()
    return latest
