"""Coleta de eventos públicos da Agenda UnB Notícias.

Execução única: ``python -m src.modules.events.collector``.
Modo recorrente: ``python -m src.modules.events.collector --interval-hours 6``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import date, datetime, time as day_time, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from time import monotonic, sleep
from typing import Callable
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from uuid import UUID
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import text
from sqlalchemy.engine import Connection

SOURCE = "agenda_unb_noticias"
BASE_URL = "https://noticias.unb.br"
LIST_PATH = "/component/agenda/agendas"
DETAIL_PATH = "/component/agenda/agenda/"
LOCK_KEY = 708073
PAGE_SIZE = 9
MAX_PAGES = 100
MAX_EVENTS = 900
MAX_HTML_BYTES = 2_000_000
MIN_REQUEST_INTERVAL_SECONDS = 1.0
HTTP_TIMEOUT_SECONDS = 20.0
MAX_RETRY_AFTER_SECONDS = 60.0
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
ZERO_TIME = {"00:00", "00:00:00"}
USER_AGENT = "AgendaUnB-EventCollector/1.0 (UnB academic calendar)"
BRASILIA = ZoneInfo("America/Sao_Paulo")


class CollectionError(Exception):
    """Falha sanitizada de origem/coleta; nunca inclui o HTML recebido."""

    def __init__(self, code: str):
        self.code = code[:60]
        super().__init__(self.code)


class _Node:
    def __init__(self, tag: str, attrs: list[tuple[str, str | None]], parent: _Node | None = None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children: list[_Node | str] = []

    def has_class(self, name: str) -> bool:
        return name in (self.attrs.get("class") or "").split()

    def find_all(self, tag: str | None = None, class_name: str | None = None) -> list[_Node]:
        found: list[_Node] = []
        for child in self.children:
            if not isinstance(child, _Node):
                continue
            if (tag is None or child.tag == tag) and (class_name is None or child.has_class(class_name)):
                found.append(child)
            found.extend(child.find_all(tag, class_name))
        return found

    def first(self, tag: str | None = None, class_name: str | None = None) -> _Node | None:
        return next(iter(self.find_all(tag, class_name)), None)

    def text(self) -> str:
        pieces: list[str] = []
        for child in self.children:
            pieces.append(child.text() if isinstance(child, _Node) else child)
        return re.sub(r"\s+", " ", " ".join(pieces)).strip()


class _TreeParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("document", [])
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1].children.append(_Node(tag, attrs, self.stack[-1]))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.stack[-1].children.append(data)


def _parse_html(source: str) -> _Node:
    parser = _TreeParser()
    parser.feed(source)
    parser.close()
    return parser.root


@dataclass(frozen=True)
class ListingEvent:
    source_id: str
    source_url: str
    title: str
    category: str


def parse_listing_page(source: str) -> tuple[list[ListingEvent], set[int]]:
    """Extrai itens e offsets da paginação da marcação Joomla observada."""
    root = _parse_html(source)
    listing = root.first("div", "lista-eventos")
    if listing is None:
        raise CollectionError("listagem_invalida")

    events: list[ListingEvent] = []
    for item in listing.find_all("div", "item"):
        title_link = None
        for heading in item.find_all("h4", "itemtitle-agenda"):
            title_link = heading.first("a")
            if title_link is not None:
                break
        if title_link is None:
            continue
        path = urlsplit(title_link.attrs.get("href") or "").path
        match = re.fullmatch(r"/component/agenda/agenda/(\d+)/?", path)
        title = title_link.text()
        if not match or len(title) < 3:
            raise CollectionError("item_listagem_invalido")
        category = (item.first("span", "cattitle-agenda") or _Node("span", [])).text()
        source_id = match.group(1)
        events.append(ListingEvent(
            source_id=source_id,
            source_url=f"{BASE_URL}{DETAIL_PATH}{source_id}",
            title=title[:200],
            category=category,
        ))

    starts: set[int] = set()
    for link in root.find_all("a"):
        href = link.attrs.get("href") or ""
        parsed = urlsplit(urljoin(BASE_URL, href))
        if parsed.hostname != "noticias.unb.br" or parsed.path != LIST_PATH:
            continue
        query = parse_qs(parsed.query)
        raw = query.get("start", [None])[0]
        if raw and raw.isdigit():
            starts.add(int(raw))
    return events, starts


def _parse_dates(value: str) -> tuple[date | None, date | None]:
    matches = re.findall(r"(?<!\d)(\d{2})/(\d{2})/(\d{4})(?!\d)", value)
    parsed: list[date] = []
    try:
        parsed = [date(int(year), int(month), int(day)) for day, month, year in matches[:2]]
    except ValueError:
        return None, None
    if not parsed:
        return None, None
    return parsed[0], parsed[1] if len(parsed) > 1 else parsed[0]


def _parse_times(value: str) -> tuple[day_time | None, day_time | None, bool]:
    matches = re.findall(r"(?<!\d)(\d{1,2}:\d{2}(?::\d{2})?)(?!\d)", value)
    if not matches:
        return None, None, True
    try:
        parsed = [day_time.fromisoformat(item) for item in matches[:2]]
    except ValueError:
        return None, None, True
    start = parsed[0]
    end = parsed[1] if len(parsed) > 1 else None
    if start.isoformat(timespec="minutes") in ZERO_TIME:
        # A meia-noite é um valor de preenchimento comum na fonte. Sem uma
        # hora inequívoca, a data vai para revisão; não vira dia inteiro.
        return None, None, True
    if end and end.isoformat(timespec="minutes") in ZERO_TIME:
        end = None
    return start, end, False


def _normalize_campus(location: str) -> str | None:
    value = _fold(location)
    if "fct e" in value or "fcte" in value or "faculdade do gama" in value or re.search(r"\bgama\b", value):
        return "Faculdade do Gama (FCTE)"
    if "fcts" in value or "faculdade de ceilandia" in value or re.search(r"\bceilandia\b", value):
        return "Faculdade de Ceilândia (FCTS)"
    if "fup" in value or "faculdade de planaltina" in value or re.search(r"\bplanaltina\b", value):
        return "Faculdade de Planaltina (FUP)"
    if "fal" in value or "fazenda agua limpa" in value:
        return "Fazenda Água Limpa (FAL)"
    if "darcy ribeiro" in value or "plano piloto" in value:
        return "Darcy Ribeiro (Plano Piloto)"
    return None


def _fold(value: str) -> str:
    import unicodedata

    return "".join(char for char in unicodedata.normalize("NFKD", value.lower()) if not unicodedata.combining(char))


def _external_link(description: _Node) -> str | None:
    for link in description.find_all("a"):
        href = urljoin(BASE_URL, link.attrs.get("href") or "")
        parsed = urlsplit(href)
        if parsed.scheme in {"http", "https"} and parsed.hostname and parsed.hostname.lower() != "noticias.unb.br":
            return href[:2048]
    return None


def normalize_detail(source: str, listing_event: ListingEvent) -> dict:
    root = _parse_html(source)
    fields = root.first("div", "item_fields")
    if fields is None:
        raise CollectionError("detalhe_invalido")
    title_node = fields.first("h3")
    details = fields.first("div", "detalhes")
    description = fields.first("div", "descricao")
    if title_node is None or details is None or description is None:
        raise CollectionError("detalhe_invalido")

    title = title_node.text() or listing_event.title
    location = (details.first("span", "local").text() if details.first("span", "local") else "")[:250]
    date_text = details.first("span", "data").text() if details.first("span", "data") else ""
    time_text = details.first("span", "hora").text() if details.first("span", "hora") else ""
    starts_on, ends_on = _parse_dates(date_text)
    starts_at, ends_at, time_ambiguous = _parse_times(time_text)

    payload: dict = {
        "fonte": SOURCE,
        "fonte_id": listing_event.source_id,
        "fonte_url": listing_event.source_url,
        "tipo": "evento" if _fold(listing_event.category) in {"eventos", "cursos", "defesas"} else "informe",
        "titulo": title[:200],
        "descricao": description.text()[:10000],
        "local": location or None,
        "link_externo": _external_link(description),
        "campus": _normalize_campus(location),
        "ambiguo": time_ambiguous or starts_on is None,
    }
    if starts_on is not None and starts_at is not None:
        start_local = datetime.combine(starts_on, starts_at, tzinfo=BRASILIA)
        payload["inicio"] = start_local.isoformat()
        if ends_on is not None and ends_at is not None:
            end_local = datetime.combine(ends_on, ends_at, tzinfo=BRASILIA)
            if end_local > start_local:
                payload["fim"] = end_local.isoformat()
            else:
                payload["ambiguo"] = True

    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    payload["hash"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


class AgendaUnBClient:
    """Cliente somente leitura, restrito à listagem e aos detalhes institucionais."""

    def __init__(self, *, transport=None, sleep_fn: Callable[[float], None] = sleep,
                 clock: Callable[[], float] = monotonic):
        self.transport = transport
        self.sleep = sleep_fn
        self.clock = clock
        self.last_request: float | None = None
        self._robots_checked = False
        self._robots: RobotFileParser | None = None

    def _get(self, path: str, params: dict | None = None) -> str:
        is_robots = path == "/robots.txt"
        if not is_robots and path != LIST_PATH and not re.fullmatch(r"/component/agenda/agenda/\d+", path):
            raise CollectionError("endpoint_proibido")
        for attempt in range(2):
            if self.last_request is not None:
                self.sleep(max(0.0, MIN_REQUEST_INTERVAL_SECONDS - (self.clock() - self.last_request)))
            self.last_request = self.clock()
            try:
                with httpx.Client(
                    timeout=HTTP_TIMEOUT_SECONDS,
                    follow_redirects=False,
                    trust_env=False,
                    transport=self.transport,
                    headers={"User-Agent": USER_AGENT, "Accept": "text/plain" if is_robots else "text/html"},
                ) as client:
                    response = client.get(f"{BASE_URL}{path}", params=params)
            except (httpx.TimeoutException, httpx.TransportError):
                if attempt == 0:
                    continue
                raise CollectionError("origem_indisponivel") from None
            if response.status_code in RETRYABLE_STATUS and attempt == 0:
                self.sleep(_retry_delay(response.headers.get("Retry-After")))
                continue
            if response.status_code != 200:
                raise CollectionError(f"http_{response.status_code}")
            if len(response.content) > MAX_HTML_BYTES:
                raise CollectionError("resposta_muito_grande")
            content_type = response.headers.get("content-type", "").lower()
            if (is_robots and "text/plain" not in content_type) or (not is_robots and "text/html" not in content_type):
                raise CollectionError("tipo_resposta_invalido")
            return response.text
        raise CollectionError("origem_indisponivel")

    def _check_robots(self) -> None:
        if self._robots_checked:
            return
        source = self._get("/robots.txt")
        rules = RobotFileParser()
        rules.set_url(f"{BASE_URL}/robots.txt")
        rules.parse(source.splitlines())
        if not rules.can_fetch(USER_AGENT, f"{BASE_URL}{LIST_PATH}") or not rules.can_fetch(
            USER_AGENT, f"{BASE_URL}{DETAIL_PATH}1"
        ):
            raise CollectionError("bloqueado_por_robots")
        self._robots = rules
        self._robots_checked = True

    def list_events(self) -> list[ListingEvent]:
        self._check_robots()
        pending = [0]
        seen_offsets: set[int] = set()
        events_by_id: dict[str, ListingEvent] = {}
        pages_read = 0
        while pending:
            offset = pending.pop(0)
            if offset in seen_offsets:
                continue
            if pages_read >= MAX_PAGES:
                raise CollectionError("limite_de_paginas")
            seen_offsets.add(offset)
            pages_read += 1
            html = self._get(LIST_PATH, {"start": offset} if offset else None)
            events, next_offsets = parse_listing_page(html)
            for event in events:
                previous = events_by_id.get(event.source_id)
                if previous and previous != event:
                    raise CollectionError("identidade_conflitante")
                events_by_id[event.source_id] = event
                if len(events_by_id) > MAX_EVENTS:
                    raise CollectionError("limite_de_eventos")
            pending.extend(sorted(next_offsets - seen_offsets))
        return list(events_by_id.values())

    def event_detail(self, event: ListingEvent) -> str:
        self._check_robots()
        parsed = urlsplit(event.source_url)
        expected_path = f"{DETAIL_PATH}{event.source_id}"
        if parsed.scheme != "https" or parsed.hostname != "noticias.unb.br" or parsed.path != expected_path:
            raise CollectionError("url_de_detalhe_invalida")
        if self._robots is not None and not self._robots.can_fetch(USER_AGENT, event.source_url):
            raise CollectionError("bloqueado_por_robots")
        return self._get(expected_path)


def _retry_delay(value: str | None) -> float:
    if not value:
        return 1.0
    try:
        delay = float(value)
    except ValueError:
        try:
            delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            raise CollectionError("retry_after_invalido") from None
    if not 0 <= delay <= MAX_RETRY_AFTER_SECONDS:
        raise CollectionError("limite_da_origem")
    return delay


def _as_mapping(value) -> dict:
    return value if isinstance(value, dict) else json.loads(value)


def _finish_run(connection: Connection, run_id: UUID, *, status: str, error_code: str | None = None,
                counters: dict[str, int] | None = None) -> None:
    counters = counters or {}
    connection.execute(text("""
        update public.coletas_eventos
           set status=:status, concluida_em=now(), erro_codigo=:error_code,
               itens_lidos=:read, criados=:created, atualizados=:updated,
               inalterados=:unchanged, conciliados=:reconciled, para_revisao=:review
         where id=:id
    """), {
        "status": status,
        "error_code": error_code,
        "read": counters.get("read", 0),
        "created": counters.get("created", 0),
        "updated": counters.get("updated", 0),
        "unchanged": counters.get("unchanged", 0),
        "reconciled": counters.get("reconciled", 0),
        "review": counters.get("review", 0),
        "id": run_id,
    })


def collect_events(connection: Connection, client: AgendaUnBClient | None = None) -> dict:
    """Lê toda a fonte, depois grava em uma única transação, sem apagar registros."""
    if not connection.scalar(text("select pg_try_advisory_lock(:key)"), {"key": LOCK_KEY}):
        connection.rollback()
        return {"status": "ignorada", "erro": "coleta_em_andamento"}
    connection.commit()
    run_id = None
    try:
        run_id = connection.execute(text(
            "insert into public.coletas_eventos(fonte) values (:source) returning id"
        ), {"source": SOURCE}).scalar_one()
        connection.commit()

        source = client or AgendaUnBClient()
        listed = source.list_events()
        normalized = [normalize_detail(source.event_detail(event), event) for event in listed]

        counters = {"read": len(normalized), "created": 0, "updated": 0,
                    "unchanged": 0, "reconciled": 0, "review": 0}
        with connection.begin():
            for payload in normalized:
                result = _as_mapping(connection.execute(text(
                    "select public.registrar_evento_coletado(cast(:payload as jsonb))"
                ), {"payload": json.dumps(payload, ensure_ascii=False)}).scalar_one())
                action = result.get("acao")
                action_key = {"criado": "created", "atualizado": "updated",
                              "inalterado": "unchanged", "conciliado": "reconciled"}.get(action)
                if action_key is None:
                    raise CollectionError("resultado_de_gravacao_invalido")
                counters[action_key] += 1
                counters["review"] += action == "criado" and result.get("status") == "pendente"
            _finish_run(connection, run_id, status="concluida", counters=counters)
        return {"id": str(run_id), "status": "concluida", **counters}
    except CollectionError as error:
        connection.rollback()
        if run_id is not None:
            with connection.begin():
                _finish_run(connection, run_id, status="falha", error_code=error.code)
        return {"id": str(run_id) if run_id else None, "status": "falha", "erro": error.code}
    except Exception:
        connection.rollback()
        if run_id is not None:
            try:
                with connection.begin():
                    _finish_run(connection, run_id, status="falha", error_code="coleta_falhou")
            except Exception:
                connection.rollback()
        return {"id": str(run_id) if run_id else None, "status": "falha", "erro": "coleta_falhou"}
    finally:
        connection.rollback()
        connection.execute(text("select pg_advisory_unlock(:key)"), {"key": LOCK_KEY})
        connection.commit()


def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval-hours", type=float, default=None,
                        help="repete a coleta após este intervalo (mínimo: 1 hora)")
    args = parser.parse_args()
    if args.interval_hours is not None and (not math.isfinite(args.interval_hours) or args.interval_hours < 1):
        parser.error("--interval-hours precisa ser um número finito de pelo menos 1")
    from src.database.connection import engine

    while True:
        with engine.connect() as connection:
            result = collect_events(connection)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        if args.interval_hours is None:
            return 0 if result.get("status") == "concluida" else 1
        sleep(args.interval_hours * 3600)


if __name__ == "__main__":
    raise SystemExit(_main())
