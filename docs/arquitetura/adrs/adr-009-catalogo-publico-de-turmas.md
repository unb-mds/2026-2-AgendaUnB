---
title: "ADR-009 · Integrar o catálogo público de turmas com identidade local e cache"
description: "Decisão, consequências e critérios de verificação: integrar o catálogo público de turmas com identidade local e cache."
---

# ADR-009 · Integrar o catálogo público de turmas com identidade local e cache

| Campo | Valor |
| --- | --- |
| Estado | Aceita para a Release 2 |
| Data do registro | 2026-11-08 |
| Rastreabilidade | RF05; RNF11 |
| Substitui | Nenhuma ADR |

Registro de decisão já descrita nos contratos da R2; não comprova implementação ou homologação.

## Contexto

A seleção de turma precisa identificar ofertas de semestres distintos e continuar utilizável quando a fonte externa falhar. A integração não comprova matrícula oficial.

## Decisão

Consultar o catálogo público Followw pelo backend, atribuir UUID local imutável à oferta e registrar vínculo autodeclarado único por (user_id, class_offering_id). Usar chave inequívoca da oferta ou a composição definida no contrato. Preservar zeros no número da turma; professor e horário são atributos atualizáveis. Em falha, servir o último catálogo válido com stale: true; sem cache, retornar 503.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Consultar a fonte a cada leitura acoplaria disponibilidade e latência. Usar apenas o código da disciplina confundiria ofertas. Integrar credenciais acadêmicas ampliaria o escopo e o acesso a dados privados.

## Consequências

Chaves incompletas ou colisões exigem revisão. Ofertas fora do catálogo disponível bloqueiam vínculo e envio de plano, mas a agenda existente continua disponível. Endpoints públicos, cobertura e paginação ainda dependem da prova de infraestrutura.

## Orientações para contribuição e verificação

Validar colisões, mudança de professor/horário, ofertas de semestres diferentes, cache desatualizado e ausência de cache. Não tratar vínculo autodeclarado como prova institucional.

## Fontes e relações

[Catálogo e vínculo](../../atualizacoes.md#catalogo-e-vinculo-com-a-turma) · [Matriz de aceite](../../matriz-release-2.md) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
