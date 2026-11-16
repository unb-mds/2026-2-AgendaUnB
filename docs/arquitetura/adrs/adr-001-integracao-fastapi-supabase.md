---
title: "ADR-001 · Integração entre FastAPI e Supabase"
---

# ADR-001 · Usar FastAPI para a API de negócio e Supabase para Auth e RPCs administrativas

**Estado** Implementada. Registro retrospectivo de DA-02.

## Contexto

O frontend usa Supabase Auth para a sessão e a FastAPI para operações de eventos, agenda e planos de ensino. Moderação de sugestões e gestão de papéis dependem do papel real do usuário, do estado do registro e de verificações que precisam valer também para chamadas diretas. O registro original descreve a solução observada; a motivação histórica e as alternativas avaliadas na época não estão documentadas.

## Decisão

O frontend usa a FastAPI para os recursos de negócio e o SDK do Supabase para autenticação, perfis, notificações e RPCs administrativas:

- **Negócio via FastAPI:** leitura/escrita de eventos públicos e pessoais, envio de sugestões de estudantes (`POST /api/v1/suggestions`), catálogo de turmas, planos de ensino e conexão/exportação com o Google Calendar.
- **Moderação e administração exclusivamente via RPCs Supabase:** o frontend (`frontend/src/lib/moderation.js`) chama diretamente `listar_sugestoes` e `moderar_sugestao` (para professores e administradores) e `admin_buscar_usuarios` e `admin_definir_papel` (apenas para administradores). Não existem rotas `/api/v1/admin` duplicadas na FastAPI.
- **Notificações transacionais:** envio, aprovação e recusa de sugestões persistem notificações em `notificacoes` por trigger na mesma transação do evento, com leitura e marcação de leitura restritas ao destinatário via RLS.
- **Navegação da interface:** `/eventos` reúne eventos públicos e agenda pessoal (`/segunda-pagina` redireciona preservando parâmetros); `/plano-de-ensino` atende o fluxo de planos; `/sugestoes` atende professores e administradores; `/admin` é restrita a administradores; o sino de notificações é exibido para estudantes.

## Alternativas para uma revisão futura

Uma API única poderia mediar também as operações administrativas. Isso reduziria os caminhos públicos de integração, mas exigiria migrar os fluxos atuais e preservar as verificações e transações no banco.

## Consequências

A equipe mantém dois caminhos de acesso. Cada operação precisa de autorização no ponto que a executa, inclusive quando uma conexão administrativa da API ignora RLS. Os testes de RPC e RLS em PostgreSQL complementam os testes da API e da interface.

[Visão geral e evidências](/arquitetura/visao-geral) · [ADR-006](/arquitetura/adrs/adr-006-autorizacao-em-camadas) · [Contratos da API](/api-specs)

## Leitura e manutenção

Data deste registro complementar: **2026-11-08**; não representa a data original de aprovação. Nenhuma ADR é substituída por este registro. O estado acima distingue implementação, proposta e decisão da R2; não constitui evidência de homologação.

Consulte o [índice de ADRs](/arquitetura/adrs/index) para o mapa de decisões e o modelo de novos registros. As alternativas são comparações para revisão, não atas de uma avaliação histórica.
