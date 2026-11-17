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

VERSION = "syllabus-v3-approved-text"
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


def extract_reference_year(pages: list[TextPage]) -> int | None:
    for page in pages:
        match = re.search(r"\b(20\d{2})\s*[/.]\s*[12]\b", page.texto)
        if match:
            return int(match[1])
    for page in pages:
        match = re.search(r"(?<!\d)(?:\d{1,2})[/-](?:\d{1,2})[/-](20\d{2})(?!\d)", page.texto)
        if match:
            return int(match[1])
    return None


def dates_in_evidence(value: str, *, default_year: int | None = None) -> set[date]:
    found = set()
    triples = [(int(y), int(m), int(d)) for d, m, y in
               re.findall(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?!\d)", value)]
    triples += [(int(y), int(m), int(d)) for d, m, y in
                re.findall(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{4})(?!\d)", value)]
    triples += [(int(y), int(m), int(d)) for y, m, d in
                re.findall(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", value)]
    triples += [(2000 + int(y), int(m), int(d)) for d, m, y in
                re.findall(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{2})(?!\d)", value)]
    triples += [(2000 + int(y), int(m), int(d)) for d, m, y in
                re.findall(r"(?<!\d)(\d{1,2})\.(\d{1,2})\.(\d{2})(?!\d)", value)]
    for index, month in enumerate(MONTHS, 1):
        month_pattern = "mar[cç]o" if month == "março" else month
        triples += [(int(y), index, int(d)) for d, y in re.findall(
            rf"(?<!\d)(\d{{1,2}})\s+de\s+{month_pattern}\s+de\s+(\d{{4}})(?!\d)", value.casefold())]
    for index, short_month in enumerate(SHORT_MONTHS, 1):
        triples += [(int(y), index, int(d)) for d, y in re.findall(
            rf"(?<!\d)(\d{{1,2}})[/\s-]+(?:de\s+)?{short_month}[/\s-]+(?:de\s+)?(\d{{4}})(?!\d)", value.casefold())]
    if default_year is not None:
        triples += [(default_year, int(m), int(d)) for d, m in
                    re.findall(r"(?<!\d)(\d{1,2})/(\d{1,2})(?![/\d])", value)]
        for index, month in enumerate(MONTHS, 1):
            month_pattern = "mar[cç]o" if month == "março" else month
            triples += [(default_year, index, int(d)) for d in re.findall(
                rf"(?<!\d)(\d{{1,2}})\s+de\s+{month_pattern}(?!\s+de\s+\d)(?!\d)", value.casefold())]
    for year, month, day in triples:
        try:
            found.add(date(year, month, day))
        except ValueError:
            pass
    return found


def times_in_evidence(value: str) -> set[time]:
    found = set()
    for match in re.finditer(r"(?<![\d:])(\d{1,2})\s*(?::\s*(\d{2})|h(?:\s*(\d{2}))?)(?![\d:])", value):
        try:
            found.add(time(int(match[1]), int(match[2] or match[3] or 0)))
        except ValueError:
            pass
    return found


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
        if not _evidence_in_source(item.titulo, item.trecho_origem, max_gap=4, allow_same_line=False):
            first_failure_reason = first_failure_reason or "title_mismatch"
            continue
        # Defesa conservadora: rótulos de aula/bibliografia não viram provas.
        title = normalize(item.titulo)
        if re.match(r"^(aula|bibliografia|refer[eê]ncias?|leitura|feriado|crit[eé]rios?|sistema|m[eé]todo)\b", title):
            continue
        marker = r"\b(provas?|exames?|p[1-9]|pf|avalia(?:ç|c)[ãa]o)\b" if item.tipo == "prova" else r"\btrabalhos?\b"
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
        hours = times_in_evidence(evidence)
        if len(hours) > 1:
            ambiguous.add("hora")
        if item.hora_sugerida is not None:
            if item.data_sugerida is None or hours != {item.hora_sugerida} or "hora" in ambiguous:
                item.hora_sugerida = None
                ambiguous.add("hora")
        item.campos_ambiguos = sorted(ambiguous)
        identity = (normalize(item.titulo), item.data_sugerida, item.hora_sugerida, item.pagina_origem)
        if identity not in seen:
            seen.add(identity)
            result.candidates.append(item)
    if output.candidatos and not result.candidates and first_failure_reason is not None:
        raise ProcessingError("falha_ia", reason=first_failure_reason)
    return result
