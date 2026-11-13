---
title: "ADR-012 · Exportar por ação explícita para uma agenda Google secundária"
description: "Decisão, consequências e critérios de verificação: exportar por ação explícita para uma agenda google secundária."
---

# ADR-012 · Exportar por ação explícita para uma agenda Google secundária

| Campo | Valor |
| --- | --- |
| Estado | Aceita para a Release 2 |
| Data do registro | 2026-11-08 |
| Rastreabilidade | RF21; RNF02 |
| Substitui | Nenhuma ADR |

Registro de decisão já descrita nos contratos da R2; não comprova implementação ou homologação.

## Contexto

A exportação escreve em um serviço externo, pode falhar parcialmente e não deve duplicar eventos quando repetida.

## Decisão

Solicitar permissão de calendário em todo login com Google via Supabase, validar o fluxo PKCE e a igualdade dos e-mails verificados, e vincular pelo sub Google. A sessão por senha não habilita a exportação direta. Criar ou reutilizar agenda secundária Agenda UnB. Exportar itens selecionados e autorizados em lotes assíncronos, com Idempotency-Key, mapeamento persistido e ID remoto estável por destino/evento. Reconciliar respostas incertas e retomar itens falhos ou pendentes. Oferecer ICS complementar.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Escrever na agenda principal ampliaria o impacto. Sincronização automática exigiria resolver conflitos continuamente e fica fora da R2. Somente ICS não atenderia à exportação direta prevista.

## Consequências

Credenciais permanecem no backend. Atualizar campos geridos exige confirmação; repetir lote não amplia essa autorização. A pessoa pode revogar o consentimento na Conta Google, preservando eventos remotos. Exclusão local não apaga a cópia remota. A primeira criação do calendário exige serialização e recuperação de resposta perdida.

## Orientações para contribuição e verificação

Verificar e-mail divergente, retry sem duplicação, falha parcial, resposta perdida, desconexão e destino excluído. PDFs, texto integral de planos e tokens ficam fora da exportação. Validar o consentimento de calendário recebido no login.

## Fontes e relações

[Google Agenda e ICS](../../atualizacoes.md#google-agenda-e-ics) · [Matriz de aceite](../../matriz-release-2.md) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
