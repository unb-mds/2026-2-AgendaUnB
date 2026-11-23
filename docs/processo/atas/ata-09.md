---
title: "Reunião 09 — 13 de out. de 2026"
description: "Ata da Reunião 9 do Grupo 8 (MDS) — acompanhamento da Sprint 05, unificação do ambiente, calendário, painel admin, RLS e bucket privado."
sidebarTitle: "Ata 09 (13/10)"
---

**13 de out. de 2026 | Reunião 9 Grupo 8 MDS**  
**Sprint:** [Sprint 05](/sprints/sprint-5)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 09 em PDF](/processo/atas/pdf/ata-09.pdf)

## Anotações

- Revisão das melhorias estruturais aplicadas ao repositório na primeira semana da Sprint 05: limpeza da estrutura de diretórios e **unificação do arquivo `.env`** em um único ponto na raiz (eliminando a duplicidade entre raiz e pasta `backend`), além da padronização dos comandos de inicialização local (`supabase start`, ambiente virtual Python e Vite).
- Acompanhamento das entregas em andamento na Sprint 05:
  - **Front-end:** avanço consistente na visualização em calendário mensal/semanal (`#36`) com alternância fluida entre Lista e Calendário, e no painel administrativo protegido (`/admin`) e fila de sugestões (`#37`) integrados via RPCs Supabase;
  - **Banco de Dados:** conclusão das migrações de sugestões de eventos e contador de interessados (`#41`), políticas RLS e RPCs administrativas (`#42`) e bucket privado `syllabus_files` com isolamento por `user_id` (`#43`);
  - **Produto e UX:** evolução de personas, wireframes de alta fidelidade (`#44`) e adoção da referência visual do *NoFluxo* para reestruturação do Story Map no Miro.
- Identificado gargalo de agenda no back-end para entregar na mesma janela os endpoints administrativos (`#38`), o upload de planos (`#40`) e a atualização da documentação de arquitetura (`#39`/`#45`). Foi alinhada a discussão técnica sobre como os planos de ensino serão analisados e extraídos no back-end na próxima sprint.

## Ações necessárias

- Automatizar a inicialização local do projeto (Docker, Supabase, back-end e front-end) via `Makefile`.
- Finalizar os ajustes responsivos e testes do calendário (`#36`), painel administrativo (`#37`) e artefatos UX (`#44`).
- Consolidar o balanço das pendências de back-end (`#38` e `#40`) e documentação (`#39` e `#45`) para a revisão da Sprint 05 em `18/10`.
