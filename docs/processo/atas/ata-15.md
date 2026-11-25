---
title: "Reunião 15 — 17 de nov. de 2026"
description: "Ata da Reunião 15 do Grupo 8 (MDS) — acompanhamento da Sprint 08, compartilhamento automático de v1, refinamento da extração, Followw, SEO e roteiro da R2."
sidebarTitle: "Ata 15 (17/11)"
---

**17 de nov. de 2026 | Reunião 15 Grupo 8 MDS**  
**Sprint:** [Sprint 08](/sprints/sprint-8)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 15 em PDF](/processo/atas/pdf/ata-15.pdf)

## Anotações

- **Validações concluídas e métricas iniciais:**
  - Fluxo de redefinição e confirmação de senha por e-mail via SMTP ativo em produção; painel da Vercel registrando os primeiros acessos orgânicos externos e evolução de **SEO** da página 10 para a página 3 do Google;
  - Coletor da **Agenda UnB Notícias** (`#75`) validado em `16/11` com deduplicação, datas civis ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)) e suítes completas de back-end, PostgreSQL e front-end.
- **Refinamentos de extração e integração Followw:**
  - Ajustes no extrator Gemini para reconhecer datas em formatos variados (inclusive quando antecedem o nome da avaliação) e sugerir automaticamente o horário inicial da prova com base no horário da turma no formato UnB;
  - Alinhamento com a equipe do **Followw** após alteração de rota da API (`api.followw.app`) e acompanhamento de nova interface para consulta de planos de ensino.
- **Decisões de produto e governança de banco:**
  - **Decisão do PO (Thomas):** a versão inicial (`v1`) de plano vinculada a oferta passa a ser **compartilhada automaticamente** ao concluir a extração com candidatos, mantendo retirada a qualquer momento sem perder cópias importadas ([ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos)); entrega de `#77` validada com `20261117150000_planos_compartilhamento_e_votos.sql`;
  - Regra operacional de migrações: sempre consultar `dev` e PRs abertos usando o timestamp do dia para evitar colisões (369 testes passando após renumeração e liberação de `listar_eventos_publicos` para visitantes).
- **Preparação para R2 e homologação:** liberação do papel `admin` para todos os integrantes no ambiente publicado, revisão do comportamento de logout no perfil, elaboração do documento `roteiro_release_2.md` e acompanhamento das entregas de `#78` a `#83`.

## Ações necessárias

- Concluir e integrar `#78`, `#79`, `#80`, `#81`, `#82` e `#83` até o congelamento funcional em `20/11`.
- Revisar a exportação direta ao Google Agenda (`#82`) e executar a auditoria de segurança cross-user (`#84`) e homologação de RNFs (`#85`).
- Refinar o `roteiro_release_2.md` e a documentação canônica no Mintlify (`#86`) para a revisão pós-congelamento em `21/11`.
