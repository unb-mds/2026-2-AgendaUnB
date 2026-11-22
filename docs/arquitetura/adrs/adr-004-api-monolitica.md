---
title: "ADR-004 · Manter a API em uma aplicação FastAPI única"
description: "Decisão de estruturar a API FastAPI como aplicação única organizada em módulos internos."
---

# ADR-004 · Manter a API em uma aplicação FastAPI única

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-01; RNF13 |
| Substitui | Nenhuma ADR |

## Contexto

A plataforma mantém uma API HTTP para eventos, agenda pessoal, catálogo de turmas, planos de ensino, lembretes, exportação Google Agenda e gestão de conta/privacidade, operando em infraestrutura gratuita com baixa sobrecarga operacional.

## Decisão

Manter uma aplicação FastAPI única organizada em módulos internos independentes sob `backend/src/modules/` (`account`, `classes`, `events`, `google_calendar`, `reminders` e `syllabus`), registrados em `backend/src/main.py` sob o prefixo `/api/v1`. A execução pesada e agendada (worker de planos, coletor institucional e sincronizador de catálogo) ocorre em processos CLI separados, sem fragmentar a API HTTP em microsserviços.

## Alternativas para comparação

Microsserviços permitiriam implantação independente por domínio, mas introduziriam comunicação entre serviços, latência de rede e custos operacionais incompatíveis com o projeto.

## Consequências

A implantação e o roteamento permanecem centralizados em um único serviço web, simplificando compartilhamento de middlewares (segurança, CORS, rate limit, limites de payload) e validação de sessão. A organização modular evita acoplamento excessivo entre domínios e preserva contratos HTTP consistentes.

## Orientações para contribuição e verificação

Verificar o registro dos routers e middlewares em `backend/src/main.py` e as suítes de testes dos módulos afetados. Esta ADR permite refatoração interna entre módulos; novos serviços HTTP separados exigem nova decisão.

## Fontes e relações

[Visão arquitetural](/arquitetura/visao-geral#3-stack-e-organizacao) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
