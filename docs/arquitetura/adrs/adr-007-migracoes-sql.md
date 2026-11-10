---
title: "ADR-007 · Usar migrações SQL como referência do esquema completo"
description: "Decisão, consequências e critérios de verificação: usar migrações sql como referência do esquema completo."
---

# ADR-007 · Usar migrações SQL como referência do esquema completo

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-05; RNF13 |
| Substitui | Nenhuma ADR |

Registro retrospectivo; a motivação histórica e as alternativas avaliadas na época não estão documentadas.

## Contexto

O banco contém tabelas, políticas RLS, funções e triggers que não são representados integralmente pelos modelos SQLAlchemy.

## Decisão

Versionar o esquema completo em supabase/migrations/ e aplicar migrações em ordem antes do código que depende delas. O ORM mapeia as estruturas usadas pela API e não substitui as migrações.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Gerar o esquema apenas pelo ORM omitiria estruturas específicas do PostgreSQL. Alterações manuais sem migração dificultariam reproduzir ambientes.

## Consequências

Frontend, API e banco precisam coordenar sua implantação. Alterações exigem verificar políticas, funções e leitores antigos. Na R2, priorizar mudanças aditivas e preservar os nomes legados definidos no contrato.

## Orientações para contribuição e verificação

Validar migrações em banco local descartável e os testes de RLS/RPC. A presença de um modelo ORM não comprova que uma migração foi aplicada.

## Fontes e relações

[Persistência e migrações](../visao-geral.md#7-persistencia-privacidade-e-migracoes) · [Compatibilidade](../../atualizacoes.md#compatibilidade-e-migracao) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
