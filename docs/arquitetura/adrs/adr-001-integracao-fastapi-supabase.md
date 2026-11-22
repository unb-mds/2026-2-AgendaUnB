---
title: "ADR-001 · Integração entre FastAPI e Supabase"
description: "Decisão de dividir o tráfego entre API de negócio FastAPI e Supabase Auth/RPCs administrativas."
---

# ADR-001 · Usar FastAPI para a API de negócio e Supabase para Auth e RPCs administrativas

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-02; RF01, RF04, RF11, RF14 |
| Substitui | Nenhuma ADR |

## Contexto

O frontend utiliza Supabase Auth para a sessão e a FastAPI para operações de eventos, agenda, catálogo de turmas, planos de ensino, lembretes, conta e exportação para o Google Agenda. Moderação de sugestões e gestão de usuários dependem do papel real da conta no banco e de verificações que precisam valer também para chamadas diretas via SDK.

## Decisão

O frontend utiliza a FastAPI para os recursos de negócio e o SDK do Supabase para autenticação, leitura de perfis, notificações e RPCs de moderação/administração:

- **Negócio via FastAPI:** leitura e escrita de eventos públicos e pessoais, envio de sugestões de estudantes (`POST /api/v1/suggestions`), catálogo de turmas, planos de ensino, lembretes, gestão de conta/privacidade e conexão/exportação com o Google Agenda.
- **Moderação e administração via RPCs Supabase:** o frontend (`frontend/src/lib/moderation.js`) chama diretamente `listar_sugestoes`, `listar_revisoes_coleta` e `moderar_sugestao` (para professores e administradores) e `admin_buscar_usuarios`, `admin_definir_papel`, `admin_listar_categorias`, `admin_criar_categoria` e `admin_excluir_categoria` (apenas para administradores). A FastAPI expõe também as rotas de categorias em `/api/v1/categories` com a mesma exigência de papel `admin` nas operações de escrita.
- **Notificações transacionais:** envio, aprovação e recusa de sugestões persistem notificações em `notificacoes` por trigger na mesma transação do evento, com leitura e marcação de leitura restritas ao destinatário via RLS.
- **Navegação da interface:** `/eventos` reúne eventos públicos e agenda pessoal (`/segunda-pagina` redireciona preservando parâmetros); `/plano-de-ensino` atende o fluxo de turmas e planos; `/sugestoes` atende professores e administradores; `/admin` é restrita a administradores; `/configuracoes` atende preferências legais, exportação e exclusão de conta; o sino de notificações é exibido a todas as contas autenticadas para lembretes e inclui a aba de sugestões para estudantes.

## Alternativas para comparação

Uma API única poderia mediar também todas as operações de moderação e administração. Isso reduziria os caminhos públicos de integração, mas exigiria migrar os fluxos já acoplados ao SDK do Supabase mantendo as verificações transacionais no banco.

## Consequências

A arquitetura mantém dois caminhos de acesso ao banco. Cada operação exige autorização no ponto que a executa, inclusive quando a conexão administrativa da API ignora RLS. Os testes de RPC e RLS em PostgreSQL complementam os testes de contrato HTTP da API e da interface.

## Fontes e relações

[Visão geral](/arquitetura/visao-geral) · [ADR-006](/arquitetura/adrs/adr-006-autorizacao-em-camadas) · [Contratos da API](/api-specs) · [Índice de ADRs](/arquitetura/adrs/index)
