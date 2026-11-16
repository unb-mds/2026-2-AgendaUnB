---
title: "ADR-012 · Exportar por ação explícita para uma agenda Google secundária"
description: "Decisão, consequências e critérios de verificação: exportar por ação explícita para uma agenda google secundária."
---

# ADR-012 · Exportar por ação explícita para uma agenda Google secundária

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-15 |
| Rastreabilidade | RF21; RNF02 |
| Substitui | Nenhuma ADR |

Decisão implementada em `backend/src/modules/google_calendar/` (`router.py`, `service.py`, `export.py`) e nas migrações `20261111150000`, `20261113174855` e `20261113212429`.

## Contexto

A exportação escreve em um serviço externo, pode falhar parcialmente e não deve duplicar eventos quando repetida, exigindo consentimento específico separado da autenticação principal e proteção de credenciais OAuth.

## Decisão

Solicitar permissão de calendário sob demanda em **Meus Eventos**, inclusive para sessões por senha, exigindo e-mail confirmado na conta (`POST /api/v1/me/google-calendar/authorization`):

- **Escopo mínimo:** solicitar exclusivamente `https://www.googleapis.com/auth/calendar.app.created`, impedindo leitura ou escrita na agenda principal ou em agendas privadas preexistentes.
- **Segurança OAuth e armazenamento:** validar `state` de uso único com expiração de 10 minutos (persistido como SHA-256 no banco), desafio PKCE S256 e igualdade de e-mail verificado vinculando pelo `sub` Google. Tokens de acesso e refresh são cifrados em repouso com algoritmo simétrico Fernet (`GOOGLE_TOKEN_ENCRYPTION_KEY`) exclusivamente no servidor.
- **Exportação idempotente e recuperação:** criar ou reutilizar a agenda secundária Agenda UnB. Exportar itens selecionados via `POST /api/v1/me/google-calendar/exports` usando IDs determinísticos gerados por SHA-256 (`user_id:kind:event_id`) com mapeamento persistido por destino/evento; suportar recuperação de agenda excluída via `PUT /api/v1/me/google-calendar/destination`.
- **Desconexão e cache:** `DELETE /api/v1/me/google-calendar/connection` invoca o endpoint de revogação oficial do Google (`https://oauth2.googleapis.com/revoke`) e remove os tokens cifrados do banco, preservando os eventos já exportados remotamente. Respostas das rotas de conexão e exportação utilizam `Cache-Control: no-store`. Oferecer `.ics` complementar para outros clientes de calendário.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Escrever na agenda principal ampliaria o impacto. Sincronização automática exigiria resolver conflitos continuamente e fica fora da R2. Somente ICS não atenderia à exportação direta prevista.

## Consequências

Credenciais permanecem no backend. Atualizar campos geridos exige confirmação; repetir lote não amplia essa autorização. A pessoa pode desconectar pela Agenda UnB. O backend revoga o acesso no Google e remove os tokens, preservando os eventos remotos. Exclusão local não apaga a cópia remota. A primeira criação do calendário exige serialização e recuperação de resposta perdida.

## Orientações para contribuição e verificação

Verificar e-mail divergente, retry sem duplicação, falha parcial, resposta perdida, desconexão e destino excluído. PDFs, texto integral de planos e tokens ficam fora da exportação. Validar o consentimento de calendário separadamente do login.

## Fontes e relações

[Google Agenda e ICS](../../atualizacoes.md#google-agenda-e-ics) · [Matriz de aceite](../../matriz-release-2.md) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
