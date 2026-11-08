---
title: "ADR-010 · Versionar planos e exigir confirmação individual para importar candidatos"
description: "Decisão, consequências e critérios de verificação: versionar planos e exigir confirmação individual para importar candidatos."
---

# ADR-010 · Versionar planos e exigir confirmação individual para importar candidatos

| Campo | Valor |
| --- | --- |
| Estado | Aceita para a Release 2 |
| Data do registro | 2026-11-08 |
| Rastreabilidade | RF06, RF07; RNF02, RNF04 |
| Substitui | Nenhuma ADR |

Registro de decisão já descrita nos contratos da R2; não comprova implementação ou homologação.

## Contexto

A extração pode produzir datas incertas. Uma versão compartilhada atende várias contas, cada uma com sua agenda e decisão de importação.

## Decisão

Iniciar versões privadas e compartilhar conteúdo revisado por decisão do autor. Professor/admin podem publicar diretamente suas revisões de conteúdo já compartilhado, sem aprovação adicional do autor original; essa permissão não alcança conteúdo privado alheio. Edições criam revisões separadas, preservando versões anteriores e cópias importadas. Seguidores autenticados votam por candidato e versão; votos não alteram datas. Confirmar candidatos em transação, com unicidade por (user_id, version_id, candidate_id), procedência e validação de acesso e datas.

Toda data extraída começa como candidata. Somente a confirmação explícita do usuário a transforma em avaliação efetiva na sua agenda; em versões compartilhadas, essa decisão pertence a cada conta. A revisão deve ser breve: mostrar candidatos em uma lista, permitir selecionar vários e confirmar o lote em uma única ação, destacar apenas campos ambíguos que exigem correção e preservar as escolhas durante ajustes. Não exigir uma sequência de confirmações por item nem importar automaticamente. Avaliar a fluidez na homologação com o tempo e as dificuldades observadas, sem inventar um limite numérico ainda não acordado.

Na R2, exigir `Idempotency-Key` por ação de confirmação, vinculada à conta, à operação e ao conteúdo do lote. Repetições da mesma ação usam a mesma chave; payload diferente com a mesma chave retorna 409. Persistir a operação e seus itens na mesma transação da confirmação e serializar requisições concorrentes. A exclusão do evento preserva o registro da importação e da operação: repetir a chave antiga não recria o evento nem reativa o vínculo. Reimportar exige o comando explícito “Adicionar novamente”, uma nova chave e nova verificação de acesso, versão e datas. Manter no máximo um evento ativo por `(user_id, version_id, candidate_id)`, mesmo com chaves diferentes; novas ações após exclusão não apagam o histórico das anteriores. O resultado de retry informa quando o evento anteriormente criado já foi removido. A transição dos clientes legados deve ser documentada antes de tornar a chave obrigatória; não inventar uma chave nova a cada retry.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Publicar todo envio exporia dados privados. Atualizar automaticamente agendas a partir de votos ou revisões eliminaria a confirmação pessoal e poderia modificar compromissos já aceitos.

## Consequências

Retirar compartilhamento bloqueia novos acessos, votos e importações, preservando avaliações já importadas. Professor/admin não obtêm acesso a conteúdo privado apenas pelo papel. author_role e evidência institucional são informações distintas. A unicidade legada apenas por candidato precisa migrar antes do compartilhamento.

Retirar o compartilhamento da versão original não retira nem exclui suas revisões: elas mantêm sua própria visibilidade e continuam disponíveis quando compartilhadas. Cópias já importadas na agenda também permanecem. Essa regra trata da retirada de compartilhamento, não define a política de exclusão de conta.

Uma revisão feita por professor ou admin mantém a procedência institucional já validada da versão de origem. Registrar a versão de origem, a evidência institucional herdada, o autor da revisão e seu papel no momento da alteração. A interface distingue documento institucional de origem e alterações posteriores da comunidade. Papel professor/admin não cria procedência institucional quando a origem não a possuía; revisões estudantis não recebem essa herança automaticamente.

## Orientações para contribuição e verificação

Verificar publicação de revisão por professor/admin sem aprovação adicional do autor original, proibição de publicar privados alheios, privacidade, retirada do compartilhamento, revisão sem alteração das cópias, repetição de importação e data ambígua. Retry antigo não deve restaurar evento apagado. A ADR-003 rege a autorização do texto enviado ao provedor.

## Fontes e relações

[Plano, versão e candidatos](../../atualizacoes.md#plano-versao-e-candidatos) · [ADR-003](adr-003-minimizar-dados-de-planos.md) · [Requisitos](../../produto/requisitos.md) · [Índice de ADRs](index.md)
