---
title: "Reunião 10 — 18 de out. de 2026"
description: "Ata da Reunião 10 do Grupo 8 (MDS) — revisão da Sprint 05, introdução do Makefile, padronização de PRs e planejamento da Sprint 06."
sidebarTitle: "Ata 10 (18/10)"
---

**18 de out. de 2026 | Reunião 10 Grupo 8 MDS**  
**Sprint:** [Sprint 05](/sprints/sprint-5)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 10 em PDF](/processo/atas/pdf/ata-10.pdf)

## Anotações

- Revisão das melhorias operacionais incorporadas ao projeto:
  - Introdução do **`Makefile`** (`make dev`, `make help` e comandos de banco com Docker ativo), unificando a inicialização do Supabase, back-end e front-end;
  - Padronização do fluxo de integração: todos os Pull Requests de código devem apontar para a branch `dev` (mantida como referência atualizada), reservando atualizações diretas na `main` apenas para documentação quando aplicável;
  - Criação de conta de teste com perfil `admin` no ambiente local para validação do fluxo de moderação e gestão de usuários.
- Balanço da **Sprint 05**:
  - **Concluídas:** visualização em calendário (`#36`), painel administrativo e sugestões via RPCs (`#37`), modelagem de sugestões/contador (`#41`), RLS administrativo (`#42`), bucket privado `syllabus_files` (`#43`) e artefatos de Produto e UX (`#44`);
  - **Realocadas para o back-end na Sprint 06:** endpoints FastAPI do painel (`#38`) e upload base de planos (`#40`), sem refazer telas nem bucket já entregues;
  - **Pendentes em aberto:** especificações técnicas (`#39`) e saneamento de lacunas documentais (`#45`), priorizadas para resolução imediata.
- Planejamento da **Sprint 06 (`19/10` a `01/11`)**, dedicada à primeira jornada completa de planos de ensino particulares (PDF com texto selecionável até 10 MB e 10 páginas, extração assistida por IA, revisão manual e confirmação transacional na agenda pessoal), com duas issues principais por frente (`S6-F01`, `S6-F02`, `S6-B01`, `S6-B02`, `S6-D01`, `S6-D02`, somadas a `#38` e `#40`).

## Ações necessárias

- Fechar as pendências documentais (`api-specs.md`, `implantacao.md`, especificações de banco/back-end e revisão da arquitetura).
- Alinhar payloads e estados de processamento de planos (`pendente`, `processando`, `concluido`, `falha`) entre banco, back-end e front-end.
- Iniciar a modelagem de planos particulares e candidatos (`S6-D01`) e a camada de privacidade e confirmação transacional (`S6-D02`).
