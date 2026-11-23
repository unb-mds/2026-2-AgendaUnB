---
title: "Reunião 06 — 20 de set. de 2026"
description: "Ata da Reunião 6 do Grupo 8 (MDS) — feedbacks da apresentação em aula, riscos do scraping do SIGAA, modo visitante e organização por issues de sprint."
sidebarTitle: "Ata 06 (20/09)"
---

**20 de set. de 2026 | Reunião 6 Grupo 8 MDS**  
**Sprint:** [Sprint 03](/sprints/sprint-3)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 06 em PDF](/processo/atas/pdf/ata-06.pdf)

## Anotações

- Análise estruturada dos **cinco pontos de melhoria** apontados após a apresentação de 3 minutos em aula:
  - Reestruturar o Story Map seguindo corretamente a hierarquia (*Atividade → Épico* e *MVP → Feature*);
  - Revisar e corrigir os Requisitos Funcionais e Não Funcionais;
  - Reformular o escopo priorizando apenas o que é essencial para o produto;
  - Pesquisar projetos existentes na área para avaliar oportunidades de reuso;
  - Realizar *benchmark* comparativo.
- Discussão técnica sobre *scraping* direto do SIGAA: o grupo identificou dois riscos críticos — fragilidade a qualquer pequena alteração de interface do portal e instabilidade recorrente durante períodos de matrícula — passando a tratar a integração automatizada com cautela.
- Revisão das evoluções apresentadas no front-end em `19/09`: novo layout visual, ajuste solicitado em aula para permitir **entrada como visitante** (consulta pública sem login obrigatório) e roteamento inicial da segunda página da aplicação.
- Definição de mudança organizacional para a **Sprint 04 (`21/09` a `05/10`)**: todas as tarefas passam a ser rastreadas formalmente por *issues* vinculadas a *milestones* de sprint, garantindo ao menos uma *issue* atribuída a cada integrante e acelerando a integração de back-end e banco de dados para a Release 1 em `28/09`.

## Ações necessárias

- Registrar oficialmente a arquitetura do projeto (`Architecture.md`) e consolidar Skills e Specs no repositório (`#10` e `#11`).
- Estruturar o banco de dados no Supabase e implementar autenticação completa (`#12` e `#16`).
- Implementar a API de eventos em FastAPI (`#13`) e conectá-la ao catálogo e modal de detalhes no front-end (`#14` e `#15`).
