---
title: "ADR-009 · Integrar o catálogo público de turmas com identidade local e cache"
description: "Decisão de sincronizar o catálogo público Followw localmente com identidade imutável e fallback em cache."
---

# ADR-009 · Integrar o catálogo público de turmas com identidade local e cache

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-15 |
| Rastreabilidade | RF05; RNF11 |
| Substitui | Nenhuma ADR |

## Contexto

A seleção de turmas no fluxo de planos de ensino precisa identificar ofertas de semestres distintos de forma estável e permanecer utilizável mesmo quando a fonte externa estiver indisponível. Além disso, o vínculo da conta com uma oferta é autodeclarado e não constitui comprovação de matrícula oficial.

## Decisão

Sincronizar o catálogo público do Followw pelo backend (`GET /public/classrooms/units`, `GET /public/subjects`, `GET /public/classrooms` em `https://followw.app/api`), atribuir UUID local imutável à disciplina e à oferta e registrar vínculo autodeclarado único por `(user_id, oferta_id)` em `vinculos_turma`. A sincronização preserva zeros à esquerda no número da turma e trata professor e horário como atributos atualizáveis fora da identidade.

O adaptador respeita espaçamento mínimo de 1 segundo entre chamadas, tratamento de HTTP 429 com `Retry-After` até 60 segundos e publicação atômica em `sincronizacoes_catalogo`, `disciplinas` e `ofertas_turma`. Em falha da origem, a API serve o último catálogo válido com `stale: true`; sem publicação válida disponível, retorna `503`.

Novos envios de planos de ensino exigem oferta disponível e seguida pela conta (`GET /api/v1/class-offerings/{id}` e `GET /api/v1/me/class-offerings`): ausência de vínculo retorna `403`, oferta retirada retorna `409` e ausência de catálogo publicado retorna `503`. Deixar de seguir uma oferta preserva o histórico particular e os compromissos já importados.

## Alternativas para comparação

Consultar a fonte externa a cada requisição do usuário acoplaria latência e disponibilidade da aplicação ao serviço externo. Usar apenas o código da disciplina confundiria ofertas e semestres distintos. Integrar credenciais acadêmicas ampliaria o escopo e o acesso a dados pessoais sem necessidade.

## Consequências

Identidades conflitantes ou incompletas exigem revisão nos metadados da sincronização antes da publicação. Ofertas ausentes em publicações futuras saem da busca (`available: false`), preservando planos e eventos já vinculados. A sincronização completa do catálogo executa de forma desacoplada da API via CLI ou workflow em `.github/workflows/production-jobs.yml`.

## Orientações para contribuição e verificação

Validar colisões de identidade, atualização de professor e horário, ofertas de semestres diferentes, comportamento com cache desatualizado (`stale: true`), ausência de cache (`503`) e bloqueio de envio sem vínculo (`403`).

## Fontes e relações

[Catálogo de turmas](/arquitetura/catalogo-de-turmas) · [Contratos da API](/api-specs) · [Matriz de rastreabilidade](/matriz-rastreabilidade) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
