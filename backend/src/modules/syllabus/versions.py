"""Versões privadas para o snapshot autorizado, sob lock do plano."""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select

from src.database.models import CandidateVote, Profile, SyllabusCandidate, SyllabusVersion

SHARED_CONTENT_NOTICE = (
    "Vínculo autodeclarado com a turma. Apenas avaliações revisadas e compartilhadas "
    "voluntariamente ficam visíveis aos seguidores; o PDF original é descartado após a "
    "extração local e a votação indica concordância ou divergência sem alterar datas "
    "automaticamente nem servir como prova oficial."
)


def utc_timestamp(value: datetime | None) -> float:
    if value is None:
        return 0.0
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc).timestamp()
    return value.astimezone(timezone.utc).timestamp()


def to_public_vote_label(db_value: str | None) -> str | None:
    if db_value in {"confirma", "confirm"}:
        return "confirm"
    if db_value in {"contesta", "contest"}:
        return "contest"
    return None


def summarize_version_votes(
    candidate_ids: list[UUID],
    votes_by_candidate: dict[UUID, list[CandidateVote]],
    current_user_id: UUID,
) -> tuple[int, int, str | None]:
    """Agrega votos por conta em uma versão usando o voto mais recente de cada usuário."""
    latest_by_user: dict[UUID, CandidateVote] = {}
    for cid in candidate_ids:
        for vote in votes_by_candidate.get(cid, ()):
            prev = latest_by_user.get(vote.user_id)
            if prev is None or (
                utc_timestamp(vote.updated_at or vote.created_at) >= utc_timestamp(prev.updated_at or prev.created_at)
            ):
                latest_by_user[vote.user_id] = vote
    confirm_count = sum(1 for vote in latest_by_user.values() if vote.value == "confirma")
    contest_count = sum(1 for vote in latest_by_user.values() if vote.value == "contesta")
    my_vote_row = latest_by_user.get(current_user_id)
    return confirm_count, contest_count, (my_vote_row.value if my_vote_row else None)



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
