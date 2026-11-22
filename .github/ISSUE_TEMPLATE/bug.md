---
name: Relato de Bug
about: Reportar uma falha funcional, erro de interface, regressão ou inconsistência de contrato
title: "fix(escopo): resumo do problema observado"
labels: ["bug"]
assignees: []
---

<!--
Para falhas de segurança ou exposição de dados, NÃO abra uma issue pública — consulte SECURITY.md.
-->

## Objetivo

<!-- Resuma o defeito observado e qual fluxo do sistema está sendo impactado. -->

- **Frente:** <!-- Front-end / Back-end / Banco de dados / Documentação -->
- **Ambiente:** <!-- Local / Preview / Produção (agendaunb.com.br) -->
- **Requisitos afetados:** <!-- Ex.: RF08, RNF08 (se aplicável) -->

## Contexto e reprodução

1. **Passos para reproduzir:**
   - Acesse `...`
   - Execute `...`
2. **Comportamento observado:**
   - Descreva o erro, status HTTP, mensagem de log ou falha visual.
3. **Comportamento esperado:**
   - Descreva o resultado correto segundo os requisitos e contratos do projeto.

## Tasks

- [ ] Reproduzir e isolar a causa raiz da falha.
- [ ] Implementar a correção sem quebrar contratos ou fluxos adjacentes.
- [ ] Adicionar teste automatizado de regressão cobrindo o cenário corrigido.

## Critérios de aceite

- [ ] O cenário reproduzido passa a funcionar conforme o comportamento esperado.
- [ ] Os testes existentes e o novo teste de regressão passam sem erros.

## Evidências para fechamento

- [ ] Anexar à issue o PR com a correção e a saída dos testes/verificações executadas.
- [ ] Confirmar a revisão técnica da alteração.
