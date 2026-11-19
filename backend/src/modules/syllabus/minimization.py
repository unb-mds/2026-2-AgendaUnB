"""Minimização determinística do texto que será apresentado para revisão."""

import re


IDENTIFIER = "[identificador removido]"
EMAIL = "[email removido]"
PHONE = "[telefone removido]"

SPACE = r"[^\S\r\n\t]"
FIELD = rf"{SPACE}*[:=·–—-]{SPACE}*"
# Duas colunas podem ser separadas por espaços ou tabs. Exportações de PDF
# também podem quebrar uma linha imediatamente após o rótulo.
NAME_SEPARATOR = rf"(?:{FIELD}(?:\r?\n{SPACE}*)?|{SPACE}*\t+{SPACE}*|{SPACE}{{2,}})"
ACADEMIC_LABEL = (
    r"disciplinas?|mat[eé]rias?|turmas?|c[oó]digo|semestre|per[ií]odo|"
    r"avalia(?:ç|c)[aã]o|provas?|trabalhos?|p[1-9]|datas?|hor[aá]rios?|"
    r"salas?|audit[oó]rios?|blocos?|laborat[oó]rios?|campus|local"
)
CONTACT_LABEL = r"e-?mail|telefone|whats(?:app)?|celular|cpf|rg|siape|matr[ií]cula"
NAME_WORD = r"[A-ZÀ-ÖØ-Þ][^\W\d_]*(?:[’'-][^\W\d_]+)*"
NAME_PART = rf"(?!(?i:{ACADEMIC_LABEL}|{CONTACT_LABEL}|nascimento|comparecer[aá])\b){NAME_WORD}"
NAME = rf"{NAME_PART}(?:{SPACE}+(?:(?i:da|das|de|do|dos|e|d[’']){SPACE}+)?{NAME_PART}){{0,11}}"
FULL_ROLE = r"professor(?:\(a\)|[ao])?s?|docente\b(?:\(s\))?|monitor(?:\(a\)|[ao])?s?|alun(?:[oa]\(a\)|\(a\)|[oa])s?|discente(?:\(s\)|s)?|coordenador(?:\(a\)|[ao])?s?|nome\s+completo"
PHONE_LABEL = r"telefones?|tel\.?|celular|fone|whats(?:app)?"
DDD = r"(?:\([1-9]\d\)|[1-9]\d)"
PHONE_SEP = r"[^\S\r\n\t]*"
PHONE_NUMBER = rf"(?:9?\d{{4}})[ .-]\d{{4}}"
FORMATTED_PHONE = rf"(?:\+55{PHONE_SEP})?{DDD}(?:{PHONE_SEP}|[.-]){PHONE_NUMBER}"
LABELED_PHONE = rf"(?:\+?55{PHONE_SEP})?(?:{DDD}[ .-]?)?9?\d{{4}}[ .-]?\d{{4}}"

RULES = (
    (re.compile(rf"(?<!\w)(?i:{FULL_ROLE})(?!\w){NAME_SEPARATOR}(?P<value>{NAME})(?!\w|@)"), IDENTIFIER),
    (re.compile(rf"(?<!\w)(?i:prof(?:a|ª)?\.|dr(?:a|ª)?\.)"
                rf"(?:{FIELD}|{SPACE}+)(?P<value>{NAME})(?!\w|@)"), IDENTIFIER),
    (re.compile(r"^(?:matr[ií]cula|cpf|nascimento)\s*[:=].*$", re.I | re.M), IDENTIFIER),
    (re.compile(r"(?<![\w.+%-])[\w.+%'-]{1,64}@(?:[a-z\d-]{1,63}\.){1,12}[a-z]{2,63}(?![\w-])", re.I), EMAIL),
    (re.compile(rf"(?<![\w+\d(]){FORMATTED_PHONE}(?![\w\d]|[.-]\d)"), PHONE),
    (re.compile(rf"(?<!\w)(?:{PHONE_LABEL})(?!\w)(?:{NAME_SEPARATOR}|{SPACE}+)"
                rf"(?P<value>{LABELED_PHONE})(?![\w\d]|[./-]\d)", re.I), PHONE),
    (re.compile(r"(?<!\d)(?:\d{3}[.]\d{3}[.]\d{3}-\d{2}|\d{9,11})(?!\d)"), IDENTIFIER),
)


def minimize_with_count(text: str) -> tuple[str, int]:
    # Encontre os trechos no original, sem reconhecer partes das próprias máscaras.
    spans = []
    for pattern, placeholder in RULES:
        for match in pattern.finditer(text):
            start, end = match.span("value" if "value" in pattern.groupindex else 0)
            spans.append((start, end, placeholder))

    selected = []
    for start, end, placeholder in sorted(spans, key=lambda span: (span[0], -span[1])):
        if selected and start < selected[-1][1]:
            first, last, mask = selected[-1]
            selected[-1] = (first, max(last, end), mask)
        else:
            selected.append((start, end, placeholder))

    pieces = []
    cursor = 0
    for start, end, placeholder in selected:
        pieces.extend((text[cursor:start], placeholder))
        cursor = end
    pieces.append(text[cursor:])
    return "".join(pieces), len(selected)


def minimize(text: str) -> str:
    return minimize_with_count(text)[0]
