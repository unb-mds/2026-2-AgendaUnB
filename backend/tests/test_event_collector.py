from datetime import date

import httpx
import pytest

from src.modules.events.collector import (
    AgendaUnBClient,
    CollectionError,
    ListingEvent,
    _parse_dates,
    normalize_detail,
    parse_listing_page,
    _retry_delay,
)


def _listing(title="Encontro acadêmico", event_id="42", category="Eventos", offset=9):
    next_page = f'<a href="/component/agenda/agendas?start={offset}">2</a>' if offset is not None else ""
    return f"""<!doctype html><div class="agendascategoria"><div class="lista-eventos">
      <div class="item"><span class="cattitle-agenda">{category}</span>
      <div class="conteudo"><h4 class="itemtitle-agenda"><a href="/component/agenda/agenda/{event_id}">{title}</a></h4></div></div>
    </div></div><ul class="pagination">{next_page}</ul>"""


def _detail(*, local="Auditório Darcy Ribeiro", time="14:00 - 16:00", dates="18/11/2026 - 18/11/2026",
            link="https://eventos.unb.br/inscricao"):
    external = f'<a href="{link}">Inscrição</a>' if link else ""
    return f"""<!doctype html><div class="item_fields"><div class="titulo"><h3>Encontro acadêmico</h3></div>
      <div class="detalhes"><span class="local">{local}</span><span class="hora">{time}</span>
      <span class="data">{dates}</span></div><div class="descricao"><p>Descrição detalhada.</p>{external}</div></div>"""


def _robots(disallow="/components/"):
    return f"User-agent: *\nDisallow: {disallow}\n"


def test_listing_reads_only_official_event_links_and_pagination():
    page = _listing() + '<a href="https://evil.test/component/agenda/agendas?start=90">9</a>'

    events, offsets = parse_listing_page(page)

    assert events == [ListingEvent(
        source_id="42",
        source_url="https://noticias.unb.br/component/agenda/agenda/42",
        title="Encontro acadêmico",
        category="Eventos",
    )]
    assert offsets == {9}


def test_client_reads_pages_sequentially_and_deduplicates_event_ids():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=_robots(), headers={"content-type": "text/plain"})
        if request.url.params.get("start") == "9":
            return httpx.Response(200, text=_listing("Oficina", "43", offset=None),
                                  headers={"content-type": "text/html; charset=utf-8"})
        return httpx.Response(200, text=_listing(offset=9),
                              headers={"content-type": "text/html; charset=utf-8"})

    client = AgendaUnBClient(transport=httpx.MockTransport(handler), sleep_fn=lambda _: None, clock=lambda: 1)

    events = client.list_events()

    assert [event.source_id for event in events] == ["42", "43"]
    assert calls[0] == "https://noticias.unb.br/robots.txt"
    assert len(calls) == 3
    assert "start=9" in calls[2]


def test_details_normalize_time_location_campus_and_external_link():
    listing = ListingEvent("42", "https://noticias.unb.br/component/agenda/agenda/42", "Título", "Eventos")

    item = normalize_detail(_detail(), listing)

    assert item["inicio"] == "2026-11-18T14:00:00-03:00"
    assert item["fim"] == "2026-11-18T16:00:00-03:00"
    assert item["local"] == "Auditório Darcy Ribeiro"
    assert item["campus"] == "Darcy Ribeiro (Plano Piloto)"
    assert item["link_externo"] == "https://eventos.unb.br/inscricao"
    assert item["tipo"] == "evento"
    assert item["hash"]


def test_zero_midnight_is_not_invented_as_event_start_or_all_day():
    listing = ListingEvent("42", "https://noticias.unb.br/component/agenda/agenda/42", "Título", "Eventos")

    item = normalize_detail(_detail(time="00:00 - 00:00:00", link=None), listing)

    assert "inicio" not in item
    assert "fim" not in item
    assert item["ambiguo"] is True
    assert "dia_inteiro" not in item


@pytest.mark.parametrize("category, expected", [
    ("Eventos", "evento"), ("Cursos", "evento"), ("Defesas", "evento"),
    ("Informes", "informe"), ("Editais", "informe"), ("Pesquisas", "informe"),
    ("Categoria nova", "informe"),
])
def test_only_known_event_categories_are_published_automatically(category, expected):
    listing = ListingEvent("44", "https://noticias.unb.br/component/agenda/agenda/44", "Aviso", category)

    item = normalize_detail(_detail(), listing)

    assert item["tipo"] == expected


def test_listing_rejects_invalid_event_identity_and_detail_contract():
    with pytest.raises(CollectionError, match="listagem_invalida"):
        parse_listing_page("<html><div class='foo'>sem listagem</div></html>")

    client = AgendaUnBClient(transport=httpx.MockTransport(lambda request: httpx.Response(200, text="ok")))
    with pytest.raises(CollectionError, match="endpoint_proibido"):
        client._get("/administrator/index.php")


def test_client_does_not_follow_redirects():
    client = AgendaUnBClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"location": "https://evil.test/"})
    ))

    with pytest.raises(CollectionError, match="http_302"):
        client._get("/component/agenda/agendas")


def test_client_checks_robots_before_fetching_events():
    calls = []

    def handler(request):
        calls.append(request.url.path)
        return httpx.Response(200, text=_robots("/component/agenda/agenda/"),
                              headers={"content-type": "text/plain"})

    client = AgendaUnBClient(transport=httpx.MockTransport(handler))

    with pytest.raises(CollectionError, match="bloqueado_por_robots"):
        client.list_events()
    assert calls == ["/robots.txt"]


def test_retry_after_is_bounded():
    assert _retry_delay("2") == 2
    with pytest.raises(CollectionError, match="limite_da_origem"):
        _retry_delay("61")
    with pytest.raises(CollectionError, match="retry_after_invalido"):
        _retry_delay("depois")


def test_source_dates_need_a_year_and_valid_calendar_day():
    assert _parse_dates("18/11/2026 - 20/11/2026") == (date(2026, 11, 18), date(2026, 11, 20))
    assert _parse_dates("18/11 - 20/11") == (None, None)
    assert _parse_dates("31/02/2026") == (None, None)
