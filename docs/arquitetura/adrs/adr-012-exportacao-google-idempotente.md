---
title: "ADR-012 · Exportar por ação explícita para uma agenda Google secundária"
description: "Decisão de exportar eventos mediante ação explícita do usuário para uma agenda Google secundária dedicada e com suporte complementar em .ics."
---

# ADR-012 · Exportar por ação explícita para uma agenda Google secundária

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-18 |
| Rastreabilidade | RF18; RNF02 |
| Substitui | Nenhuma ADR |

## Contexto

A exportação grava eventos em um serviço externo, pode sofrer falhas parciais de rede ou limite de taxa e não deve duplicar compromissos quando repetida. O fluxo também exige consentimento OAuth específico, separado da autenticação principal da plataforma, e proteção rigorosa de credenciais.

## Decisão

Solicitar permissão de calendário sob demanda em **Meus Eventos**, inclusive para sessões por e-mail e senha, exigindo conta com e-mail confirmado (`POST /api/v1/me/google-calendar/authorization`):

- **Escopo mínimo e projeto OAuth separado:** solicitar exclusivamente `openid`, `email` e `https://www.googleapis.com/auth/calendar.app.created` em um projeto Google Cloud dedicado ao Calendar (separado do login Supabase), impedindo leitura ou escrita na agenda principal ou em outras agendas privadas do usuário.
- **Segurança OAuth e armazenamento:** validar `state` de uso único com expiração de 10 minutos (armazenado como hash SHA-256 em `google_calendar_oauth_states`), desafio PKCE S256 e correspondência entre o e-mail verificado da conta Google e o e-mail confirmado da conta no Agenda UnB, vinculando pelo `sub` Google. Tokens de acesso e refresh são cifrados em repouso com Fernet (`GOOGLE_TOKEN_ENCRYPTION_KEY`) exclusivamente no servidor (`google_calendar_connections`).
- **Prévia, exportação idempotente, reexportação e recuperação:** criar ou reutilizar a agenda secundária **"Agenda UnB"**. Antes de reexportar itens alterados, consultar `POST /api/v1/me/google-calendar/exports/preview` para classificar cada evento (até 20 por lote) em `create`, `update` ou `unchanged`, informando `requires_overwrite_confirmation`. Exportar itens selecionados via `POST /api/v1/me/google-calendar/exports` (com `Idempotency-Key` opcional, `allow_managed_field_updates`, `include_description`, `start_date` e `end_date`) utilizando IDs determinísticos `base32hex` gerados por SHA-256 (`user_id:kind:event_id`) e persistindo o mapeamento em `public.google_calendar_event_exports` (`user_id`, `event_kind`, `local_event_id`, `calendar_id`, `google_event_id`, `exported_version`, `status`, `last_idempotency_key`).
- **Semântica de datas e privacidade no payload:** eventos de dia inteiro enviam `start.date` e `end.date` exclusivo (`YYYY-MM-DD`); eventos com horário enviam `dateTime` em `America/Sao_Paulo` com `ends_at` (quando posterior a `starts_at`) ou duração padrão de 1 hora ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)). `location` e `description` são enviados apenas quando aplicáveis (`include_description: true` para descrição), nunca incluindo PDFs, texto integral de planos ou tokens.
- **Recuperação de destino e tratamento de falhas:** suportar recuperação ou recriação de agenda excluída (`404`/`410`) via `PUT /api/v1/me/google-calendar/destination` (`calendar_id: null` limpa o destino antigo e invalida os mapeamentos associados), reconciliação de timeout/concorrência (`409 Conflict`) e espera limitada em `429` (`Retry-After` até 2 segundos, 1 nova tentativa).
- **Desconexão e ausência de sincronização bidirecional:** `DELETE /api/v1/me/google-calendar/connection` invoca a revogação oficial do Google (`https://oauth2.googleapis.com/revoke`) e remove os tokens cifrados do banco, preservando os eventos já exportados remotamente. Se o Google retornar `401`/`403` de permissão revogada ou `invalid_grant`, o servidor limpa as credenciais locais e retorna `409` orientando reconexão. Não há sincronização bidirecional: alterações ou exclusões no Agenda UnB não modificam nem apagam cópias no Google Agenda e vice-versa. Respostas das rotas de conexão e exportação utilizam `Cache-Control: no-store`.
- **Exportação `.ics` complementar:** em **Meus Eventos**, mesmo sem conexão Google ativa, oferecer download de arquivo `.ics` (RFC 5545) compatível com Apple Calendar e Outlook, com `VTIMEZONE` `America/Sao_Paulo`, `UID` determinístico (`<kind>-<id>@agendaunb.unb.br`), `DTSTAMP` UTC, `DTSTART`/`DTEND` com fuso ou `VALUE=DATE` exclusivo, codificação UTF-8, escape de caracteres especiais e *line folding* de 75 octetos (`frontend/src/lib/ics.js`).

## Alternativas para comparação

Escrever diretamente na agenda principal do usuário aumentaria o risco de interferência em compromissos pessoais preexistentes. Sincronização bidirecional automática exigiria resolução contínua de conflitos e webhooks externos. Oferecer apenas `.ics` atenderia importações pontuais, mas não a atualização idempotente direta no Google Agenda.

## Consequências

Credenciais e renovação de tokens permanecem restritas ao backend. Atualizar campos geridos exige confirmação explícita do usuário na prévia (`allow_managed_field_updates: true`); reenviar o lote sem essa confirmação preserva os itens remotos (`already_exported`). Falhas parciais devolvem estado por item (`exported`, `updated`, `already_exported`, `failed`), permitindo nova tentativa seletiva ou download em `.ics`.

## Orientações para contribuição e verificação

Verificar rejeição de e-mail divergente no callback, retry com `Idempotency-Key` sem duplicação, falha parcial por item, reconciliação após `409`, desconexão com revogação, recuperação de destino excluído (`404`/`410`) e conformidade RFC 5545 do `.ics` gerado.

## Fontes e relações

[Contratos da API](/api-specs#exportacao-para-o-google-calendar) · [Matriz de rastreabilidade](/matriz-rastreabilidade) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
