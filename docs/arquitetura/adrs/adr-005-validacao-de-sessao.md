---
title: "ADR-005 · Validar a sessão no Supabase Auth e consultar o papel no banco"
description: "Decisão de validar o token Bearer no Supabase Auth e carregar o papel persistido em profiles."
---

# ADR-005 · Validar a sessão no Supabase Auth e consultar o papel no banco

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-03; RF01, RF03, RF04 |
| Substitui | Nenhuma ADR |

## Contexto

A API precisa identificar a conta autenticada, exigir confirmação de e-mail e verificar seu papel (`student`, `professor`, `admin`) sem confiar em metadados ou valores declarados pelo navegador.

## Decisão

Validar o token `Authorization: Bearer <token>` consultando o Supabase Auth (com timeout de 5 segundos), exigir endereço de e-mail confirmado e carregar `profiles.papel` a partir do banco de dados pelo ID autenticado. Sessão ausente ou inválida retorna `401`; falha do serviço de autenticação retorna `503`; perfil ausente ou e-mail não confirmado retorna `403`.

## Alternativas para comparação

Validar JWT apenas localmente reduziria chamadas ao serviço de autenticação, mas exigiria gestão de chaves públicas e não refletiria imediatamente revogações de conta. Confiar no papel informado pelo cliente violaria o controle de acesso.

## Consequências

Rotas protegidas dependem da disponibilidade do Supabase Auth e acrescentam uma consulta de perfil. Alterações de papel no banco passam a valer de imediato, sem depender do estado em cache no cliente.

## Orientações para contribuição e verificação

A referência de implementação está em `backend/src/middlewares/auth.py`. Verificar cenários de sessão ausente, token inválido, e-mail não confirmado, perfil ausente e indisponibilidade do Auth. Testes unitários que substituem a dependência de autenticação não validam a integração real com o Supabase Auth.

## Fontes e relações

[Fluxo da API](/arquitetura/visao-geral#5-api-rest-implementada) · [Contratos](/api-specs) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
