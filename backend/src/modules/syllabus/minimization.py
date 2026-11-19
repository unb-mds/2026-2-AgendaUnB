"""Minimização determinística do texto que será apresentado para revisão."""

import re


IDENTIFIER = "[identificador removido]"
EMAIL = "[email removido]"
PHONE = "[telefone removido]"

RULES = (
    (re.compile(r"^(?:professor(?:a)?|docente|aluno(?:a)?|discente|nome|matr[ií]cula|cpf|nascimento)\s*[:=].*$", re.I | re.M), IDENTIFIER),
    (re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}"), EMAIL),
    (re.compile(r"(?<!\d)(?:\d{3}[.]\d{3}[.]\d{3}-\d{2}|\d{9,11})(?!\d)"), IDENTIFIER),
    (re.compile(r"(?:\+55\s*)?\(?\d{2}\)?[ -]\d{4,5}-\d{4}"), PHONE),
)


def minimize(text: str) -> str:
    for pattern, placeholder in RULES:
        text = pattern.sub(placeholder, text)
    return text
