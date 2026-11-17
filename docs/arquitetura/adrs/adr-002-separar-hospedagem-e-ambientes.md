---
title: "ADR-002 · Hospedagem e isolamento de ambientes"
---

# ADR-002 · Separar a hospedagem da SPA, da API e dos jobs em orçamento zero

**Estado** Implementada (implantada em ambiente hospedado único nesta fase, com isolamento lógico de credenciais). Corresponde à DA-07.

## Contexto

A aplicação tem uma SPA React/Vite, uma API Python (FastAPI), jobs periódicos/assíncronos (worker de planos, coletor institucional de eventos e sincronização do catálogo) e serviços de banco, autenticação e armazenamento no Supabase. O projeto opera com orçamento zero (Free Tier) e precisa evitar sobrecarga ou timeouts no web service da API, proteger segredos no frontend e manter pipelines de CI reproduzíveis.

## Decisão

Hospedar cada camada no serviço gratuito mais adequado ao seu perfil de execução, mantendo separação estrita de segredos:

- **Frontend SPA (Vercel):** `vercel.json` e `frontend/vercel.json` publicam exclusivamente o bundle estático Vite (`framework: "vite"`), incluindo a função de busca (`frontend/api/search.js`). O build valida em `frontend/src/lib/deploymentConfig.js` que `VITE_API_URL` seja HTTPS terminado em `/api/v1` e impede que previews utilizem Auth, banco ou API de produção. `frontend/src/lib/supabaseConfig.js` bloqueia chaves `sb_secret_` ou JWT `service_role` em variáveis `VITE_*`.
- **API Web (Render Free Tier):** `render.yaml` define o Web Service com `runtime: docker` (`backend/Dockerfile`, `python:3.11-slim`), health check em `/health` e `CORS_ORIGINS` restrito às origens explícitas da SPA. Por operar em plano gratuito, a instância entra em repouso após inatividade e desperta na primeira requisição.
- **Jobs periódicos e pesados (GitHub Actions):** Como Background Workers do Render não possuem plano gratuito, a execução agendada e sob demanda do worker de planos (`worker`), coletor de eventos (`collector`) e sincronização de turmas (`catalog`) é executada em `.github/workflows/production-jobs.yml` (Python 3.11, ambiente `production-jobs`).
- **Supabase gerenciado e SMTP:** Banco PostgreSQL (conexão via Session Pooler com `sslmode=require`), Supabase Auth e Storage privado. E-mails transacionais de confirmação e recuperação usam templates próprios (`supabase/templates/confirmation.html`, `recovery.html`) e SMTP customizado no ambiente hospedado (Inbucket local em desenvolvimento). O backend valida a configuração SMTP em `backend/src/services/email.py` e `backend/src/deployment.py` com mascaramento estrito de `SMTP_PASS` (`repr=False` e omissão em logs/respostas). Clientes Storage que enviam cabeçalho `Bearer` utilizam a chave JWT legada `service_role` apenas no servidor.
- **CI reproduzível:** `.github/workflows/app-ci.yml` executa Vitest, build Vite, Playwright e Pytest (SQLite em memória); `.github/workflows/supabase-ci.yml` sobe instância descartável via Supabase CLI, aplica migrações em ordem, executa `supabase db lint --level error` e roda os testes PostgreSQL de RLS, RPCs e triggers.

## Alternativas para avaliação

Hospedar a SPA junto da API via Vercel Services acoplaria o runtime Python aos limites de tamanho e payload serverless (4,5 MB, abaixo dos 10 MiB de upload de planos). Rodar jobs em `BackgroundTasks` da API ou em Background Workers pagos violaria a resiliência a reinícios ou a restrição de orçamento zero. Manter projetos hospedados duplicados para homologação e produção nesta fase foi adiado por prazo e orçamento, mantendo a trava em `deploymentConfig.js` para quando previews separados forem habilitados.

## Consequências

A separação permite escalar e atualizar SPA, API e jobs independentemente sem expor segredos ao navegador. Exige manter `CORS_ORIGINS`, URLs de retorno do Supabase Auth, callbacks OAuth e variáveis `VITE_*` sincronizados entre os provedores, além de coordenar migrações de banco antes de publicar código dependente. O spin-down do plano gratuito da API gera latência inicial na primeira chamada após ociosidade.

[Plano de implantação](/implantacao) · [Modelos de deploy](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/deploy/README.md) · [ADR-007](/arquitetura/adrs/adr-007-migracoes-sql) · [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia)

## Leitura e manutenção

Data deste registro: **2026-11-15** (atualiza registro complementar de 2026-11-08 com as decisões consolidadas da S7-B02). Valores específicos de IDs de projeto, domínios publicados, credenciais ou backups operacionais não devem ser registrados nesta ADR.
