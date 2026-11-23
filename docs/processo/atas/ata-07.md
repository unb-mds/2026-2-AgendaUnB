---
title: "Reunião 07 — 29 de set. de 2026"
description: "Ata da Reunião 7 do Grupo 8 (MDS) — balanço da Release 1 (28/09), correções de autenticação/Docker, campo de link externo e fechamento do MVP."
sidebarTitle: "Ata 07 (29/09)"
---

**29 de set. de 2026 | Reunião 7 Grupo 8 MDS**  
**Sprint:** [Sprint 04](/sprints/sprint-4)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 07 em PDF](/processo/atas/pdf/ata-07.pdf)

## Anotações

- Balanço da apresentação da **Release 1 (`v0.1.0`)**, realizada em **28/09/2026**: o produto funcional e a interface foram bem recebidos, mas a avaliação apontou a necessidade urgente de atualizar e aprofundar a documentação técnica e de produto no repositório e no GitHub Pages, além de formalizar a publicação da release e suas *release notes*.
- Registro das correções críticas integradas na véspera da R1:
  - **Autenticação (`#16`):** identificado por Felipe que os formulários de cadastro e login em `App.jsx` ainda não estavam vinculados ao Supabase e que o Google OAuth não transportava o papel do usuário; foram implementadas `signUpWithEmail`, `signInWithEmail` e `promoverParaProfessor` no `AuthContext`, validação de `@unb.br` (bloqueando `@aluno.unb.br`) diretamente no banco, criação do `.env.example` e atualização do callback OAuth local para a porta `14321`;
  - **Ambiente local:** padronização da execução com Docker + Supabase CLI (`npx supabase start` nas portas `14321`/`14322`) e FastAPI (`uvicorn src.main:app --reload`), além da adição das *skills* de IA do projeto (`#11`);
  - **Eventos e engajamento (`#14` e `#15`):** inclusão do campo de **link externo** (para redirecionamento a editais ou inscrições no SIGAA) e protótipo do contador de interessados/redirecionamentos na página de detalhes.
- Alinhamento para encerrar os ajustes restantes de integração da API de eventos (`#13`) e a consolidação da arquitetura (`#10`) até o fechamento da Sprint 04 em `04/10`.

## Ações necessárias

- Publicar a release `v0.1.0` com as *release notes* completas e atualizar o GitHub Pages.
- Concluir os testes ponta a ponta entre front-end, API FastAPI e Supabase, fechando formalmente as issues `#10` a `#16`.
- Preparar o planejamento da Sprint 05 com foco em calendário, moderação de sugestões, painel administrativo e saneamento documental.
