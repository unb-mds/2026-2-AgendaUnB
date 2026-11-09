---
title: "ADR-002 · Hospedagem e isolamento de ambientes"
---

# ADR-002 · Separar a hospedagem da SPA e da API e isolar ambientes

**Estado** Proposta. Corresponde à DA-07.

## Contexto

A aplicação tem uma SPA React/Vite, uma API Python e serviços de banco, autenticação e armazenamento no Supabase. O plano de implantação usa serviços gerenciados para reduzir manutenção. A homologação precisa permitir testes com dados fictícios antes da promoção da versão.

## Decisão proposta

Hospedar a SPA e a API separadamente e isolar os serviços e dados de homologação e produção. O plano original sugere Vercel para a SPA e Render para a API. A escolha final do provedor da API e dos serviços de execução de jobs depende da prova de infraestrutura da Sprint 7.

## Alternativas para avaliação

Hospedar a SPA junto da API reduziria a coordenação de domínios, mas ligaria o deploy do frontend ao runtime do backend. Compartilhar o banco entre ambientes reduziria o número de projetos a manter e aumentaria o risco de testes afetarem dados, usuários e segredos de produção.

## Consequências

A separação permite validar cada ambiente com os próprios dados e credenciais. Exige CORS, URLs de retorno do Auth e configurações de build por ambiente. A publicação precisa coordenar migrações, backend e frontend pelo mesmo commit. Os procedimentos e critérios de homologação ficam no plano de implantação.

[Plano de implantação](../../implantacao.md) · [Prova de infraestrutura e CI (#68)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)

## Leitura e manutenção

Data deste registro complementar: **2026-11-08**; não representa a data original de aprovação. Nenhuma ADR é substituída por este registro. O estado acima distingue implementação, proposta e decisão da R2; não constitui evidência de homologação.

Consulte o [índice de ADRs](index.md) para o mapa de decisões e o modelo de novos registros. As alternativas são comparações para revisão, não atas de uma avaliação histórica.
