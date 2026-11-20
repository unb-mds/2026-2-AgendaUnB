---
title: "ADR-010 · Versionar planos e exigir confirmação individual para importar candidatos"
description: "Decisão, consequências e critérios de verificação: versionar planos e exigir confirmação individual para importar candidatos."
---

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-15 |
| Rastreabilidade | RF06, RF07; RNF02, RNF04 |
| Substitui | Nenhuma ADR |

Decisão implementada nas migrações `20261109120000`, `20261110120000` e `20261111141000`, em `backend/src/modules/syllabus/` e na jornada `/plano-de-ensino` (`frontend/src/pages/TeachingPlanPage.jsx`).

## Contexto

A extração pode produzir datas incertas. Uma versão compartilhada atende várias contas, cada uma com sua agenda e decisão de importação, enquanto o acompanhamento pela interface precisa refletir estados persistidos sem criar compromissos automáticos.

## Decisão

1. **Versionamento, tabela oficial e controle de leitura:**
   - Candidatos extraídos e revisados são gravados na tabela oficial `avaliacoes` com `versao_id` e `ordem` (`AssessmentCandidate` é apenas alias ORM de compatibilidade), preservando `data_sugerida`/`hora_sugerida` civis sem inferir `data_avaliacao` (`suggestedDate`, `suggestedTime`, `ambiguousFields`, `versionId`).
   - **Atualização de produto (PO, 2026-11-17):** versões iniciais (`v1`) de planos vinculados a uma oferta (`offering_id`) concluídos com candidatos extraídos passam a ser compartilhadas automaticamente (`compartilhada`) ao serem consultadas ou confirmadas pelo autor (`GET /api/v1/syllabus/{id}` e `POST /api/v1/syllabus/{id}/confirm`), disponibilizando apenas os candidatos extraídos aos seguidores autenticados da turma — o PDF original permanece descartado e o texto bruto/metadados seguem restritos ao autor. Caso `v1` seja retirada pelo autor ou admin (`retirada_em`), ela volta a `privada` e não é recompartilhada automaticamente, exigindo ação voluntária (`PUT .../sharing`) se o autor desejar republicá-la. Versões posteriores (reprocessamentos `v2+` e rascunhos de revisão) iniciam `privada` até publicação explícita (`PUT .../sharing` ou `share: true`).
   - A função `ator_pode_ler_versao` (e a RLS via `pode_ler_versao`) garante leitura apenas ao autor da versão ou a seguidores da oferta quando `visibilidade = 'compartilhada'`; o papel `professor`/`admin` nunca libera acesso a rascunhos privados alheios.
   - Autor, seguidores autenticados da oferta, professor e admin podem revisar versões compartilhadas (`POST /api/v1/syllabus/{id}/versions`, mantendo rastreabilidade de versão de origem, autor e papel; herança de procedência institucional ocorre apenas quando a revisão é feita por professor/admin sobre versão que já a possuía). Versões compartilhadas não permitem editar títulos ou datas no lugar: correções geram nova versão revisada, enquanto autor ou admin podem retirar a versão (`DELETE .../sharing`) ou retirar logicamente um candidato da versão (`DELETE .../candidates/{cid}` marcando `status = 'descartado'`), preservando revisões derivadas e cópias já importadas na agenda pessoal.
2. **Revisão e confirmação idempotente em transação:**
   - Toda data extraída começa como candidata e só vira evento pessoal (`eventos_pessoais`, categoria `Acadêmico`, fuso padrão `-03:00` quando confirmado) mediante ação explícita em lote via `POST /api/v1/syllabus/{id}/confirm` (até 100 itens).
   - A confirmação exige `Idempotency-Key` persistida em `operacoes_importacao` e `itens_importacao` na mesma transação dos eventos. Repetir a mesma chave com o mesmo conteúdo retorna o resultado anterior sem recriar eventos apagados pelo usuário; reusar a chave com conteúdo diferente retorna `409` (`AG409`); mantém-se no máximo um evento ativo por `(user_id, versao_id, avaliacao_id)`; reimportar após exclusão exige nova chave. A RPC legada `revisar_candidatos_plano` permanece restrita ao dono para compatibilidade.
3. **Jornada de acompanhamento na interface (`/plano-de-ensino`):**
   - Visitantes recebem apenas orientação e convite para autenticação, sem envio de planos nem vínculo de turmas; usuários autenticados consultam oferta seguida (`GET /class-offerings/{id}`, `GET /me/class-offerings`), biblioteca compartilhada (`GET /class-offerings/{id}/shared-plans`), histórico (`GET /syllabus?limit=10&offset=0`) e detalhe (`GET /syllabus/{id}`).
   - Os estados de plano são `pendente`, `processando`, `concluido` e `falha`, com `authorizationRequired` e `preparedTextAvailable` distinguindo espera por autorização humana da fila pronta. O polling de progresso não se sobrepõe (5s para detalhe e 15s para histórico, espaçamento até 30s), pausa em abas ocultas ou erro e encerra em estado final. A seleção em lote valida títulos (3–200 caracteres), tipo (`Prova`/`Trabalho`) e datas antes do envio, preservando escolhas durante ajustes.
   - Em **Revisar datas**, uma prova pendente com data definida e sem horário no plano recebe no rascunho local uma sugestão de início da aula a partir do campo `schedule` da oferta vinculada (`GET /class-offerings/{id}`), interpretado conforme a [grade de horários do SIGAA na UnB](https://design.unb.br/codigos-aulas-sigaa/) para o dia da semana da prova (por exemplo, `24T23` sugere `14:00` numa segunda ou quarta). O campo indica a origem da sugestão e permanece editável; alterar a data recalcula a sugestão, enquanto horários vindos do plano ou editados pelo estudante são preservados. Sem aula no dia, com mais de um bloco no dia ou com código não interpretável, o preenchimento é manual.

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

[Plano, versão e candidatos](/atualizacoes#plano-versao-e-candidatos) · [Dados de planos](/arquitetura/dados-de-planos) · [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos) · [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
