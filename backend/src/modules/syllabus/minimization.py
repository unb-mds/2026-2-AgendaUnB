"""Minimização determinística do texto que será apresentado para revisão."""

import re


IDENTIFIER = "[identificador removido]"
EMAIL = "[email removido]"
PHONE = "[telefone removido]"

SPACE = r"[^\S\r\n\t]"
FIELD = rf"{SPACE}*[:=·–—-]{SPACE}*"
# Duas colunas podem ser separadas por espaços ou tabs. Exportações de PDF
# também podem quebrar uma linha imediatamente após o rótulo.
NAME_SEPARATOR = rf"(?:{FIELD}(?:\r?\n{SPACE}*)?|{SPACE}*[\t|]{SPACE}*|{SPACE}{{2,}})"
ACADEMIC_LABEL = (
    r"disciplinas?|mat[eé]rias?|turmas?|c[oó]digo|semestre|per[ií]odo|"
    r"avalia(?:ç|c)[aã]o|provas?|trabalhos?|p[1-9]|datas?|hor[aá]rios?|"
    r"salas?|audit[oó]rios?|blocos?|laborat[oó]rios?|campus|local"
)
CONTACT_LABEL = r"e-?mail|telefone|whats(?:app)?|celular|cpf|rg|siape|matr[ií]cula|contatos?"
NAME_WORD = r"(?:[A-ZÀ-ÖØ-Þ]\.|[A-ZÀ-ÖØ-Þ][^\W\d_]*(?:[’'-][^\W\d_]+)*)"
NAME_PART = rf"(?!(?i:{ACADEMIC_LABEL}|{CONTACT_LABEL}|nascimento|comparecer[aá])\b){NAME_WORD}"
NAME_TAIL = rf"{SPACE}+(?:(?i:da|das|de|do|dos|e){SPACE}+)?{NAME_PART}"
NAME = rf"{NAME_PART}(?:{NAME_TAIL}){{0,11}}"
FULL_ROLE = (
    r"professor(?:\(a\)|a?s?|es|as)|docente(?:\(s\)|s)?|monitor(?:\(a\)|a?s?|es|as)|"
    r"alun(?:[oa](?:\(a\))?|\(a\))s?|discente(?:\(s\)|s)?|"
    rf"coordenador(?:\(a\)|a?s?|es|as)|nome{SPACE}+completo"
)
SHORT_ROLE = r"prof(?:a|ª|s)?\.|dr(?:a|ª)?\."
RESPONSIBLE = rf"(?:{SPACE}+respons[aá]ve(?:l|is))?"
NAME_FIELD_END = rf"(?={SPACE}*(?:[\r\n\t|;,]|$))"
LOWERCASE_NAME = rf"(?i:{NAME}){NAME_FIELD_END}"
PHONE_LABEL = r"telefones?|tel\.?|celular|fone|whats(?:app)?"
DDD = r"(?:\([1-9]\d\)|[1-9]\d)"
PHONE_SEPARATOR = rf"(?:{SPACE}*[-.‐‑–—]{SPACE}*|{SPACE}+)"
PHONE_NUMBER = rf"9?\d{{4}}{PHONE_SEPARATOR}\d{{4}}"
FORMATTED_PHONE = rf"(?:(?:\+55{PHONE_SEPARATOR}?)?{DDD}{PHONE_SEPARATOR}?{PHONE_NUMBER}|\+55[1-9]\d9?\d{{8}})"
LABELED_PHONE = rf"(?:\+?55{PHONE_SEPARATOR}?)?(?:{DDD}{PHONE_SEPARATOR}?)?9?\d{{4}}{PHONE_SEPARATOR}?\d{{4}}"
CPF_FORMATTED = r"\d{3}\.\d{3}\.\d{3}-\d{2}"
CPF_VALUE = rf"(?:{CPF_FORMATTED}|\d{{3}}{SPACE}+\d{{3}}{SPACE}+\d{{3}}{SPACE}+\d{{2}}|\d{{11}})"
BARE_CPF = re.compile(r"(?<![\w/])[0-9]{11}(?!\w|[./-]\d)")
ACADEMIC_NUMBER_LABEL = re.compile(
    rf"\b(?:c[oó]digo(?:{SPACE}+(?:d[aeo]{SPACE}+)?(?:disciplina|turma))?|turma|disciplina)"
    rf"{SPACE}*(?:[:=]{SPACE}*)?$", re.I,
)
RG_VALUE = r"(?:\d{1,2}\.\d{3}\.\d{3}(?:-?[\dX])?|\d{7,9}(?:-?[\dX])?|\d{6,8}-[\dX])"
NUMBER_LABEL = rf"(?:{SPACE}+(?:n[º°.]|n[uú]mero))?"
VALUE_SEPARATOR = rf"(?:{NAME_SEPARATOR}|{SPACE}+)"
END_NUMBER = r"(?!\w|[./-]\d)"
# A forma com barra da UnB tem ano de ingresso em dois dígitos.
UNB_MATRICULA = rf"\d{{2}}{SPACE}*/{SPACE}*\d{{7}}"
MATRICULA = rf"(?:{UNB_MATRICULA}|\d{{9}})"
BIRTH_LABEL = rf"(?:(?:data{SPACE}+(?:de{SPACE}+)?)?nascimento|nascid[ao]{SPACE}+em)"
BIRTH_DATE = (
    rf"(?:\d{{4}}-\d{{2}}-\d{{2}}|\d{{1,2}}[/.-]\d{{1,2}}[/.-](?:\d{{4}}|\d{{2}})"
    rf"|\d{{1,2}}{SPACE}+de{SPACE}+[a-zç]+{SPACE}+de{SPACE}+\d{{4}})"
)
WEB_SCHEME = r"(?:https?://)?(?:www\.)?"
URL_END = r"""[^\s<>"'|()\[\]]*[^\s<>"'|()\[\].,;!?]"""
PERSONAL_PROFILE = (
    r"(?:lattes\.cnpq\.br/|buscatextual\.cnpq\.br/buscatextual/visualizacv\.do\?"
    r"|(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|pub)/)"
)
PERSONAL_SITE = rf"(?:site|link|blog|p[aá]gina|perfil){SPACE}+(?:pessoal|particular)"
WHATSAPP_LINK = r"(?:wa\.me/\d|(?:api\.|web\.)?whatsapp\.com/send\?)"
HOME_LABEL = (
    rf"(?:endere[cç]o{SPACE}+(?:residencial|pessoal|particular|(?:da|de){SPACE}+resid[eê]ncia)"
    rf"|resid[eê]ncia{SPACE}+(?:em|d[oea])|mora{SPACE}+em)"
)
ADDRESS_PART = r"[^\r\n\t|;]"
ADDRESS_END = rf"(?=(?:{SPACE}*[,–—]{SPACE}*|{SPACE}+)(?:{ACADEMIC_LABEL}|{CONTACT_LABEL})\b|[.!?](?:\s|$))"
HOME_VALUE = (
    rf"\w(?:(?!{ADDRESS_END}){ADDRESS_PART}){{2,199}}?(?<!\s)"
    rf"(?={ADDRESS_END}|{SPACE}*(?:[\r\n\t|;]|$))"
)

RULES = (
    (re.compile(rf"(?<![\w./@]){WEB_SCHEME}{PERSONAL_PROFILE}{URL_END}", re.I), IDENTIFIER),
    (re.compile(rf"(?<!\w){PERSONAL_SITE}{VALUE_SEPARATOR}"
                rf"(?P<value>{WEB_SCHEME}(?:[a-z\d-]+\.)+[a-z]{{2,}}(?:[/#?]{URL_END})?)", re.I), IDENTIFIER),
    (re.compile(rf"(?<![\w./@]){WEB_SCHEME}{WHATSAPP_LINK}(?:{URL_END})?", re.I), PHONE),
    (re.compile(rf"(?<!\w){HOME_LABEL}\b{VALUE_SEPARATOR}(?P<value>{HOME_VALUE})", re.I), IDENTIFIER),
    (re.compile(rf"(?<!\w)(?i:(?:{FULL_ROLE}){RESPONSIBLE})(?!\w){NAME_SEPARATOR}"
                rf"(?:(?i:{SHORT_ROLE}){SPACE}+)*(?P<value>{LOWERCASE_NAME}|{NAME})(?!\w|@)"), IDENTIFIER),
    (re.compile(rf"(?m)^{SPACE}*(?i:{FULL_ROLE})(?!\w)(?:{SPACE}*\r?\n{SPACE}*|{SPACE}+)"
                rf"(?P<value>{NAME}){NAME_FIELD_END}"), IDENTIFIER),
    (re.compile(rf"(?<!\w)(?i:{FULL_ROLE})(?!\w){SPACE}+(?P<value>{NAME_PART}(?:{NAME_TAIL}){{1,11}})"
                r"(?!\w|@)"), IDENTIFIER),
    (re.compile(rf"(?<!\w)(?i:{SHORT_ROLE})"
                rf"(?:{FIELD}|{SPACE}+)(?P<value>{NAME})(?!\w|@)"), IDENTIFIER),
    (re.compile(rf"(?<!\w){BIRTH_LABEL}(?!\w){VALUE_SEPARATOR}(?P<value>{BIRTH_DATE}){END_NUMBER}",
                re.I), IDENTIFIER),
    (re.compile(r"(?<![\w.+%-])[\w.+%'-]{1,64}@(?:[a-z\d-]{1,63}\.){1,12}[a-z]{2,63}(?![\w-])", re.I), EMAIL),
    (re.compile(rf"(?<![\w+\d(]){FORMATTED_PHONE}(?![\w\d]|[.-]\d)"), PHONE),
    (re.compile(rf"(?<!\w)(?:{PHONE_LABEL})(?!\w)(?:{NAME_SEPARATOR}|{SPACE}+)"
                rf"(?P<value>{LABELED_PHONE})(?![\w\d]|[./-]\d)", re.I), PHONE),
    (re.compile(rf"(?<!\w){CPF_FORMATTED}(?!\w)"), IDENTIFIER),
    (re.compile(rf"(?<!\w)cpf{NUMBER_LABEL}{VALUE_SEPARATOR}(?P<value>{CPF_VALUE}){END_NUMBER}", re.I), IDENTIFIER),
    (re.compile(rf"(?<!\w)(?:r\.?g\.?|registro geral){NUMBER_LABEL}{VALUE_SEPARATOR}"
                rf"(?P<value>{RG_VALUE}){END_NUMBER}", re.I), IDENTIFIER),
    (re.compile(rf"(?<![\w/]){UNB_MATRICULA}{END_NUMBER}"), IDENTIFIER),
    (re.compile(rf"(?<!\w)matr[ií]cula(?:{SPACE}+unb)?{NUMBER_LABEL}{VALUE_SEPARATOR}"
                rf"(?P<value>{MATRICULA}){END_NUMBER}", re.I), IDENTIFIER),
    (re.compile(rf"(?<!\w)(?:matr[ií]cula{SPACE}+)?siape{NUMBER_LABEL}{VALUE_SEPARATOR}"
                rf"(?P<value>\d{{6,8}}){END_NUMBER}", re.I), IDENTIFIER),
)


def _valid_cpf(number: str) -> bool:
    digits = [int(digit) for digit in number]
    if len(set(digits)) == 1:
        return False
    for length in (9, 10):
        total = sum(digit * weight for digit, weight in zip(digits, range(length + 1, 1, -1)))
        if (total * 10 % 11) % 10 != digits[length]:
            return False
    return True


def minimize_with_count(text: str) -> tuple[str, int]:
    # Encontre os trechos no original, sem reconhecer partes das próprias máscaras.
    spans = []
    for pattern, placeholder in RULES:
        for match in pattern.finditer(text):
            start, end = match.span("value" if "value" in pattern.groupindex else 0)
            spans.append((start, end, placeholder))
    for match in BARE_CPF.finditer(text):
        start, end = match.span()
        if _valid_cpf(match[0]) and not ACADEMIC_NUMBER_LABEL.search(text, max(0, start - 64), start):
            spans.append((start, end, IDENTIFIER))

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
