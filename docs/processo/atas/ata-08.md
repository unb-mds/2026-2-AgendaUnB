---
title: "Reunião 08 — 04 de out. de 2026"
description: "Ata da Reunião 8 do Grupo 8 (MDS) — encerramento do MVP da Sprint 04, diretrizes para a R2 e planejamento da Sprint 05."
sidebarTitle: "Ata 08 (04/10)"
---

**04 de out. de 2026 | Reunião 8 Grupo 8 MDS**  
**Sprint:** [Sprint 04](/sprints/sprint-4)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 08 em PDF](/processo/atas/pdf/ata-08.pdf)

## Anotações

- Encerramento e validação da **Sprint 04**: todas as 7 issues do MVP (`#10` a `#16`) foram concluídas, cumprindo a *Definition of Done* com a aplicação integrada consultando eventos reais no banco via FastAPI, aplicando busca/filtros, exibindo detalhes e autenticando estudantes e professores.
- Alinhamento com o feedback pós-R1: reforçou-se que cada integrante deve dominar e saber explicar tecnicamente tudo o que implementa, pois a avaliação da Release 2 cobrará maior profundidade arquitetural e consistência documental.
- Planejamento da **Sprint 05 (`05/10` a `18/10`)**, combinando a entrega de novas funcionalidades centrais com a regularização das pendências documentais:
  - **Front-end:** visualização em calendário mensal e semanal (`#36`, Gabriel) e painel administrativo de moderação de eventos e gestão de usuários (`#37`, Thomas);
  - **Banco de Dados:** modelagem de sugestões de eventos e contador de interessados (`#41`), RLS e RPCs de segurança do painel administrativo (`#42`) e criação do bucket privado `syllabus_files` com RLS (`#43`) (Luis e Felipe);
  - **Back-end:** endpoints administrativos (`#38`) e endpoint base de upload de planos de ensino (`#40`) (Thomaz e Heitor);
  - **Documentação e UX:** especificações técnicas (`#39`), artefatos de Produto/UX no Figma (`#44`) e preenchimento de lacunas documentais (`#45`).

## Ações necessárias

- Reorganizar as pastas do repositório e unificar as variáveis de ambiente (`.env`) na raiz para simplificar o setup local.
- Iniciar imediatamente as migrações SQL (`#41`, `#42` e `#43`) e as telas de calendário (`#36`) e painel administrativo (`#37`).
- Revisar o Story Map e avançar nos artefatos de UX (`#44`) e na documentação técnica (`#39` e `#45`).
