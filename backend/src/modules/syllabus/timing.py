"""Timestamps persistidos em UTC, incluindo compatibilidade com SQLite de teste."""
from datetime import datetime, timezone


def duration_ms(start: datetime, end: datetime | None) -> int | None:
    if end is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return max(0, round((end - start).total_seconds() * 1000))
