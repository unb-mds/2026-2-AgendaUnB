---
title: "Decisões arquiteturais"
description: "Índice, estados e guia de leitura dos registros de decisão arquitetural do Agenda UnB."
---

# Decisões arquiteturais (ADRs)

Uma ADR registra uma decisão que afeta a estrutura, os dados ou as integrações do sistema, seu contexto e suas consequências. Consulte o mapa abaixo e leia a decisão relevante antes de alterar a área correspondente.

## Como interpretar os registros

- **Implementada:** decisão adotada na arquitetura do sistema e refletida no código, nas migrações e nos contratos vigentes.
- **Aceita:** decisão aprovada no escopo arquitetural, pendente de implementação completa.
- **Proposta:** opção ainda dependente de validação ou escolha técnica.
- **Substituída:** decisão preservada para histórico, com link obrigatório para sua sucessora.

A data do registro não representa necessariamente a data original de formulação da decisão. Os identificadores `DA-01` a `DA-07` preservam a rastreabilidade com os registros arquiteturais iniciais.

## Mapa de decisões

| ADR | Decisão | Estado | Rastreabilidade |
| --- | --- | --- | --- |
| [ADR-001](/arquitetura/adrs/adr-001-integracao-fastapi-supabase) | Integração FastAPI e Supabase | Implementada | DA-02 |
| [ADR-002](/arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes) | Hospedagem e ambientes em orçamento zero | Implementada | DA-07; RNF03, RNF13 |
| [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos) | Minimização de dados de planos | Implementada | RF06; RNF02 |
| [ADR-004](/arquitetura/adrs/adr-004-api-monolitica) | Manter a API em uma aplicação FastAPI única | Implementada | DA-01; RNF13 |
| [ADR-005](/arquitetura/adrs/adr-005-validacao-de-sessao) | Validar a sessão no Supabase Auth e consultar o papel no banco | Implementada | DA-03; RF01, RF03, RF04 |
| [ADR-006](/arquitetura/adrs/adr-006-autorizacao-em-camadas) | Aplicar autorização na API, nas RPCs e nas políticas RLS | Implementada | DA-04; RF04, RF09, RF11; RNF02, RNF04 |
| [ADR-007](/arquitetura/adrs/adr-007-migracoes-sql) | Usar migrações SQL como referência do esquema completo | Implementada | DA-05; RNF13 |
| [ADR-008](/arquitetura/adrs/adr-008-vinculos-de-eventos-publicos) | Salvar vínculos aos eventos públicos na agenda pessoal | Implementada | DA-06; RF08, RF12, RF13 |
| [ADR-009](/arquitetura/adrs/adr-009-catalogo-publico-de-turmas) | Integrar o catálogo público de turmas com identidade local e cache | Implementada | RF05; RNF11 |
| [ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos) | Versionar planos e exigir confirmação individual para importar candidatos | Implementada | RF06, RF07; RNF02, RNF04 |
| [ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes) | Distinguir datas civis de instantes e usar fim exclusivo | Implementada | RF06, RF08, RF17, RF18 |
| [ADR-012](/arquitetura/adrs/adr-012-exportacao-google-idempotente) | Exportar por ação explícita para uma agenda Google secundária | Implementada | RF18; RNF02 |
| [ADR-013](/arquitetura/adrs/adr-013-lembretes-persistentes) | Persistir lembretes com agendamento idempotente e revalidação | Implementada | RF13, RF17 |
| [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia) | Processamento assíncrono resiliente de planos com fila persistida, lease e orçamento | Implementada | RF06; RNF02, RNF06, RNF10, RNF13 |

## Roteiro para manutenção

1. Identifique a ADR relacionada e consulte a [referência da API](/api-specs) e a [visão arquitetural](/arquitetura/visao-geral).
2. Preserve as regras de autorização, identidade, privacidade e idempotência descritas nas decisões vigentes.
3. Ao encontrar divergência entre código e documentação, registre e alinhe o contrato antes de alterar o comportamento público.
4. Ao substituir uma decisão, crie a próxima ADR, relacione a anterior e atualize seu estado para `Substituída`, sem renumerar o histórico.
5. Atualize este índice, a visão de arquitetura e a navegação em `docs/docs.json` no mesmo ciclo de alteração.

## Modelo para uma nova ADR

Use um arquivo `adr-NNN-resumo-da-decisao.md`, com título e descrição no frontmatter. Mantenha uma decisão central por registro e texto conciso em português, preservando nomes técnicos exatos.

```markdown
# ADR-NNN · Decisão em uma frase

| Campo | Valor |
| --- | --- |
| Estado | Proposta / Aceita / Implementada / Substituída |
| Data do registro | AAAA-MM-DD |
| Rastreabilidade | IDs existentes de requisitos ou decisões |
| Substitui | Nenhuma ADR ou link para a anterior |

## Contexto
Problema, restrições e evidências técnicas.

## Decisão
Escolha, limites e regras que o sistema deve preservar.

## Alternativas para comparação
Opções avaliadas e trade-offs relevantes.

## Consequências
Benefícios, custos, riscos, migração e impactos operacionais.

## Orientações para contribuição e verificação
Cenários a verificar e referências de código e testes.

## Fontes e relações
Links para documentação, requisitos e ADRs relacionadas.
```

[Visão arquitetural](/arquitetura/visao-geral) · [Padrões](/produto/padroes) · [Matriz de rastreabilidade](/matriz-rastreabilidade)
