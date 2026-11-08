---
title: "ADR-011 · Distinguir datas civis de instantes e usar fim exclusivo"
description: "Decisão, consequências e critérios de verificação: distinguir datas civis de instantes e usar fim exclusivo."
---

# ADR-011 · Distinguir datas civis de instantes e usar fim exclusivo

| Campo | Valor |
| --- | --- |
| Estado | Aceita para a Release 2 |
| Data do registro | 2026-11-08 |
| Rastreabilidade | RF06, RF08, RF17, RF21 |
| Substitui | Nenhuma ADR |

Registro de decisão já descrita nos contratos da R2; não comprova implementação ou homologação.

## Contexto

Calendário, extração, lembretes e exportação precisam interpretar datas da mesma forma. Meia-noite em um registro antigo não prova que o evento ocupa o dia inteiro.

## Decisão

Usar America/Sao_Paulo como referência do calendário na R2. Representar instantes com deslocamento explícito e persistência timestamptz; representar dias inteiros por datas civis. Usar fim exclusivo e consultar intervalos por interseção. Datas ambíguas exigem revisão; dia conhecido sem hora só vira dia inteiro após confirmação explícita.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Tratar tudo como timestamp confundiria dias civis e fusos. Deduzir dia inteiro de 00:00 alteraria o significado de registros legados. Fim inclusivo exigiria convenções diferentes nos consumidores.

## Consequências

Frontend, API, banco, jobs e exportadores precisam adotar a mesma semântica. Legados apenas com início preservam o instante e o fim ausente. O calendário atual descrito na visão arquitetural usa o fuso do navegador; esta ADR registra o alvo da R2, não uma migração concluída.

## Orientações para contribuição e verificação

Verificar intervalo de vários dias, interseção da janela, navegador em outro fuso, fim anterior ao início e ambiguidade. Exemplo: 18 a 20/11 inclusive usa start_date 2026-11-18 e end_date 2026-11-21.

## Fontes e relações

[Datas e eventos](../../atualizacoes.md#datas-e-eventos) · [Calendário atual](../visao-geral.md#4-frontend-e-navegacao) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
