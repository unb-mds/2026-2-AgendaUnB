"""Descarta PDFs originais legados do Storage após extração concluída ou falha (ADR-003)."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
import sys
from uuid import UUID

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from src.database.connection import SessionLocal
from src.database.models import Syllabus
from src.services.storage import SupabaseStorageService

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

TERMINAL_STATUSES = ("concluido", "falha")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def discard_legacy_pdfs(
    db: Session,
    storage: SupabaseStorageService,
    *,
    execute: bool = False,
    batch_size: int = 50,
) -> dict[str, int | bool]:
    if batch_size < 1 or batch_size > 500:
        raise ValueError("batch_size deve estar entre 1 e 500.")

    eligible_filter = (
        Syllabus.status.in_(TERMINAL_STATUSES)
        & or_(Syllabus.file_path.is_not(None), Syllabus.arquivo_url.is_not(None))
    )
    eligible = int(db.scalar(select(func.count()).select_from(Syllabus).where(eligible_filter)) or 0)
    if not execute:
        return {"dry_run": True, "eligible": eligible, "discarded": 0, "failed": 0}

    discarded = 0
    failed = 0
    skipped_ids: set[UUID] = set()

    while True:
        query = select(Syllabus.id).where(eligible_filter)
        if skipped_ids:
            query = query.where(Syllabus.id.notin_(skipped_ids))
        row_ids = list(
            db.scalars(
                query.order_by(Syllabus.created_at.asc(), Syllabus.id.asc()).limit(batch_size)
            ).all()
        )
        if not row_ids:
            break

        for row_id in row_ids:
            plan = db.scalar(
                select(Syllabus)
                .where(
                    Syllabus.id == row_id,
                    Syllabus.status.in_(TERMINAL_STATUSES),
                    or_(Syllabus.file_path.is_not(None), Syllabus.arquivo_url.is_not(None)),
                )
                .with_for_update(skip_locked=True)
            )
            if plan is None:
                db.rollback()
                skipped_ids.add(row_id)
                continue

            raw_path = plan.file_path or plan.arquivo_url
            object_key = storage.normalize_path(raw_path)
            if object_key and not storage.delete_file_if_present(object_key):
                db.rollback()
                skipped_ids.add(row_id)
                failed += 1
                continue

            plan.file_path = None
            plan.arquivo_url = None
            plan.discarded_at = _utcnow()
            db.commit()
            discarded += 1

    return {"dry_run": False, "eligible": eligible, "discarded": discarded, "failed": failed}


def main(argv: list[str] | None = None) -> int:
    load_dotenv(find_dotenv())
    parser = argparse.ArgumentParser(
        description="Descarta PDFs legados de planos com extração concluída ou falha."
    )
    parser.add_argument(
        "--executar",
        action="store_true",
        help="Remove os objetos do Storage e registra o descarte no banco.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Quantidade máxima de planos por lote (1 a 500).",
    )
    args = parser.parse_args(argv)
    if args.batch_size < 1 or args.batch_size > 500:
        parser.exit(2, "Informe --batch-size entre 1 e 500.\n")

    storage = SupabaseStorageService()
    try:
        with SessionLocal() as db:
            summary = discard_legacy_pdfs(
                db,
                storage,
                execute=args.executar,
                batch_size=args.batch_size,
            )
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__}), file=sys.stderr)
        return 1

    print(json.dumps(summary))
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
