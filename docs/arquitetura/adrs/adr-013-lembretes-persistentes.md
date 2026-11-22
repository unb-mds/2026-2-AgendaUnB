---
title: "ADR-013 · Persistir lembretes com agendamento idempotente e revalidação"
description: "Decisão de agendar lembretes persistentes via triggers no PostgreSQL e dispará-los periodicamente com revalidação."
---

# ADR-013 · Persistir lembretes com agendamento idempotente e revalidação

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | RF13, RF17 |
| Substitui | Nenhuma ADR |

## Contexto

O usuário precisa visualizar avisos de proximidade dos seus compromissos ao retornar à plataforma, mesmo que o navegador ou a API estivessem fechados no momento do disparo. Eventos e vínculos podem ser alterados ou removidos entre o agendamento e a hora prevista do aviso.

## Decisão

Persistir lembretes na tabela `lembretes` exatamente 24 horas antes do início de cada compromisso pessoal (`eventos_pessoais`) ou evento público salvo (`eventos_salvos`):

- **Regra de horário:** para eventos com hora marcada, o disparo é agendado para `inicio - 24 horas`. Para eventos de dia inteiro, utiliza-se a meia-noite de `America/Sao_Paulo` do primeiro dia civil ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)).
- **Manutenção por triggers:** triggers no PostgreSQL agendam o lembrete na criação ou salvamento, recalculam quando a data de início muda e cancelam pendências após exclusão do compromisso, remoção do vínculo ou retirada do evento público do catálogo. Entradas na agenda faltando 24 horas ou menos para o início não geram alerta retroativo.
- **Unicidade e disparo atômico:** índices únicos parciais por conta, evento e `inicio_referencia` impedem duplicatas. O job periódico `public.disparar_lembretes()` via Supabase Cron (`pg_cron`, a cada 5 minutos) utiliza `FOR UPDATE SKIP LOCKED`, revalida elegibilidade e torna os avisos visíveis na central uma única vez, descartando pendências cujo evento já iniciou.
- **Leitura isolada:** a API (`GET /api/v1/me/reminders` e `PUT /api/v1/me/reminders/{id}/read`) e as políticas RLS permitem a cada conta ler apenas os próprios avisos disparados e registrar `lido_em` preservando a primeira leitura.

## Alternativas para comparação

Alertas apenas no navegador dependeriam de a aba estar aberta no instante exato. Disparar sem revalidar o evento e o vínculo notificaria sobre compromissos cancelados ou removidos. E-mail não é o canal adotado para lembretes de proximidade, permanecendo restrito aos fluxos de autenticação.

## Consequências

O funcionamento dos lembretes independe de sessão aberta no navegador ou de requisições HTTP contínuas na API. As notificações de moderação de sugestões (`notificacoes`) permanecem um fluxo separado, compartilhando apenas a interface do sino na barra de navegação.

## Orientações para contribuição e verificação

Verificar criação 24 horas antes, ausência de alerta tardio, recálculo ao alterar início, cancelamento ao excluir/remover vínculo/rejeitar evento, comportamento para dia inteiro, idempotência do disparo concorrente e isolamento entre contas (`backend/tests/test_reminders_database.py`, `backend/tests/test_reminders_api.py` e `frontend/tests/reminders.spec.js`).

## Fontes e relações

[Dados de eventos](/arquitetura/dados-de-eventos#3-lembretes) · [Contratos da API](/api-specs#lembretes-da-agenda) · [Implantação](/implantacao) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
