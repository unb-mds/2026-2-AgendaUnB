---
title: "Reunião 14 — 14 de nov. de 2026"
description: "Ata da Reunião 14 do Grupo 8 (MDS) — revisão da Sprint 07, domínio agendaunb.com.br, alinhamento de migrações/CI, ADRs e planejamento da Sprint 08."
sidebarTitle: "Ata 14 (14/11)"
---

**14 de nov. de 2026 | Reunião 14 Grupo 8 MDS**  
**Sprint:** [Sprint 07](/sprints/sprint-7)  
**Participantes:** Felipe Couto Duque, Gabriel Escramin Lourenço, Heitor Gomes Monteiro, Luis Davi Pontes da Silva, Thomas Augusto Amorim de Araujo, Thomaz Marra Martins.  
**Arquivo para download:** [Baixar Ata 14 em PDF](/processo/atas/pdf/ata-14.pdf)

## Anotações

- **Domínio próprio e ambiente publicado:** ativado o domínio oficial **`agendaunb.com.br`** integrado à Vercel e ao Supabase Cloud, com autenticação persistente operando em produção, criação de eventos validada e início dos ajustes de **SEO** para indexação nos mecanismos de busca.
- **Alinhamento de migrações e CI:** os 7 PRs de banco foram sincronizados com a branch `dev`, com migrações renumeradas sequencialmente (`20261111130000–160000`) para compatibilidade entre ambiente local e `npx supabase db push`, correção de bug na ordem de exclusão de conta, endurecimento de `EXECUTE` nas funções SQL e **311 testes automatizados passando** na simulação de CI.
- **Revisão da Sprint 07:**
  - Evidências de orçamento zero (`#68`) consolidadas e registradas nas decisões [ADR-002](/arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes), [ADR-009](/arquitetura/adrs/adr-009-catalogo-publico-de-turmas), [ADR-012](/arquitetura/adrs/adr-012-exportacao-google-idempotente) e [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia);
  - Integração do catálogo público Followw e tela *Minhas Turmas* (`#70`/`#71`), fluxo real de planos (`#72`/`#73`), configuração de SMTP para confirmação e redefinição de senha (`#74`) e ajustes finais de filtragem de datas longas no coletor da Agenda UnB Notícias (`#75`).
- **Planejamento da Sprint 08 (`16/11` a `23/11`, com congelamento funcional em `20/11`):** compartilhamento e votação de planos (`#77`/`#78`), eventos salvos e redirecionamento (`#79`), fechamento de eventos/moderação/categorias (`#80`), lembretes 24h (`#81`), exportação direta ao Google Agenda + ICS (`#82`), privacidade/LGPD (`#83`), segurança (`#84`), homologação RNF (`#85`) e documentação final (`#86`).

## Ações necessárias

- Finalizar a validação completa do coletor da Agenda UnB Notícias (`#75`) e do fluxo de confirmação/redefinição de senha via SMTP (`#74`).
- Integrar a camada de API sobre os PRs de banco já preparados para a Sprint 8 até o congelamento funcional em `20/11`.
- Avançar na documentação legal/LGPD (`#83`) e nos testes preventivos de segurança (`#84`) e performance (`#85`).
