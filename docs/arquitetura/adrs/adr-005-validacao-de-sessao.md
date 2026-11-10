---
title: "ADR-005 · Validar a sessão no Supabase Auth e consultar o papel no banco"
description: "Decisão, consequências e critérios de verificação: validar a sessão no supabase auth e consultar o papel no banco."
---

# ADR-005 · Validar a sessão no Supabase Auth e consultar o papel no banco

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-03; RF01, RF03, RF04 |
| Substitui | Nenhuma ADR |

Registro retrospectivo; a motivação histórica e as alternativas avaliadas na época não estão documentadas.

## Contexto

A API precisa identificar a conta e seu papel sem confiar em valores enviados pelo navegador.

## Decisão

Validar o Bearer consultando Supabase Auth e carregar profiles.papel pelo ID autenticado. O middleware atual usa timeout de cinco segundos. Sessão inválida resulta em 401; falha do serviço de autenticação resulta em 503; perfil ausente resulta em 403.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Validar JWT localmente reduziria chamadas externas, mas exigiria gerir chaves e regras de validação. Usar o papel informado pelo cliente não preservaria a autorização.

## Consequências

Rotas protegidas dependem da disponibilidade do Auth e acrescentam uma consulta de perfil. Mudanças de papel são lidas do banco, sem confiar no estado da interface.

## Orientações para contribuição e verificação

A referência é backend/src/middlewares/auth.py. Verificar sessão ausente, inválida, indisponibilidade do Auth e perfil ausente. Testes que substituem a dependência de autenticação não validam essa integração.

## Fontes e relações

[Fluxo da API](../visao-geral.md#5-api-rest-implementada) · [Contratos](../../api-specs.md) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
