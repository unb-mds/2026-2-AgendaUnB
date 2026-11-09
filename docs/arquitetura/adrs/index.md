---
title: "Decisões arquiteturais"
description: "Índice, estados e guia de leitura dos registros de decisão arquitetural do Agenda UnB."
---

# Decisões arquiteturais (ADRs)

Uma ADR registra uma decisão que afeta a estrutura, os dados ou as integrações do sistema, seu contexto e suas consequências. Comece pela tabela e leia a decisão relevante antes de alterar a área correspondente.

## Como interpretar os registros

- **Implementada:** solução registrada na documentação arquitetural existente; não implica aprovação formal nem testes executados nesta revisão.
- **Aceita para a Release 2:** decisão presente no escopo e nos contratos aprovados da R2; implementação e homologação precisam de evidências próprias.
- **Proposta:** opção ainda dependente de validação ou escolha da equipe.
- **Substituída:** decisão preservada para histórico, com link obrigatório para sua sucessora.

A data do registro não é a data da decisão. Referências DA preservam os identificadores da consolidação anterior. Alternativas comparativas não são apresentadas como opções historicamente avaliadas.

## Mapa de decisões

| ADR | Decisão | Estado | Rastreabilidade |
| --- | --- | --- | --- |
| [ADR-001](adr-001-integracao-fastapi-supabase.md) | Integração FastAPI e Supabase | Implementada | DA-02 |
| [ADR-002](adr-002-separar-hospedagem-e-ambientes.md) | Hospedagem e ambientes | Proposta | DA-07 |
| [ADR-003](adr-003-minimizar-dados-de-planos.md) | Minimização de dados de planos | Aceita para a Release 2 | RF06; RNF02 |
| [ADR-004](adr-004-api-monolitica.md) | Manter a API em uma aplicação FastAPI única | Implementada | DA-01; RNF13 |
| [ADR-005](adr-005-validacao-de-sessao.md) | Validar a sessão no Supabase Auth e consultar o papel no banco | Implementada | DA-03; RF01, RF03, RF04 |
| [ADR-006](adr-006-autorizacao-em-camadas.md) | Aplicar autorização na API, nas RPCs e nas políticas RLS | Implementada | DA-04; RF04, RF09, RF11; RNF02, RNF04 |
| [ADR-007](adr-007-migracoes-sql.md) | Usar migrações SQL como referência do esquema completo | Implementada | DA-05; RNF13 |
| [ADR-008](adr-008-vinculos-de-eventos-publicos.md) | Salvar vínculos aos eventos públicos na agenda pessoal | Implementada | DA-06; RF08, RF12, RF13, RF18 |
| [ADR-009](adr-009-catalogo-publico-de-turmas.md) | Integrar o catálogo público de turmas com identidade local e cache | Aceita para a Release 2 | RF05; RNF11 |
| [ADR-010](adr-010-versoes-e-confirmacao-de-planos.md) | Versionar planos e exigir confirmação individual para importar candidatos | Aceita para a Release 2 | RF06, RF07; RNF02, RNF04 |
| [ADR-011](adr-011-datas-civis-e-instantes.md) | Distinguir datas civis de instantes e usar fim exclusivo | Aceita para a Release 2 | RF06, RF08, RF17, RF21 |
| [ADR-012](adr-012-exportacao-google-idempotente.md) | Exportar por ação explícita para uma agenda Google secundária | Aceita para a Release 2 | RF21; RNF02 |
| [ADR-013](adr-013-lembretes-persistentes.md) | Persistir lembretes com agendamento idempotente e revalidação | Aceita para a Release 2 | RF13, RF17 |

## Roteiro para pessoas e agentes de IA

1. Identifique o estado da ADR e leia suas fontes. Consulte a [API atual](../../api-specs.md) para comportamento disponível e os [contratos da R2](../../atualizacoes.md#contratos-da-release-2) para o alvo planejado.
2. Preserve as regras de autorização, identidade, privacidade e idempotência descritas. Não use uma decisão planejada como prova de funcionalidade existente.
3. Ao encontrar divergência entre código e documentação, registre o fato e a evidência antes de mudar comportamento. Os testes citados são pontos de verificação, não resultados desta revisão.
4. Ao mudar uma decisão, crie a próxima ADR, relacione a anterior e atualize seu estado quando a substituição for aprovada. Não renumere o histórico nem invente datas, responsáveis ou alternativas avaliadas.
5. Atualize este índice, a visão de arquitetura e as navegações de MkDocs e Mintlify no mesmo PR.

## Modelo para uma nova ADR

Use um arquivo `adr-NNN-resumo-da-decisao.md`, com título e descrição no frontmatter. Mantenha uma decisão central por registro e texto curto em português; preserve nomes técnicos exatos.

```markdown
# ADR-NNN · Decisão em uma frase

| Campo | Valor |
| --- | --- |
| Estado | Proposta / Aceita para a Release 2 / Implementada / Substituída |
| Data do registro | AAAA-MM-DD |
| Rastreabilidade | IDs existentes de requisitos ou decisões; não inventar |
| Substitui | Nenhuma ADR ou link para a anterior |

## Contexto
Problema, restrições e evidências documentais.

## Decisão
Escolha, limites e regras que contribuições devem preservar.

## Alternativas para comparação
Opções e trade-offs. Informar se houve avaliação documentada ou apenas comparação.

## Consequências
Benefícios, custos, riscos, migração e pendências.

## Orientações para contribuição e verificação
Cenários a verificar, referências de código/testes e limites da evidência.

## Fontes e relações
Links para documentação, requisitos e ADRs relacionadas.
```

## Limites e decisões ainda abertas

A prova de infraestrutura ainda deve validar o provedor da API, execução de jobs e viabilidade do catálogo público. Estes registros não escolhem um scheduler nem aprovam a hospedagem proposta. O limite de entrada de texto bruto também permanece pendente no contrato da R2.

A documentação contém trechos históricos de planos ainda indisponíveis e uma visão mais recente com upload e confirmação. Consulte o inventário da API e o código antes de assumir disponibilidade. A ADR-011 explicita a transição do fuso do navegador para o contrato da R2.

[Visão arquitetural](../visao-geral.md) · [Padrões](../../produto/padroes.md) · [Matriz de aceite](../../matriz-release-2.md)
