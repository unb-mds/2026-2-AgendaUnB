"""Minimização determinística do texto que será apresentado para revisão."""

import re


IDENTIFIER = "[identificador removido]"
EMAIL = "[email removido]"
PHONE = "[telefone removido]"

SPACE = r"[^\S\r\n\t]"
FIELD = rf"{SPACE}*[:=·–—-]{SPACE}*"
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

RULES = (
    (re.compile(rf"(?<!\w)(?i:{FULL_ROLE})(?!\w){FIELD}(?P<value>{NAME})(?!\w|@)"), IDENTIFIER),
    (re.compile(rf"(?<!\w)(?i:prof(?:a|ª)?\.|dr(?:a|ª)?\.)"
                rf"(?:{FIELD}|{SPACE}+)(?P<value>{NAME})(?!\w|@)"), IDENTIFIER),
    (re.compile(r"^(?:matr[ií]cula|cpf|nascimento)\s*[:=].*$", re.I | re.M), IDENTIFIER),
    (re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}"), EMAIL),
    (re.compile(r"(?<!\d)(?:\d{3}[.]\d{3}[.]\d{3}-\d{2}|\d{9,11})(?!\d)"), IDENTIFIER),
    (re.compile(r"(?:\+55\s*)?\(?\d{2}\)?[ -]\d{4,5}-\d{4}"), PHONE),
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
