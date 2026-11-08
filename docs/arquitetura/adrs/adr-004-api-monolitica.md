---
title: "ADR-004 · Manter a API em uma aplicação FastAPI única"
description: "Decisão, consequências e critérios de verificação: manter a api em uma aplicação fastapi única."
---

# ADR-004 · Manter a API em uma aplicação FastAPI única

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-01; RNF13 |
| Substitui | Nenhuma ADR |

Registro retrospectivo; a motivação histórica e as alternativas avaliadas na época não estão documentadas.

## Contexto

A equipe mantém uma API de negócio com módulos de eventos e planos. A visão arquitetural registra uma aplicação única, sem microsserviços.

## Decisão

Manter uma aplicação FastAPI organizada em módulos internos. O módulo events concentra rotas, schemas, consultas e regras de eventos; main.py também registra o módulo syllabus. Isso não exige colocar todas as funcionalidades no mesmo router.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Microsserviços permitiriam implantação independente, mas introduziriam comunicação e operação distribuídas. Uma camada de serviços poderia separar regras dos routers sem mudar a unidade de implantação.

## Consequências

A operação permanece concentrada. Routers extensos aumentam o acoplamento; futuras separações internas devem preservar os contratos existentes.

## Orientações para contribuição e verificação

Verificar o registro dos routers em backend/src/main.py e os testes dos módulos afetados. Esta ADR permite refatoração interna; não aprova novos serviços externos.

## Fontes e relações

[Visão arquitetural](../visao-geral.md#3-stack-e-organizacao) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
