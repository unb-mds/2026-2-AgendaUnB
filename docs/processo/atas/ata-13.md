---
title: "Reunião 13 — 10 de nov. de 2026"
description: "Ata da Reunião 13 do Grupo 8 (MDS) — migração da documentação para Mintlify, escolha do Gemini, deploy inicial na Vercel e política de 1 PR por issue."
sidebarTitle: "Ata 13 (10/11)"
---

**10 de nov. de 2026 | Reunião 13 Grupo 8 MDS**  
**Sprint:** [Sprint 07](/sprints/sprint-7)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 13 em PDF](/processo/atas/pdf/ata-13.pdf)

## Anotações

- **Migração da documentação para o Mintlify:** diante do bloqueio/sinalização indevida do GitHub Pages da disciplina, a documentação oficial foi migrada para o **Mintlify** (`agenda-un-b.mintlify.app`), garantindo disponibilidade contínua e futura vinculação ao domínio próprio na Vercel.
- **Escolha do provedor de IA e privacidade:** confirmado o uso da API gratuita do **Gemini** com tratamento e minimização prévia de dados sensíveis antes do envio, descarte local do PDF após extração e validação em corpus sintético (`S7-B01` / `#51`, benchmarks de `09/11` e `10/11`, [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos) e [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia)).
- **Contratos, infraestrutura gratuita e deploy inicial:**
  - Contratos da Release 2 consolidados (`S7-F01` / `#67`, esclarecimentos de `08/11` e adoção da *skill* `project-standards` antes de cada implementação);
  - Publicação da primeira URL HTTPS na **Vercel** (`2026-2-agendaunb.vercel.app`) antes da meta de `12/11`;
  - Banco de dados e CI entregues por Luis para `#68` (GitHub Actions com lint/testes Supabase e tabela `fila_processamento_ia`) e `#75` (tabela de triagem `eventos_coletados` com `url_origem UNIQUE` e `status_revisao`), além da modelagem de ofertas/versões (`#69`, Felipe) aplicada no Supabase Cloud.
- **Governança de Git e resolução de conflitos:** após colisões de numeração de migrações (`20261110120000`) e branches desatualizadas, instituiu-se oficialmente a regra de **uma única branch e um único PR por issue** com template padronizado (`status: <incompleto>` / `<completo>` em Draft até conclusão integral dos checks) e revisão semanal sincronizada com `dev`.

## Ações necessárias

- Concluir o lado de back-end das provas de orçamento zero (`#68`: hospedagem/worker, Gemini, Google Calendar OAuth, SMTP e Followw) e da coleta da Agenda UnB Notícias (`#75`).
- Renumerar e alinhar as migrações pendentes nos PRs abertos para manter ordem idêntica entre ambiente local e Supabase Cloud.
- Integrar catálogo Followw (`#70`/`#71`), fluxo real de planos (`#72`/`#73`) e autenticação com SMTP (`#74`) no ambiente publicado até `15/11`.
