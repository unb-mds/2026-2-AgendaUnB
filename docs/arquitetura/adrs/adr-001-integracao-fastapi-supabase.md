---
title: "ADR-001 · Integração entre FastAPI e Supabase"
---

# ADR-001 · Usar FastAPI para a API de negócio e Supabase para Auth e RPCs administrativas

**Estado** Implementada. Registro retrospectivo de DA-02.

## Contexto

O frontend usa Supabase Auth para a sessão e a FastAPI para operações de eventos e agenda. Moderação e gestão de papéis dependem do papel real do usuário, do estado do registro e de verificações que precisam valer também para chamadas diretas. O registro original descreve a solução observada. A motivação histórica e as alternativas avaliadas na época não estão documentadas.

## Decisão

O frontend usa a FastAPI para os recursos de negócio e o SDK do Supabase para autenticação, perfis, notificações e RPCs administrativas. As RPCs verificam o papel no banco ao moderar sugestões ou alterar papéis. As políticas RLS controlam o acesso aos dados expostos pelo SDK. A FastAPI verifica sessão, papel ou propriedade conforme o recurso.

## Alternativas para uma revisão futura

Uma API única poderia mediar também as operações administrativas. Isso reduziria os caminhos públicos de integração, mas exigiria migrar os fluxos atuais e preservar as verificações e transações no banco.

## Consequências

A equipe mantém dois caminhos de acesso. Cada operação precisa de autorização no ponto que a executa, inclusive quando uma conexão administrativa da API ignora RLS. Os testes de RPC e RLS em PostgreSQL complementam os testes da API e da interface.

[Visão geral e evidências](../visao-geral.md) · [Guia do painel administrativo](../../painel-administrativo.md) · [Contratos da API](../../api-specs.md)

## Leitura e manutenção

Data deste registro complementar: **2026-11-08**; não representa a data original de aprovação. Nenhuma ADR é substituída por este registro. O estado acima distingue implementação, proposta e decisão da R2; não constitui evidência de homologação.

Consulte o [índice de ADRs](index.md) para o mapa de decisões e o modelo de novos registros. As alternativas são comparações para revisão, não atas de uma avaliação histórica.
