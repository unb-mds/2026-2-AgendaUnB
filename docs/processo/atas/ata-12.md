---
title: "Reunião 12 — 01 de nov. de 2026"
description: "Ata da Reunião 12 do Grupo 8 (MDS) — revisão da Sprint 06, higiene de branches, descoberta do Followw, decisão sobre RPCs e prévia v0.2.0-beta.1."
sidebarTitle: "Ata 12 (01/11)"
---

**01 de nov. de 2026 | Reunião 12 Grupo 8 MDS**  
**Sprint:** [Sprint 06](/sprints/sprint-6)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 12 em PDF](/processo/atas/pdf/ata-12.pdf)

## Anotações

- Revisão da **auditoria de higiene do repositório** conduzida por Felipe (`29/10`): mapeamento de 21 branches já integradas à `dev` para limpeza, ativação da exclusão automática de *head branches* pós-merge, reconciliação de conflitos de documentação editada diretamente na `main` (`modelo-de-dados.md` e `especificacao-banco-de-dados.md`) e correção do conflito de migrações (`column status already exists`) entre o upload (`#40`) e `S6-D01`.
- Consolidação da **Sprint 06** e da prévia **[v0.2.0-beta.1](/processo/release-notes/v0-2-0-beta-1)**:
  - Entregues consulta, revisão e confirmação na API (`S6-B01`, originalmente `S6-B02`, por Thomaz), envio real de PDFs (`#40`), base de dados/transação (`S6-D01`/`S6-D02`), rota `/eventos` (com redirecionamento de `/segunda-pagina`), eventos salvos e notificações de moderação;
  - **Decisão arquitetural (`#38`):** mantidas as **RPCs do Supabase** como interface única do painel administrativo, removendo rotas REST duplicadas ([ADR-001](/arquitetura/adrs/adr-001-integracao-fastapi-supabase) e [ADR-006](/arquitetura/adrs/adr-006-autorizacao-em-camadas));
  - **Realocação:** a extração assíncrona com IA (`#51`) segue para a Sprint 7 como `S7-B01` (Heitor), apoiada na especificação completa da jornada de planos (PDF e entrada de texto até 50 mil caracteres, fila persistida no PostgreSQL e benchmark comparativo entre provedores).
- **Descoberta estratégica — Followw (`followw.app`):** o grupo avaliou o catálogo público do Followw como alternativa viável e resiliente ao *scraping* frágil do SIGAA, decidindo contatar a equipe responsável e testar os endpoints públicos na Sprint 7.
- Alinhamento do calendário rumo à **Release 2 (`25/11/2026`)**, dividindo o trabalho restante entre a **Sprint 7 (`07/11` a `15/11`)** e a **Sprint 8 (`16/11` a `23/11`)**.

## Ações necessárias

- Contatar a equipe do Followw e validar os endpoints públicos de turmas e disciplinas em orçamento zero (`#68`).
- Consolidar os contratos oficiais e a matriz de aceite da Release 2 (`S7-F01` / `#67`) e escolher o provedor de IA.
- Estruturar a infraestrutura de filas, CI e deploy inicial na Vercel na abertura da Sprint 7.
