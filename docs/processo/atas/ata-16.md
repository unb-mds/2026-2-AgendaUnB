---
title: "Reunião 16 — 21 de nov. de 2026"
description: "Ata da Reunião 16 do Grupo 8 (MDS) — revisão pós-congelamento funcional, acabamento de interface, SEO na 1ª página, segurança e preparação para R2 (25/11)."
sidebarTitle: "Ata 16 (21/11)"
---

**21 de nov. de 2026 | Reunião 16 Grupo 8 MDS**  
**Sprint:** [Sprint 08](/sprints/sprint-8)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 16 em PDF](/processo/atas/pdf/ata-16.pdf)

## Anotações

- Revisão após o **congelamento funcional (`20/11/2026`)**: funcionalidades da **[Release 2 (`v0.2.0`)](/processo/release-notes/v0-2-0)** integradas no ambiente publicado (`agendaunb.com.br`), que também alcançou a **primeira página dos resultados do Google** com os ajustes de SEO.
- **Lista de acabamento e refinamento visual definida para fechamento:**
  - Corrigir sobreposição (`z-index`) do seletor na aba de planos de ensino atrás da listagem de turmas;
  - Remover texto informativo redundante na tela de planos já coberto pelos Termos de Uso e Política de Privacidade;
  - Simplificar a interface após conexão com o Google Agenda, centralizando a ação de desconexão em `/configuracoes`;
  - Padronizar a altura dos cards na grade de eventos (evitando distorção causada por quantidade variável de tags) e deliberar pela proporção **retangular** uniforme dos cards;
  - Concluir os últimos ajustes da exportação direta ao Google Agenda (`#82`) e da revogação de consentimento.
- **Verificações finais de qualidade (`#84`, `#85` e `#86`):**
  - **Segurança (`#84`, Luis e Felipe):** conferência da matriz cross-user, JWT, RLS, criptografia de tokens OAuth e ausência de dados sensíveis em logs;
  - **Homologação de RNFs (`#85`, Gabriel e equipe):** testes ponta a ponta em `agendaunb.com.br`, verificação de acessibilidade WCAG 2.1 AA nos temas claro e escuro, responsividade a partir de 360 px e validação entre navegadores;
  - **Documentação e pacote de entrega (`#86`, Thomas e Luis):** fechamento da documentação canônica no Mintlify (incluindo políticas de comunidade, matriz de rastreabilidade, ADRs, guia de implantação/rollback e release notes `v0.2.0`).
- Alinhamento da divisão de falas da apresentação, testes gerais por toda a equipe, **ensaio geral em `24/11`** e **aceite oficial da Release 2 em `25/11`**.

## Ações necessárias

- Aplicar os ajustes finais de acabamento visual (cards retangulares, seletor de planos e botão de desconexão do Google Agenda) e fechar a validação da exportação ao Google Agenda até `23/11`.
- Executar testes completos de ponta a ponta por todos os integrantes e validar todos os links e o build da documentação Mintlify.
- Realizar o ensaio geral em `24/11/2026` e conduzir a apresentação e o aceite oficial da **Release 2 (`v0.2.0`)** em `25/11/2026`.
