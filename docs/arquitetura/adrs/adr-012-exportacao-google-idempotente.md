---
title: "ADR-012 · Exportar por ação explícita para uma agenda Google secundária"
description: "Decisão, consequências e critérios de verificação: exportar por ação explícita para uma agenda google secundária."
---

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-18 |
| Rastreabilidade | RF21; RNF02 |
| Substitui | Nenhuma ADR |

Decisão implementada em `backend/src/modules/google_calendar/` (`router.py`, `service.py`, `export.py`), no frontend (`frontend/src/components/GoogleCalendarConnection.jsx`, `frontend/src/lib/ics.js`) e nas migrações `20261111150000`, `20261113174855`, `20261113212429` e `20261118130000`.

## Contexto

A exportação escreve em um serviço externo, pode falhar parcialmente e não deve duplicar eventos quando repetida, exigindo consentimento específico separado da autenticação principal e proteção de credenciais OAuth.

## Decisão

Solicitar permissão de calendário sob demanda em **Meus Eventos**, inclusive para sessões por senha, exigindo e-mail confirmado na conta (`POST /api/v1/me/google-calendar/authorization`):

- **Escopo mínimo:** solicitar exclusivamente `https://www.googleapis.com/auth/calendar.app.created`, impedindo leitura ou escrita na agenda principal ou em agendas privadas preexistentes.
- **Segurança OAuth e armazenamento:** validar `state` de uso único com expiração de 10 minutos (persistido como SHA-256 no banco), desafio PKCE S256 e igualdade de e-mail verificado vinculando pelo `sub` Google. Tokens de acesso e refresh são cifrados em repouso com algoritmo simétrico Fernet (`GOOGLE_TOKEN_ENCRYPTION_KEY`) exclusivamente no servidor.
- **Prévia, exportação idempotente, reexportação e recuperação:** criar ou reutilizar a agenda secundária **Agenda UnB**. Antes de reexportar itens alterados, consultar `POST /api/v1/me/google-calendar/exports/preview` para classificar cada evento em `create`, `update` ou `unchanged` e solicitar confirmação explícita de sobrescrita (`requires_overwrite_confirmation`). Exportar itens selecionados via `POST /api/v1/me/google-calendar/exports` (com `Idempotency-Key` opcional, `allow_managed_field_updates` e `include_description`) usando IDs determinísticos base32hex gerados por SHA-256 (`user_id:kind:event_id`) e persistindo o mapeamento em `public.google_calendar_event_exports` (`user_id`, `event_kind`, `local_event_id`, `calendar_id`, `google_event_id`, `exported_version`, `status`, `last_idempotency_key`). Eventos de dia inteiro usam `start.date` e `end.date` exclusivo (`YYYY-MM-DD`), e eventos com horário usam `dateTime` em `America/Sao_Paulo` com `ends_at` ou duração de 1 hora ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)). Suportar recuperação ou recriação de agenda excluída (`404`/`410`) via `PUT /api/v1/me/google-calendar/destination` (`calendar_id: null` limpa o destino antigo e os mapeamentos associados), reconciliação de timeout/concorrência (`409 Conflict`) e espera limitada em `429` (`Retry-After` até 2 segundos, 1 retry).
- **Desconexão, cache e ICS complementar:** `DELETE /api/v1/me/google-calendar/connection` invoca o endpoint de revogação oficial do Google (`https://oauth2.googleapis.com/revoke`) e remove os tokens cifrados do banco, preservando os eventos já exportados remotamente. Se o Google retornar `401`/`403` (permissão revogada) ou `invalid_grant`, o servidor limpa as credenciais locais e retorna `409` exigindo reconexão. Respostas das rotas de conexão e exportação utilizam `Cache-Control: no-store`. Oferecer exportação `.ics` (RFC 5545, com `VTIMEZONE` `America/Sao_Paulo`, `UID` determinístico `<kind>-<id>@agendaunb.unb.br`, UTF-8, escape e line folding de 75 octetos) complementar para Apple Calendar e Outlook.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Escrever na agenda principal ampliaria o impacto. Sincronização automática exigiria resolver conflitos continuamente e fica fora da R2. Somente ICS não atenderia à exportação direta prevista.

## Consequências

Credenciais permanecem no backend. Atualizar campos geridos exige confirmação; repetir lote não amplia essa autorização. A pessoa pode desconectar pela Agenda UnB. O backend revoga o acesso no Google e remove os tokens, preservando os eventos remotos. Exclusão local não apaga a cópia remota. A primeira criação do calendário exige serialização e recuperação de resposta perdida.

## Orientações para contribuição e verificação

Verificar e-mail divergente, retry sem duplicação, falha parcial, resposta perdida, desconexão e destino excluído. PDFs, texto integral de planos e tokens ficam fora da exportação. Validar o consentimento de calendário separadamente do login.

## Fontes e relações

[Google Agenda e ICS](/atualizacoes#google-agenda-e-ics) · [Matriz de aceite](/matriz-release-2) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
