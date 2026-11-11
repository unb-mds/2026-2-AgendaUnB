<!--
Uma issue = uma branch = um PR. Reutilize a branch e o PR nas entregas parciais.
Título sugerido: tipo(escopo): resumo da mudança (#número-da-issue).
Preencha os campos; quando não se aplicarem, explique brevemente.
O checklist da issue é a fonte de verdade do progresso; não o duplique aqui.
-->

## Status

status: `<incompleto>`

<!--
Use <completo> somente quando TODOS os checks da issue estiverem concluídos.
Ao concluir sua parte, marque na própria issue apenas os itens efetivamente
concluídos e validados. Atualize este PR com as entregas e os próximos passos.
Se algum item for reaberto, volte para <incompleto>.
Preserve as crases para exibir os sinais < >.
Mantenha o PR como Draft enquanto incompleto. Completo não substitui aprovação.
Este template não sincroniza checklists nem bloqueia merges automaticamente.
-->

## Issue relacionada

Relacionado à issue #NUMERO

**Branch:** `nome-da-branch`

<!-- Vincule uma única issue de escopo. Quando completo, substitua a linha
"Relacionado à issue #NUMERO" por "Fixes #NUMERO". -->

## Contexto e resultado

<!-- Explique o problema, a motivação e o comportamento antes/depois. -->

## O que foi feito

- **Entregas:** descreva as mudanças e os itens da issue atendidos.
- **Decisões técnicas:** explique escolhas relevantes e limitações, se houver.

## Tipo de alteração

- [ ] Correção de bug
- [ ] Nova funcionalidade
- [ ] Interface, layout ou acessibilidade
- [ ] Refatoração ou ajuste técnico
- [ ] Documentação
- [ ] Testes
- [ ] Infraestrutura, configuração ou dependências
- [ ] Banco de dados ou migração

## Como testar

1. **Preparação:** informe ambiente, permissões, dados e comandos necessários, incluindo a pasta de execução.
2. **Execução:** detalhe ações, telas ou rotas a testar.
3. **Resultado esperado:** descreva o comportamento observável e os casos de erro relevantes.

## Validações e evidências

<!-- Registre apenas verificações realmente executadas. Informe falhas, testes
ignorados ou não executados e seus motivos. -->

| Verificação / comando | Resultado observado | Evidência |
| --- | --- | --- |
| Preencher | Preencher | Log |

## Impactos e cuidados

<!-- Descreva impactos em APIs, compatibilidade, permissões/RLS, dados,
dependências e configuração. Para migrações ou implantação especial, informe
ordem de aplicação e como reverter ou mitigar a mudança. Não exponha segredos. -->

## Pendências e continuidade

<!-- Enquanto incompleto, liste itens abertos na issue, bloqueios, dependências
e próximos passos, com responsáveis quando definidos. Quando completo, registre
"Nenhuma; todos os checks da issue foram concluídos". -->

## Checklist para revisão

<!-- Este checklist verifica a entrega; o status depende do checklist da issue.
Para itens não aplicáveis, substitua a checkbox por "Não se aplica — justificativa". -->

- [ ] O PR e a branch atendem exclusivamente à issue vinculada.
- [ ] Atualizei os itens concluídos na issue e conferi o status deste PR.
- [ ] Descrevi as mudanças, as pendências e os passos de teste.
- [ ] Executei as verificações aplicáveis e registrei resultados e limitações.
- [ ] Atualizei a documentação afetada e registrei o uso relevante de IA em `docs/processo/uso-de-ia.md`.
- [ ] Documentei impactos e cuidados de implantação/reversão, quando aplicáveis.
- [ ] Revisei o diff, sem segredos nem alterações fora do escopo.
