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


@pytest.mark.parametrize("time_label, dates, expected_start, expected_end", [
    ("Dia inteiro", "18/11/2026 - 18/11/2026", "2026-11-18", "2026-11-19"),
    ("Dia todo", "18/11/2026 - 20/11/2026", "2026-11-18", "2026-11-21"),
    ("Todo o dia", "01/12/2026 - 01/12/2026", "2026-12-01", "2026-12-02"),
    ("Horário integral", "10/11/2026 - 10/11/2026", "2026-11-10", "2026-11-11"),
])
def test_explicit_all_day_formats_are_detected_with_exclusive_end(time_label, dates, expected_start, expected_end):
    listing = ListingEvent("50", "https://noticias.unb.br/component/agenda/agenda/50", "Semana Acadêmica", "Eventos")
    item = normalize_detail(_detail(time=time_label, dates=dates), listing)

    assert item.get("dia_inteiro") is True
    assert item["data_inicio"] == expected_start
    assert item["data_fim"] == expected_end
    assert item["ambiguo"] is False
    assert "inicio" not in item
    assert "fim" not in item


def test_zero_time_without_explicit_signal_remains_ambiguous_for_review():
    listing = ListingEvent("51", "https://noticias.unb.br/component/agenda/agenda/51", "Reunião Geral", "Eventos")
    item = normalize_detail(_detail(time="00:00 - 00:00:00", dates="18/11/2026 - 18/11/2026"), listing)

    assert item.get("dia_inteiro") is None or item.get("dia_inteiro") is False
    assert "inicio" not in item
    assert "fim" not in item
    assert item["ambiguo"] is True


def test_duplicate_similarity_detection_positive_and_negative_cases():
    from src.modules.events.collector import check_potential_duplicate

    d1 = date(2026, 11, 18)
    d1_next = date(2026, 11, 19)
    d1_far = date(2026, 12, 18)

    # 1. Mesma data, pequena variação de pontuação e acentuação -> Potencial duplicata
    is_dup, reason = check_potential_duplicate(
        "Semana Universitária 2026", d1,
        "SEMANA universitária — 2026!", d1,
    )
    assert is_dup is True
    assert "mesma_data" in reason

    # 2. Data próxima (1 dia de diferença), títulos muito semelhantes -> Potencial duplicata
    is_dup, reason = check_potential_duplicate(
        "Palestra: Inteligência Artificial na Educação", d1,
        "Palestra Inteligência Artificial na Educação", d1_next,
    )
    assert is_dup is True
    assert "data_proxima_1_dia" in reason

    # 3. Pequena variação com preposição/artigo -> Potencial duplicata
    is_dup, reason = check_potential_duplicate(
        "Workshop de Python para Iniciantes", d1,
        "Workshop de Python Iniciantes", d1,
    )
    assert is_dup is True

    # 4. FALSO POSITIVO EVITADO: datas distantes (meses diferentes) mesmo com títulos idênticos
    is_dup, _ = check_potential_duplicate(
        "Reunião Ordinária da Congregação", d1,
        "Reunião Ordinária da Congregação", d1_far,
    )
    assert is_dup is False

    # 5. FALSO POSITIVO EVITADO: números distintivos diferentes (ex: matérias ou turmas)
    is_dup, _ = check_potential_duplicate(
        "Cálculo 1", d1,
        "Cálculo 2", d1,
    )
    assert is_dup is False

    is_dup, _ = check_potential_duplicate(
        "Física Experimental 1", d1,
        "Física Experimental 2", d1_next,
    )
    assert is_dup is False

    # 6. FALSO POSITIVO EVITADO: títulos completamente diferentes no mesmo dia
    is_dup, _ = check_potential_duplicate(
        "Apresentação de TCC", d1,
        "Torneio de Xadrez Universitário", d1,
    )
    assert is_dup is False


@pytest.mark.parametrize("location, expected_campus", [
    ("Auditório da FCTE, Campus Gama", "Faculdade do Gama (FCTE)"),
    ("Faculdade de Ceilândia - Sala 12", "Faculdade de Ceilândia (FCTS)"),
    ("Campus Planaltina (FUP) - Bloco Acadêmico", "Faculdade de Planaltina (FUP)"),
    ("Fazenda Água Limpa (FAL) - Sede", "Fazenda Água Limpa (FAL)"),
    ("ICC Sul, Auditório Pompeu de Sousa", "Darcy Ribeiro (Plano Piloto)"),
    ("Reitoria da UnB, Sala de Reuniões", "Darcy Ribeiro (Plano Piloto)"),
    ("Beijódromo, Campus Darcy Ribeiro", "Darcy Ribeiro (Plano Piloto)"),
    ("Praça dos Três Poderes", None),
])
def test_multicampus_normalization_coverage(location, expected_campus):
    from src.modules.events.collector import _normalize_campus

    assert _normalize_campus(location) == expected_campus
