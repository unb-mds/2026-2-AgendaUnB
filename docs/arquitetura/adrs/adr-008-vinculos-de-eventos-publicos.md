---
title: "ADR-008 · Salvar vínculos aos eventos públicos na agenda pessoal"
description: "Decisão de modelar eventos públicos salvos por vínculo referencial em vez de cópia."
---

# ADR-008 · Salvar vínculos aos eventos públicos na agenda pessoal

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-06; RF08, RF12, RF13 |
| Substitui | Nenhuma ADR |

## Contexto

A agenda pessoal reúne compromissos privados do usuário e eventos públicos do catálogo cujos dados continuam sendo mantidos pela moderação e pelos organizadores na origem.

## Decisão

Representar o evento público salvo na tabela `eventos_salvos` com chave primária composta `(user_id, event_id)`, sem duplicar os dados do evento em `eventos_pessoais`. A consulta lê os dados atualizados do evento original aprovado, mantendo o CRUD privado separado. Salvar (`PUT /api/v1/me/saved-events/{event_id}`) e remover o vínculo (`DELETE /api/v1/me/saved-events/{event_id}`) são operações idempotentes.

## Alternativas para comparação

Copiar o evento público para `eventos_pessoais` permitiria edições individuais, mas geraria divergências de título, local e data quando o evento oficial fosse atualizado ou retirado do catálogo.

## Consequências

Alterações no evento público original refletem-se automaticamente em **Meus Eventos** e disparam atualização nos lembretes pendentes. Remover um vínculo cancela os lembretes associados sem excluir o evento público; excluir o evento público remove seus vínculos em cascata. Salvar um evento não representa inscrição oficial nem confirmação de presença.

## Orientações para contribuição e verificação

Verificar idempotência, isolamento entre contas, atualização do evento original, retirada da aprovação, exclusão em cascata e cancelamento de lembretes (`backend/tests/test_saved_events_api.py` e `backend/tests/test_reminders_database.py`).

## Fontes e relações

[Eventos salvos](/eventos-salvos) · [Conferir evento](/arquitetura/conferir-evento) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
