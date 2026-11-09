"""Texto e sugestões não confiáveis: validar procedência antes de persistir."""
import io
import re
from dataclasses import dataclass
from datetime import date, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from pypdf import PdfReader

from src.modules.syllabus.processing_config import ProcessingConfig, ProcessingError

VERSION = "syllabus-v1"
Kind = Literal["prova", "trabalho", "projeto", "seminario", "lista", "entrega", "outro"]
AmbiguousField = Literal["titulo", "tipo", "data", "hora"]


@dataclass(frozen=True)
class TextPage:
    pagina: int
    texto: str


class CandidateData(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    titulo: str = Field(min_length=1, max_length=300)
    tipo: Kind
    data_sugerida: date | None = None
    hora_sugerida: time | None = None
    campos_ambiguos: list[AmbiguousField] = Field(default_factory=list, max_length=4)
    pagina_origem: int = Field(ge=1, le=10, strict=True)
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


def normalize(value: str) -> str:
    return " ".join(value.split()).casefold()


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


def dates_in_evidence(value: str) -> set[date]:
    found = set()
    triples = [(int(y), int(m), int(d)) for d, m, y in
               re.findall(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?!\d)", value)]
    triples += [(int(y), int(m), int(d)) for y, m, d in
                re.findall(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", value)]
    for index, month in enumerate(MONTHS, 1):
        triples += [(int(y), index, int(d)) for d, y in re.findall(
            rf"(?<!\d)(\d{{1,2}})\s+de\s+{month}\s+de\s+(\d{{4}})(?!\d)", value.casefold())]
    for year, month, day in triples:
        try:
            found.add(date(year, month, day))
        except ValueError:
            pass
    return found


def validate_candidates(raw: str, pages: list[TextPage]) -> ExtractionResult:
    try:
        output = ExtractionData.model_validate_json(raw)
    except (ValidationError, ValueError):
        raise ProcessingError("falha_ia") from None
    sources = {page.pagina: normalize(page.texto) for page in pages}
    result = ExtractionResult([])
    seen = set()
    for item in output.candidatos:
        evidence = normalize(item.trecho_origem)
        if evidence not in sources.get(item.pagina_origem, "") or normalize(item.titulo) not in evidence:
            raise ProcessingError("falha_ia")
        ambiguous = set(item.campos_ambiguos)
        # Uma data ISO plausível não basta: exigir data completa e inequívoca
        # no trecho citado. Nunca completar ano, dia ou mês usando o relógio.
        if item.data_sugerida is not None and dates_in_evidence(evidence) != {item.data_sugerida}:
            item.data_sugerida = None
            result.unsupported_dates += 1
            ambiguous.add("data")
        if item.data_sugerida is None:
            ambiguous.add("data")
        if item.hora_sugerida is not None:
            hour, minute = item.hora_sugerida.hour, item.hora_sugerida.minute
            pattern = rf"(?<!\d)0?{hour}(?::|h){minute:02d}(?!\d)"
            full_hour = minute == 0 and re.search(rf"(?<!\d)0?{hour}h(?!\d)", evidence)
            if item.data_sugerida is None or not (re.search(pattern, evidence) or full_hour):
                item.hora_sugerida = None
                ambiguous.add("hora")
        if item.tipo == "outro":
            ambiguous.add("tipo")
        item.campos_ambiguos = sorted(ambiguous)
        identity = (normalize(item.titulo), item.data_sugerida, item.hora_sugerida, item.pagina_origem)
        if identity not in seen:
            seen.add(identity)
            result.candidates.append(item)
    return result
