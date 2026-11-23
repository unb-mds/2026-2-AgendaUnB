---
title: "Reunião 11 — 27 de out. de 2026"
description: "Ata da Reunião 11 do Grupo 8 (MDS) — regularização documental, acompanhamento da Sprint 06 e alinhamento de carga e dependências."
sidebarTitle: "Ata 11 (27/10)"
---

**27 de out. de 2026 | Reunião 11 Grupo 8 MDS**  
**Sprint:** [Sprint 06](/sprints/sprint-6)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 11 em PDF](/processo/atas/pdf/ata-11.pdf)

## Anotações

- Revisão da **regularização documental concluída em `24/10`**: publicados [Contratos do backend](/api-specs) (`api-specs.md`) e [Plano de implantação](/implantacao) (`implantacao.md`), além da revisão da arquitetura (incluindo decisões pendentes de hospedagem, CI/CD e testes) e dos padrões do projeto.
- Balanço da apresentação intermediária de acompanhamento realizada em aula (`26/10`), expondo o estado atual da plataforma e reforçando a necessidade de equilibrar a distribuição de entregas e commits entre todos os integrantes.
- Acompanhamento técnico da **Sprint 06** (planos de ensino particulares, PDF com texto selecionável até 10 MB e 10 páginas):
  - **Banco de Dados:** avanço nas migrações de planos particulares e candidatos com procedência (`S6-D01`, Felipe) e políticas RLS + operação transacional idempotente de confirmação (`S6-D02`, Luis);
  - **Back-end:** priorização das entregas bloqueantes para o front-end — upload autenticado `POST /api/v1/syllabus/upload` (`#40`), consulta/confirmação (`S6-B02`, Thomaz) e definição do provedor de IA e worker assíncrono (`#51`, Heitor);
  - **Front-end:** implementação do envio e histórico em `/plano-de-ensino` (`S6-F01`, Thomas) e da interface de revisão assistida e importação (`S6-F02`, Gabriel).
- Diante das dependências concentradas no back-end, decidiu-se priorizar o fluxo completo de planos de ensino e reavaliar a necessidade de duplicar em REST o painel administrativo (`#38`), já operacional via RPCs Supabase.

## Ações necessárias

- Finalizar os Pull Requests de `#40`, `S6-D01`, `S6-D02` e `S6-B02`, resolvendo eventuais conflitos de migrações na branch `dev`.
- Definir o provedor de IA e os critérios de avaliação para a extração assíncrona de planos de ensino (`#51`).
- Realizar auditoria de branches e higiene do repositório antes do fechamento da Sprint 06 em `01/11`.
