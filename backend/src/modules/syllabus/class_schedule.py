"""Leitura de horários semanais SIGAA informados no plano."""
import re
from collections.abc import Iterable
from datetime import time


# https://design.unb.br/codigos-aulas-sigaa/
_PERIOD_STARTS = {
    "M": ("08:00", "08:55", "10:00", "10:55", "12:00"),
    "T": ("12:55", "14:00", "14:55", "16:00", "16:55", "18:00"),
    "N": ("19:00", "19:50", "20:50", "21:40"),
}
_PERIOD_MINUTES = {"M": 55, "T": 55, "N": 50}
_CODE = re.compile(r"([2-7]+)([MTN])([1-6]+)")
_SCHEDULE_LINE = re.compile(
    rf"(?:(?:hor[áa]rios?(?:\s+(?:da\s+turma|(?:das?|de)\s+aulas?))?(?:\s*[:=|–—-]\s*|\s+)"
    rf"|turma\s*:?\s*\w+\s*[:=|–—-]\s*))?(?P<codes>{_CODE.pattern}(?:[\s,;|/]+{_CODE.pattern})*)\.?",
    re.IGNORECASE,
)


def _starts_by_weekday(codes: str) -> dict[int, time]:
    by_day: dict[int, set[tuple[int, int]]] = {}
    for days, shift, periods in _CODE.findall(codes.upper()):
        slots = _PERIOD_STARTS[shift]
        for period in periods:
            index = int(period) - 1
            if index >= len(slots):
                return {}
            start = time.fromisoformat(slots[index])
            start_minutes = start.hour * 60 + start.minute
            for day in days:
                # A segunda-feira é 2 no SIGAA e 0 em date.weekday().
                by_day.setdefault(int(day) - 2, set()).add((start_minutes, start_minutes + _PERIOD_MINUTES[shift]))

    starts = {}
    for day, periods in by_day.items():
        ordered = sorted(periods)
        # Entre períodos consecutivos da grade há intervalos de até 10 minutos.
        if all(start - end <= 10 for (_, end), (start, _) in zip(ordered, ordered[1:])):
            hours, minutes = divmod(ordered[0][0], 60)
            starts[day] = time(hours, minutes)
    return starts


def class_starts_in_plan(texts: Iterable[str]) -> dict[int, time] | None:
    """Sugestões por dia de date.weekday(), válidas em todas as grades declaradas."""
    starts = None
    for text in texts:
        for line in text.splitlines():
            match = _SCHEDULE_LINE.fullmatch(line.replace("**", "").strip(" \t|"))
            if match is None:
                continue
            current = _starts_by_weekday(match["codes"])
            starts = current if starts is None else {
                day: start for day, start in starts.items() if current.get(day) == start
            }
    return starts
