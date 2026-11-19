"""Texto e sugestões não confiáveis: validar procedência antes de persistir."""
import io
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pypdf import PdfReader

from src.modules.syllabus.processing_config import ProcessingConfig, ProcessingError

VERSION = "syllabus-v4-structured-titles"
Kind = Literal["prova", "trabalho"]
AmbiguousField = Literal["titulo", "tipo", "data", "hora"]


@dataclass(frozen=True)
class TextPage:
    pagina: int | None
    texto: str


class CandidateData(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    titulo: str = Field(min_length=1, max_length=300)
    tipo: Kind
    data_sugerida: date | None = None
    hora_sugerida: time | None = None
    campos_ambiguos: list[AmbiguousField] = Field(default_factory=list, max_length=4)
    pagina_origem: int | None = Field(default=None, ge=1, le=10, strict=True)
    trecho_origem: str = Field(min_length=1, max_length=1000)

    @field_validator("data_sugerida", mode="before")
    @classmethod
    def iso_date_only(cls, value):
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)):
            raise ValueError("Data deve ser ISO ou nula.")
        return value

    @field_validator("hora_sugerida", mode="before")
    @classmethod
    def local_time_only(cls, value):
        if value is not None and (not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}(:00)?", value)):
            raise ValueError("Hora local deve ser HH:MM ou nula.")
        return value


class ExtractionData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidatos: list[CandidateData] = Field(max_length=100)


@dataclass
class ExtractionResult:
    candidates: list[CandidateData]
    unsupported_dates: int = 0


_INVISIBLE_RE = re.compile(r"[\u00ad\u200b-\u200d\ufeff]")
_DASH_RE = re.compile(r"[\u2010-\u2015\u2212]")
_TOKEN_RE = re.compile(r"[^\W_]+(?:[/:.][^\W_]+)*")


def normalize(value: str) -> str:
    cleaned = unicodedata.normalize("NFKC", value)
    cleaned = _INVISIBLE_RE.sub("", cleaned)
    cleaned = _DASH_RE.sub("-", cleaned)
    cleaned = re.sub(r"(\d)\s*/\s*(\d)", r"\1/\2", cleaned)
    return " ".join(cleaned.split()).casefold()


def _tokens(value: str) -> list[str]:
    return _TOKEN_RE.findall(normalize(value))


def _tokens_match_same_line(evidence_tokens: list[str], source_raw: str) -> bool:
    if not evidence_tokens:
        return False
    needed = set(evidence_tokens)
    for line in source_raw.splitlines():
        if needed <= set(_tokens(line)):
            return True
    return False


def _evidence_in_source(evidence_raw: str, source_raw: str, *, max_gap: int = 8, allow_same_line: bool = True) -> bool:
    norm_evidence = normalize(evidence_raw)
    norm_source = normalize(source_raw)
    if not norm_evidence:
        return False
    if norm_evidence in norm_source:
        return True
    segments = [seg.strip() for seg in re.split(r"\.{3,}|…", evidence_raw) if seg.strip()]
    seg_tokens = [toks for seg in segments if (toks := _tokens(seg))]
    source_tokens = _tokens(source_raw)
    if not seg_tokens or not source_tokens:
        return False
    pos = 0
    matched_ordered = True
    for toks in seg_tokens:
        n = len(toks)
        found_end = None
        for start in range(pos, len(source_tokens)):
            if source_tokens[start] != toks[0]:
                continue
            si = start + 1
            ti = 1
            max_end = min(len(source_tokens), start + n + max_gap)
            while ti < n and si < max_end:
                if source_tokens[si] == toks[ti]:
                    ti += 1
                si += 1
            if ti == n:
                found_end = si
                break
        if found_end is None:
            matched_ordered = False
            break
        pos = found_end
    if matched_ordered:
        return True
    if allow_same_line and len(seg_tokens) == 1:
        return _tokens_match_same_line(seg_tokens[0], source_raw)
    return False


def extract_pages(content: bytes, config: ProcessingConfig) -> list[TextPage]:
    if not content.startswith(b"%PDF-") or len(content) > 10 * 1024 * 1024:
        raise ProcessingError("pdf_invalido")
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise ProcessingError("pdf_protegido")
        if not 1 <= len(reader.pages) <= config.max_pages:
            raise ProcessingError("limite_paginas")
        pages = []
        size = 0
        for number, page in enumerate(reader.pages, 1):
            value = page.extract_text() or ""
            size += len(value.encode("utf-8"))
            if size > config.max_text_bytes:
                raise ProcessingError("limite_paginas")
            pages.append(TextPage(number, value))
    except ProcessingError:
        raise
    except Exception:
        raise ProcessingError("pdf_invalido") from None
    if not any(page.texto.strip() for page in pages):
        raise ProcessingError("pdf_sem_texto")
    return pages


MONTHS = "janeiro fevereiro março abril maio junho julho agosto setembro outubro novembro dezembro".split()
SHORT_MONTHS = "jan fev mar abr mai jun jul ago set out nov dez".split()

_TIME_EXPR = r"(\d{1,2})\s*(?::\s*(\d{2})|h(?:(?:\s*(\d{2}))?(?:\s*min\b)?|s\b|rs\b|oras?\b)(?![a-z]))"
_TIME_RE = re.compile(rf"(?<![\d:]){_TIME_EXPR}(?![\d:])", re.IGNORECASE)
_DURATION_LENGTH_RE = re.compile(
    r"\b(?:dura[çc][ãa]o(?:\s+de)?|prazo(?:\s+de)?|em\s+at[eé]|por)\s+\d{1,2}\s*(?:h\b|hs\b|horas?\b)",
    re.IGNORECASE,
)
_DURATION_RANGE_RE = re.compile(
    rf"(?<![\d:])(?:das?\s+|de\s+)?{_TIME_EXPR}\s*(?:[àa]s?|at[eé](?:\s+[àa]s?)?)\s*{_TIME_EXPR}(?![\d:])",
    re.IGNORECASE,
)
_BARE_START_DURATION_RE = re.compile(
    rf"\bdas?\s+(\d{{1,2}})\s*(?:[àa]s?|at[eé](?:\s+[àa]s?)?)\s*{_TIME_EXPR}(?![\d:])",
    re.IGNORECASE,
)
_STRUCTURED_TITLE_RE = re.compile(
    r"^(prova|avalia[çc][ãa]o|exame|trabalho|entrega|projeto|semin[áa]rio)(?:\s+(\d+))?\s*[-–—:]\s*(.+)$",
    re.IGNORECASE,
)
_STRUCTURED_PREFIX_BY_KIND = {
    "prova": {"prova", "avaliação", "avaliacao", "exame"},
    "trabalho": {"trabalho", "entrega", "projeto", "seminário", "seminario"},
}
_VERBOSE_TITLE_VERB_RE = re.compile(
    r"\b(?:ser[áa]\s+(?:realizada?|aplicada?|feita|a\s+de)|ocorrer[áa]|acontecer[áa]|foi\s+definid[ao]|marcad[ao]\s+para|est[áa]\s+agendad[ao]|encerrando\s+o\s+ciclo|teremos\s+a\s+(?:prova|avalia[çc][ãa]o))\b",
    re.IGNORECASE,
)
_SUBJECT_AFTER_ASSESSMENT_RE = re.compile(
    r"\b(?:avalia[çc][ãa]o|prova|exame|trabalho)(?:\s+(?:te[óo]ric[ao]|pr[áa]tic[ao]|escrit[ao]|regular|final|parcial|substitutiva|individual))*\s+(?:ser[áa]\s+(?:a\s+)?)?(?:de|da|do|sobre)\s+(.+)",
    re.IGNORECASE,
)
_TRAILING_CLAUSE_RE = re.compile(
    r"\s*(?:,|;|\.|(?:\b(?:ser[áa]|ocorrer[áa]|acontecer[áa]|foi\s+definid[ao]|marcad[ao]|agendad[ao]|que\s+ocorrer[áa]|no\s+dia|em\s+\d|na\s+(?:segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo|sala)|no\s+(?:audit[óo]rio|laborat[óo]rio|bloco)|das?\s+\d|[àa]s?\s+\d))).*$",
    re.IGNORECASE,
)
_EXPLICIT_FIXED_LABEL_RE = re.compile(r"\b(?:prova\s+\d+|trabalho\s+\d+|p[1-9]\b|t[1-9]\b)", re.IGNORECASE)
_ADMIN_POLICY_RE = re.compile(
    r"\b(?:pedidos?\s+de\s+segunda\s+chamada|protocolados?\s+na\s+secretaria|justificativa\s+documental|revis[ãa]o\s+de\s+men[çc][ãa]o)\b",
    re.IGNORECASE,
)


def extract_reference_year(pages: list[TextPage]) -> int | None:
    for page in pages:
        match = re.search(r"\b(20\d{2})\s*[/.-]\s*[12]\b", page.texto)
        if match:
            return int(match[1])
    for page in pages:
        match = re.search(
            r"\b(?:semestre|ano\s+letivo|per[ií]odo(?:\s+letivo)?)\b[^.\n]{0,40}\b(20\d{2})\b",
            page.texto,
            re.IGNORECASE,
        )
        if match:
            return int(match[1])
    for page in pages:
        dates = dates_in_evidence(page.texto)
        if dates:
            return min(d.year for d in dates)
    return None


def dates_in_evidence(value: str, *, default_year: int | None = None) -> set[date]:
    found = set()
    lowered = value.casefold()
    triples = [(int(y), int(m), int(d)) for d, m, y in
               re.findall(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?!\d)", lowered)]
    triples += [(int(y), int(m), int(d)) for d, m, y in
                re.findall(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)", lowered)]
    triples += [(int(y), int(m), int(d)) for y, m, d in
                re.findall(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", lowered)]
    triples += [(2000 + int(y), int(m), int(d)) for d, m, y in
                re.findall(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{2})(?!\d)", lowered)]
    triples += [(2000 + int(y), int(m), int(d)) for d, m, y in
                re.findall(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{2})(?!\d)", lowered)]
    for index, month in enumerate(MONTHS, 1):
        month_pattern = "mar[cç]o" if month == "março" else month
        triples += [(int(y), index, int(d)) for d, y in re.findall(
            rf"(?<!\d)(\d{{1,2}})[/\s-]+(?:de\s+)?{month_pattern}\b(?:,?\s*(?:de\s+)?|[/\s-]+)((?:19|20)\d{{2}})(?!\d)", lowered)]
        triples += [(2000 + int(y), index, int(d)) for d, y in re.findall(
            rf"(?<!\d)(\d{{1,2}})[/\s-]+(?:de\s+)?{month_pattern}\b(?:[/\-]|\s+de\s+)(\d{{2}})(?![\d:]|\s*h\b)", lowered)]
    for index, short_month in enumerate(SHORT_MONTHS, 1):
        triples += [(int(y), index, int(d)) for d, y in re.findall(
            rf"(?<!\d)(\d{{1,2}})[/\s-]+(?:de\s+)?{short_month}\b\.?(?:,?\s*(?:de\s+)?|[/\s-]+)((?:19|20)\d{{2}})(?!\d)", lowered)]
        triples += [(2000 + int(y), index, int(d)) for d, y in re.findall(
            rf"(?<!\d)(\d{{1,2}})[/\s-]+(?:de\s+)?{short_month}\b\.?(?:[/\-]|\s+de\s+)(\d{{2}})(?![\d:]|\s*h\b)", lowered)]
    if default_year is not None:
        triples += [(default_year, int(m), int(d)) for d, m in
                    re.findall(r"(?<!\d)(\d{1,2})/(\d{1,2})(?![/\d])", lowered)]
        year_ahead = r"(?!(?:(?:,?\s*(?:de\s+)?|[/\s-]+)(?:19|20)\d{2}\b|(?:[/\-]|\s+de\s+)\d{2}(?![\d:]|\s*h\b)))"
        for index, month in enumerate(MONTHS, 1):
            month_pattern = "mar[cç]o" if month == "março" else month
            triples += [(default_year, index, int(d)) for d in re.findall(
                rf"(?<!\d)(\d{{1,2}})\s+(?:de\s+)?{month_pattern}\b{year_ahead}", lowered)]
        for index, short_month in enumerate(SHORT_MONTHS, 1):
            triples += [(default_year, index, int(d)) for d in re.findall(
                rf"(?<!\d)(\d{{1,2}})\s+(?:de\s+)?{short_month}\b\.?(?!\.){year_ahead}", lowered)]
    for year, month, day in triples:
        try:
            found.add(date(year, month, day))
        except ValueError:
            pass
    return found


def _parse_time(hour_s: str, min1: str | None, min2: str | None) -> time | None:
    try:
        return time(int(hour_s), int(min1 or min2 or 0))
    except ValueError:
        return None


def times_in_evidence(value: str) -> set[time]:
    cleaned = _DURATION_LENGTH_RE.sub(" ", value)
    found = set()
    for match in _TIME_RE.finditer(cleaned):
        parsed = _parse_time(match[1], match[2], match[3])
        if parsed is not None:
            found.add(parsed)
    return found


def resolve_evidence_hours(value: str) -> tuple[set[time], time | None]:
    """Retorna (todos os horários encontrados, horário inicial inequívoco ou None)."""
    cleaned = _DURATION_LENGTH_RE.sub(" ", value)
    hours = times_in_evidence(cleaned)
    if not re.search(r"\bou\b", cleaned.casefold()):
        bare_matches = list(_BARE_START_DURATION_RE.finditer(cleaned))
        if len(bare_matches) == 1:
            bm = bare_matches[0]
            start_t = _parse_time(bm[1], None, None)
            end_t = _parse_time(bm[2], bm[3], bm[4])
            if start_t is not None and end_t is not None and start_t < end_t and hours == {end_t}:
                return {start_t, end_t}, start_t
    if len(hours) <= 1:
        return hours, next(iter(hours), None)
    if len(hours) == 2 and not re.search(r"\bou\b", cleaned.casefold()):
        matches = list(_DURATION_RANGE_RE.finditer(cleaned))
        if len(matches) == 1:
            m = matches[0]
            start_t = _parse_time(m[1], m[2], m[3])
            end_t = _parse_time(m[4], m[5], m[6])
            if start_t is not None and end_t is not None and start_t < end_t and {start_t, end_t} == hours:
                return hours, start_t
    return hours, None


def _title_grounded_in_evidence(
    titulo: str,
    trecho_origem: str,
    tipo: Kind,
    page_source: str = "",
) -> bool:
    if _evidence_in_source(titulo, trecho_origem, max_gap=4, allow_same_line=False):
        return True
    match = _STRUCTURED_TITLE_RE.match(titulo.strip())
    if not match:
        return False
    prefix = match.group(1).casefold()
    if prefix not in _STRUCTURED_PREFIX_BY_KIND[tipo]:
        return False
    tail = match.group(3).strip()
    if not _tokens(tail):
        return False
    if _evidence_in_source(tail, trecho_origem, max_gap=4, allow_same_line=False):
        return True
    return bool(page_source) and _evidence_in_source(tail, page_source, max_gap=4, allow_same_line=False)


def _clean_verbose_title(titulo: str, tipo: Kind) -> str:
    """Se o modelo copiou uma frase narrativa inteira como título, extrai 'Prova/Trabalho - <Matéria>'."""
    text = titulo.strip()
    if len(text) < 42 and not _VERBOSE_TITLE_VERB_RE.search(text):
        return text
    if not _VERBOSE_TITLE_VERB_RE.search(text):
        return text
    match = _SUBJECT_AFTER_ASSESSMENT_RE.search(text)
    if not match:
        return text
    subject = _TRAILING_CLAUSE_RE.sub("", match.group(1)).strip(" -–—:,.")
    if not subject or len(subject) < 2:
        return text
    label = "Prova" if tipo == "prova" else "Trabalho"
    return f"{label} - {subject}"


def _sort_and_index_candidates(candidates: list[CandidateData]) -> list[CandidateData]:
    """Ordena cronologicamente e padroniza a numeração 'Prova X - <Tema>' sem sobrescrever rótulos fixos do texto."""
    indexed = list(enumerate(candidates))
    indexed.sort(key=lambda pair: (
        pair[1].data_sugerida is None,
        pair[1].data_sugerida or date.max,
        pair[1].hora_sugerida is None,
        pair[1].hora_sugerida or time.max,
        pair[0],
    ))
    ordered = [item for _, item in indexed]
    counters = {"prova": 0, "trabalho": 0}
    for item in ordered:
        match = _STRUCTURED_TITLE_RE.match(item.titulo.strip())
        if not match:
            continue
        if _EXPLICIT_FIXED_LABEL_RE.search(item.trecho_origem):
            continue
        prefix = "Prova" if item.tipo == "prova" else "Trabalho"
        tail = match.group(3).strip()
        counters[item.tipo] += 1
        item.titulo = f"{prefix} {counters[item.tipo]} - {tail}"
    return ordered


def validate_candidates(raw: str, pages: list[TextPage], *, default_year: int | None = None) -> ExtractionResult:
    try:
        output = ExtractionData.model_validate_json(raw)
    except (ValidationError, ValueError):
        raise ProcessingError("falha_ia", reason="schema_invalid") from None
    sources = {page.pagina: page.texto for page in pages}
    reference_year = default_year or extract_reference_year(pages)
    result = ExtractionResult([])
    seen = set()
    first_failure_reason: str | None = None
    for item in output.candidatos:
        evidence = normalize(item.trecho_origem)
        if item.pagina_origem not in sources:
            first_failure_reason = first_failure_reason or "page_mismatch"
            continue
        if not _evidence_in_source(item.trecho_origem, sources[item.pagina_origem]):
            first_failure_reason = first_failure_reason or "evidence_mismatch"
            continue
        if not _title_grounded_in_evidence(item.titulo, item.trecho_origem, item.tipo, sources[item.pagina_origem]):
            first_failure_reason = first_failure_reason or "title_mismatch"
            continue
        item.titulo = _clean_verbose_title(item.titulo, item.tipo)
        # Defesa conservadora: rótulos de aula/bibliografia/regras administrativas não viram provas.
        title = normalize(item.titulo)
        if re.match(r"^(aula|bibliografia|refer[eê]ncias?|leitura|feriado|crit[eé]rios?|sistema|m[eé]todo)\b", title):
            continue
        if item.data_sugerida is None and _ADMIN_POLICY_RE.search(item.trecho_origem):
            continue
        marker = (
            r"\b(provas?|exames?|p[1-9]|pf|ps|substitutiva|avalia(?:ç|c)[ãa]o|avalia(?:ç|c)[õo]es)\b"
            if item.tipo == "prova"
            else r"\b(trabalhos?|t[1-9]|entregas?\s+avaliativas?|projetos?\s+(?:final|avaliativos?)|semin[áa]rios?\s+avaliativos?|relat[óo]rios?\s+avaliativos?)\b"
        )
        if not (re.search(marker, title) or re.search(marker, evidence)):
            continue
        ambiguous = set(item.campos_ambiguos)
        # Aceitar ano completo, abreviado (DD/MM/AA) ou ano de referência explícito no plano/oferta.
        # Sem referência de ano no documento/oferta, não completar usando o relógio.
        if item.data_sugerida is not None and dates_in_evidence(evidence, default_year=reference_year) != {item.data_sugerida}:
            item.data_sugerida = None
            result.unsupported_dates += 1
            ambiguous.add("data")
        if item.data_sugerida is None:
            ambiguous.add("data")
        hours, unambiguous_start = resolve_evidence_hours(evidence)
        if len(hours) > 1 and unambiguous_start is None:
            ambiguous.add("hora")
        if item.hora_sugerida is not None:
            if item.data_sugerida is None or "hora" in ambiguous or item.hora_sugerida != unambiguous_start:
                item.hora_sugerida = None
                ambiguous.add("hora")
        item.campos_ambiguos = sorted(ambiguous)
        identity = (normalize(item.titulo), item.data_sugerida, item.hora_sugerida, item.pagina_origem)
        if identity not in seen:
            seen.add(identity)
            result.candidates.append(item)
    if output.candidatos and not result.candidates and first_failure_reason is not None:
        raise ProcessingError("falha_ia", reason=first_failure_reason)
    result.candidates = _sort_and_index_candidates(result.candidates)
    return result
