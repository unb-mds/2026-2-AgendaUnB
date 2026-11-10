---
title: "ADR-006 · Aplicar autorização na API, nas RPCs e nas políticas RLS"
description: "Decisão, consequências e critérios de verificação: aplicar autorização na api, nas rpcs e nas políticas rls."
---

# ADR-006 · Aplicar autorização na API, nas RPCs e nas políticas RLS

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-04; RF04, RF09, RF11; RNF02, RNF04 |
| Substitui | Nenhuma ADR |

Registro retrospectivo; a motivação histórica e as alternativas avaliadas na época não estão documentadas.

## Contexto

O frontend acessa tanto a API quanto o Supabase. Conexões administrativas da API podem ignorar as políticas de segurança por linha (RLS).

## Decisão

Verificar papel, propriedade e visibilidade no ponto que executa cada operação. A API filtra os dados privados pela conta autenticada; RPCs administrativas verificam o papel no banco; RLS limita o acesso via SDK. Guards de páginas são apenas controle de navegação.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Centralizar tudo na API exigiria migrar os fluxos da ADR-001. Confiar apenas no frontend ou apenas em RLS deixaria caminhos sem proteção.

## Consequências

A equipe mantém regras coerentes em mais de uma camada. Professor/admin moderam eventos; apenas admin gerencia papéis e categorias. Na R2, o papel administrativo não dá acesso ao conteúdo acadêmico privado de outras contas.

## Orientações para contribuição e verificação

Verificar acessos cruzados entre contas e papéis, incluindo chamadas diretas. SQLite não comprova RLS, triggers ou RPCs; esses cenários exigem PostgreSQL/Supabase de teste.

## Fontes e relações

[ADR-001](adr-001-integracao-fastapi-supabase.md) · [Matriz de regras](../visao-geral.md#11-matriz-de-regras-e-evidencias) · [Permissões da R2](../../atualizacoes.md#permissoes-e-erros) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
