---
title: "ADR-007 · Usar migrações SQL como referência do esquema completo"
description: "Decisão de versionar o esquema completo, políticas RLS, funções e triggers em migrações SQL."
---

# ADR-007 · Usar migrações SQL como referência do esquema completo

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-05; RNF13 |
| Substitui | Nenhuma ADR |

## Contexto

O banco PostgreSQL contém tabelas, restrições, índices parciais, políticas RLS, funções e triggers que não são representados integralmente pelos modelos SQLAlchemy da API.

## Decisão

Versionar o esquema completo em `supabase/migrations/` e aplicar as migrações em ordem cronológica antes de publicar código da API ou do frontend que dependa delas. O ORM em `backend/src/database/models.py` mapeia apenas as estruturas usadas pela aplicação e não substitui as migrações SQL.

Em ambientes persistentes, a aplicação de migrações segue protocolo seguro:

1. **Backup lógico prévio:** extrair snapshot consistente com `pg_dump` (formato custom) antes de alterar o banco, conferindo o conteúdo com `pg_restore --list`.
2. **Ensaio isolado:** validar a aplicação das migrações pendentes em instância isolada (nunca usando `pg_restore --clean` ou `supabase db reset` sobre o banco compartilhado), executando os testes de RLS, RPCs, triggers e pré-requisitos do worker.
3. **Verificação de pré-condições e transação:** validar remoção de estruturas obsoletas somente após confirmar migração dos dados sob bloqueio contra escritas concorrentes; executar a migração de forma controlada e confirmar a integridade do esquema e das políticas aplicadas.

## Alternativas para comparação

Gerar o esquema apenas pelo ORM omitiria políticas RLS, triggers e funções SQL específicas do PostgreSQL. Alterações manuais sem arquivo de migração impediriam reprodutibilidade entre ambientes.

## Consequências

Frontend, API e banco precisam coordenar a ordem de implantação. Alterações de esquema devem priorizar mudanças aditivas compatíveis com leitores em transição e preservar contratos existentes.

## Orientações para contribuição e verificação

Validar migrações do zero e lint de esquema (`supabase db lint --level error --fail-on error`) em instância descartável via CI (`.github/workflows/supabase-ci.yml`), além dos testes de RLS e RPC em PostgreSQL local. A existência de um modelo ORM não garante que a migração correspondente tenha sido aplicada no banco de destino.

## Fontes e relações

[Persistência e migrações](/arquitetura/visao-geral#7-persistencia-privacidade-e-migracoes) · [Especificação do banco](/arquitetura/banco-de-dados) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
