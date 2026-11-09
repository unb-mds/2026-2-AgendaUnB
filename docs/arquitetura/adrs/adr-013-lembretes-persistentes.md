---
title: "ADR-013 · Persistir lembretes com agendamento idempotente e revalidação"
description: "Decisão, consequências e critérios de verificação: persistir lembretes com agendamento idempotente e revalidação."
---

# ADR-013 · Persistir lembretes com agendamento idempotente e revalidação

| Campo | Valor |
| --- | --- |
| Estado | Aceita para a Release 2 |
| Data do registro | 2026-11-08 |
| Rastreabilidade | RF13, RF17 |
| Substitui | Nenhuma ADR |

Registro de decisão já descrita nos contratos da R2; não comprova implementação ou homologação.

## Contexto

O usuário deve encontrar o aviso ao retornar à plataforma. Eventos e vínculos podem mudar entre o agendamento e o disparo.

## Decisão

Persistir aviso na plataforma 24 horas antes do início do evento da própria agenda. Para dia inteiro, usar meia-noite do primeiro dia em Brasília. Identificar a tarefa por conta, tipo e ID do evento e instante de referência; revalidar elegibilidade no disparo. Recalcular após mudança de início e cancelar pendências após exclusão, remoção do vínculo ou retirada do catálogo.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Alertas apenas no navegador dependeriam de a página estar aberta. Disparar sem revalidar o vínculo poderia avisar sobre itens removidos. E-mail não é o canal previsto para esses lembretes.

## Consequências

Entrada na agenda após o instante de disparo não gera alerta retroativo. Job já agendado e atrasado pode ser retomado antes do início uma única vez. A leitura é restrita à conta e retries preservam o primeiro read_at. A tecnologia do scheduler ainda depende da prova de infraestrutura.

## Orientações para contribuição e verificação

Verificar duplicatas, atraso, cancelamento, mudança de horário e isolamento por conta. Notificações atuais de moderação são outro fluxo e não comprovam implementação dos lembretes.

## Fontes e relações

[Agenda e lembretes](../../atualizacoes.md#agenda-redirecionamento-e-lembretes) · [Implantação](../../implantacao.md) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
