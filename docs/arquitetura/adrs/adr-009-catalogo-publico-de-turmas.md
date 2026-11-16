---
title: "ADR-009 · Integrar o catálogo público de turmas com identidade local e cache"
description: "Decisão, consequências e critérios de verificação: integrar o catálogo público de turmas com identidade local e cache."
---

# ADR-009 · Integrar o catálogo público de turmas com identidade local e cache

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-15 |
| Rastreabilidade | RF05; RNF11 |
| Substitui | Nenhuma ADR |

Decisão implementada em `backend/src/modules/classes/` e nas migrações `20261109120000`, `20261110142000` e `20261111120000`.

## Contexto

A seleção de turma precisa identificar ofertas de semestres distintos e continuar utilizável quando a fonte externa falhar. A integração não comprova matrícula oficial.

## Decisão

Consultar o catálogo público Followw pelo backend (`GET /public/classrooms/units`, `GET /public/subjects`, `GET /public/classrooms`), atribuir UUID local imutável à oferta e registrar vínculo autodeclarado único por `(user_id, oferta_id)`. Preservar zeros no número da turma; professor e horário são atributos atualizáveis. Respeitar o limite observado da origem (600 requisições/minuto por IP, tratamento de HTTP 429 com `Retry-After`), espaçamento mínimo entre chamadas e paginação no cliente, persistindo o snapshot localmente em `sincronizacoes_catalogo` e `ofertas_turma`. Em falha da origem, servir o último catálogo válido; sem publicação válida disponível, retornar `503`.

Novos envios de planos de ensino exigem oferta disponível e seguida pela conta (`GET /class-offerings/{id}` e `GET /me/class-offerings`): ausência de vínculo retorna `403`, oferta retirada retorna `409` e ausência de catálogo publicado retorna `503`. Deixar de seguir uma oferta preserva o histórico particular e os compromissos já importados.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Consultar a fonte a cada leitura acoplaria disponibilidade e latência. Usar apenas o código da disciplina confundiria ofertas. Integrar credenciais acadêmicas ampliaria o escopo e o acesso a dados privados.

## Consequências

Chaves incompletas ou colisões exigem revisão. Ofertas fora do catálogo disponível bloqueiam vínculo e novo envio de plano, mas a agenda e o histórico existentes continuam disponíveis. A sincronização completa do catálogo roda de forma desacoplada via job em `.github/workflows/production-jobs.yml`.

## Orientações para contribuição e verificação

Validar colisões, mudança de professor/horário, ofertas de semestres diferentes, cache desatualizado, ausência de cache (`503`) e bloqueio sem vínculo (`403`). Não tratar vínculo autodeclarado como prova institucional.

## Fontes e relações

[Catálogo de turmas](/arquitetura/catalogo-de-turmas) · [Catálogo e vínculo](/atualizacoes#catalogo-e-vinculo-com-a-turma) · [Matriz de aceite](/matriz-release-2) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
