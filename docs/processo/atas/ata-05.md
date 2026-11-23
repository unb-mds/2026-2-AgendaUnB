---
title: "Reunião 05 — 15 de set. de 2026"
description: "Ata da Reunião 5 do Grupo 8 (MDS) — debate de permissões/moderação, divisão de artefatos para a R1 (28/09), otimização de mídia e GitHub Pages."
sidebarTitle: "Ata 05 (15/09)"
---

**15 de set. de 2026 | Reunião 5 Grupo 8 MDS**  
**Sprint:** [Sprint 03](/sprints/sprint-3)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 05 em PDF](/processo/atas/pdf/ata-05.pdf)

## Anotações

- Debate aprofundado sobre **permissões e moderação de eventos**: avaliou-se o uso de IA com RAG (incluindo fluxo de recurso avaliado por administradores em caso de rejeição) frente à complexidade de controle de falsos positivos, convergindo para um modelo de autenticação com contas verificadas — login com Google/e-mail para estudantes e exigência de e-mail institucional `@unb.br` para professores.
- Consolidação do fluxo prático de versionamento: novas *branches* devem ser integradas primeiro em `dev` via Pull Request para validação conjunta antes de seguirem para `main`.
- Registro da otimização de mídia no front-end: o vídeo de fundo da página inicial foi comprimido de aproximadamente **15 MB para 1,6 MB**, melhorando significativamente o tempo de carregamento.
- Com a **Release 1 definida para 28/09/2026** e a apresentação de 3 minutos em aula agendada, os artefatos pendentes foram formalmente distribuídos entre as frentes:
  - **Front-end:** preenchimento do template do Figma e abertura de Issues;
  - **Back-end:** arquivo de Skills, refinamento de Specs e detalhamento de Requisitos Funcionais e Não Funcionais;
  - **Banco de Dados:** Product Canvas, Documento de Visão (já com PR aberto), Milestones e registro da documentação de **Uso de IA**.
- Revisão do Story Map elaborado no Miro e definição da rotina contínua de logs de reuniões, commits semanais, diário de bordo individual e publicação no **GitHub Pages**.

## Ações necessárias

- Apresentar em aula (em 3 minutos) os requisitos, Story Map, Product Canvas, Documento de Visão e GitHub Pages publicados.
- Avançar na autenticação/login e iniciar a análise de integração com dados acadêmicos (avaliando viabilidade e riscos de *scraping* do SIGAA).
- Incorporar imediatamente os feedbacks recebidos na aula seguinte ao planejamento da Sprint 04.
