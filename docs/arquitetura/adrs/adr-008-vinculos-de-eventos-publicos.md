---
title: "ADR-008 · Salvar vínculos aos eventos públicos na agenda pessoal"
description: "Decisão, consequências e critérios de verificação: salvar vínculos aos eventos públicos na agenda pessoal."
---

# ADR-008 · Salvar vínculos aos eventos públicos na agenda pessoal

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-06; RF08, RF12, RF13, RF18 |
| Substitui | Nenhuma ADR |

Registro retrospectivo; a motivação histórica e as alternativas avaliadas na época não estão documentadas.

## Contexto

A agenda reúne compromissos privados e eventos públicos cujos dados continuam sendo mantidos na origem.

## Decisão

Representar o público salvo por eventos_salvos, com chave (user_id, event_id), sem copiar o evento. Ler os dados do original aprovado e manter o CRUD privado separado. Salvar e remover o próprio vínculo são operações idempotentes.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Copiar o público para eventos_pessoais permitiria alterações individuais, mas geraria divergências de título, local e data em relação ao original.

## Consequências

Mudanças na origem aparecem na agenda. Remover um vínculo não exclui o público; excluir o público remove vínculos em cascata. Salvar não comprova inscrição nem presença. Lembretes e métricas separadas permanecem evolução da R2.

## Orientações para contribuição e verificação

Verificar duplicatas, isolamento entre contas, alteração do original, retirada da aprovação e exclusão em cascata. backend/tests/test_saved_events_api.py cobre a API com SQLite; RLS exige PostgreSQL.

## Fontes e relações

[Eventos salvos](../../eventos-salvos.md) · [Agenda na R2](../../atualizacoes.md#agenda-redirecionamento-e-lembretes) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
