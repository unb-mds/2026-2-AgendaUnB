---
title: "ADR-007 · Usar migrações SQL como referência do esquema completo"
description: "Decisão, consequências e critérios de verificação: usar migrações sql como referência do esquema completo."
---

# ADR-007 · Usar migrações SQL como referência do esquema completo

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-05; RNF13 |
| Substitui | Nenhuma ADR |

Registro retrospectivo; a motivação histórica e as alternativas avaliadas na época não estão documentadas.

## Contexto

O banco contém tabelas, políticas RLS, funções e triggers que não são representados integralmente pelos modelos SQLAlchemy.

## Decisão

Versionar o esquema completo em `supabase/migrations/` e aplicar migrações em ordem antes do código que depende delas. O ORM mapeia as estruturas usadas pela API e não substitui as migrações.

Em ambientes persistentes (homologação ou produção), a aplicação de migrações deve seguir protocolo seguro:

1. **Backup lógico prévio:** extrair snapshot consistente com `pg_dump` (formato custom) cobrindo `public`, `auth`, `storage` e `supabase_migrations` (estrutura, dados, proprietários e privilégios) antes de alterar o banco, inspecionando com `pg_restore --list`.
2. **Ensaio isolado:** restaurar o snapshot em um banco local isolado (nunca sobre o banco compartilhado com `pg_restore --clean` ou `supabase db reset`), aplicar as migrações pendentes e executar os testes de RLS, RPCs, triggers e pré-requisitos do worker.
3. **Verificação de pré-condições e transação:** validar remoção de tabelas legadas somente após confirmar ausência de registros sob bloqueio contra escritas concorrentes; ensaiar o lote em transação com `ROLLBACK` antes da aplicação definitiva; executar em transação única (removendo eventuais `BEGIN/COMMIT` internos apenas no executor em lote, sem alterar os arquivos SQL versionados) seguida de `NOTIFY pgrst, 'reload schema'` e conferência do histórico de versões e integridade dos dados preservados.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Gerar o esquema apenas pelo ORM omitiria estruturas específicas do PostgreSQL. Alterações manuais sem migração dificultariam reproduzir ambientes.

## Consequências

Frontend, API e banco precisam coordenar sua implantação. Alterações exigem verificar políticas, funções e leitores antigos. Na R2, priorizar mudanças aditivas e preservar os nomes legados definidos no contrato.

## Orientações para contribuição e verificação

Validar migrações do zero e lint de esquema (`supabase db lint --level error`) em instância descartável via CI (`.github/workflows/supabase-ci.yml`), além dos testes de RLS/RPC em PostgreSQL local. A presença de um modelo ORM não comprova que uma migração foi aplicada, e renomeações fora de ordem exigem reconciliação explícita do histórico sem reset automático.

## Fontes e relações

[Persistência e migrações](/arquitetura/visao-geral#7-persistencia-privacidade-e-migracoes) · [Compatibilidade](/atualizacoes#compatibilidade-e-migracao) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
