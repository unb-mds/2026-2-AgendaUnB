---
title: "ADR-011 · Distinguir datas civis de instantes e usar fim exclusivo"
description: "Decisão de modelar instantes com fuso explícito e eventos de dia inteiro com datas civis e fim exclusivo."
---

# ADR-011 · Distinguir datas civis de instantes e usar fim exclusivo

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | RF06, RF08, RF17, RF18 |
| Substitui | Nenhuma ADR |

## Contexto

Calendário, extração de planos, coleta de eventos, lembretes e exportadores precisam interpretar datas e intervalos de forma uniforme. Horários `00:00` em registros antigos ou em textos extraídos não comprovam que o evento ocupa o dia inteiro.

## Decisão

Adotar `America/Sao_Paulo` como fuso de referência da agenda acadêmica e distinguir explicitamente instantes de eventos de dia inteiro:

- **Eventos com horário (`all_day = false`):** representados por instantes ISO 8601 com deslocamento explícito em `starts_at` e `ends_at` opcional (`data_evento`/`data_hora` e `data_fim` em `TIMESTAMPTZ`). Quando informado, o término deve ser posterior ao início.
- **Eventos de dia inteiro (`all_day = true`):** representados por datas civis em `start_date` e `end_date` (`data_inicio_civil` e `data_fim_civil` em `DATE`). O fim é sempre **exclusivo**: um evento de 18 a 20/11 inclusive usa `start_date: 2026-11-18` e `end_date: 2026-11-21` (e um único dia omite ou envia `start_date + 1 dia`).
- **Normalização no banco:** triggers (`eventos_normaliza_datas` e `eventos_pessoais_normaliza_datas`) preenchem `data_evento`/`data_hora` e `data_fim` em eventos de dia inteiro com a meia-noite de `America/Sao_Paulo` das datas civis correspondentes, permitindo ordenação, filtros por interseção de janela e agendamento uniforme de lembretes.
- **Ambiguidade:** datas sem ano ou sem hora definida não são convertidas automaticamente em dia inteiro nem recebem `00:00` implícito; exigem confirmação humana ou revisão antes da publicação ou importação.

## Alternativas para comparação

Tratar tudo como timestamp único confundiria dias civis com fusos horários de navegadores. Deduzir dia inteiro a partir de `00:00` alteraria indevidamente o significado de eventos marcados para a meia-noite. Fim inclusivo exigiria cálculos distintos entre API, banco, calendário e exportação RFC 5545 / Google Calendar.

## Consequências

API, banco, interface, coletor de notícias, lembretes e exportadores (Google Calendar e `.ics`) compartilham a mesma semântica de intervalo por interseção e fim exclusivo. Eventos de dia inteiro na resposta da API expõem `all_day: true`, `start_date` e `end_date`, evitando deslocamento de dia em navegadores fora de `-03:00`.

## Orientações para contribuição e verificação

Verificar intervalos de múltiplos dias, interseção em filtros `startDate`/`endDate`, renderização em fusos diferentes de `America/Sao_Paulo`, rejeição de fim anterior ou igual ao início e preservação da ambiguidade de `00:00` na coleta e na extração de planos.

## Fontes e relações

[Dados de eventos](/arquitetura/dados-de-eventos) · [Contratos da API](/api-specs) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
