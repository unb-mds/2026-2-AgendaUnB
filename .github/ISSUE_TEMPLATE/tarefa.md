---
name: Tarefa ou Funcionalidade
about: Planejar e acompanhar uma entrega de funcionalidade, refatoração, banco de dados ou documentação
title: "tipo(escopo): resumo da entrega"
labels: []
assignees: []
---

<!--
Uma issue = uma branch = um PR.
O checklist em "Tasks" é a fonte de verdade do progresso para o Pull Request vinculado.
-->

## Objetivo

<!-- Descreva de forma clara e direta o objetivo da entrega e o resultado esperado no produto ou na arquitetura. -->

- **Frente:** <!-- Front-end / Back-end / Banco de dados / Documentação / Infraestrutura -->
- **Dependências:** <!-- Liste issues ou módulos relacionados, ou "Nenhuma" -->
- **Requisitos:** <!-- Ex.: RF05, RF06, RNF02 (ou "Não se aplica") -->

## Tasks

- [ ] Definir ou alinhar contratos, rotas, esquema ou componentes afetados.
- [ ] Implementar a alteração respeitando os padrões e regras de negócio do projeto.
- [ ] Adicionar ou atualizar testes automatizados cobrindo o fluxo principal e casos de erro.
- [ ] Atualizar a documentação técnica ou de produto correspondente, quando aplicável.

## Critérios de aceite

- [ ] O comportamento implementado atende aos requisitos e contratos especificados sem regressões nos fluxos existentes.
- [ ] As validações de segurança, permissões (API/RLS) e privacidade aplicáveis foram verificadas.
- [ ] Os testes automatizados e o build das frentes alteradas executam sem falhas.

## Observações

<!-- Registre restrições técnicas, decisões de escopo, cuidados de migração/implantação ou limites conhecidos. -->

## Evidências para fechamento

- [ ] Anexar à issue o PR vinculado e o resultado das verificações executadas para os critérios de aceite.
- [ ] Confirmar a revisão técnica dos contratos, permissões e dados afetados pela entrega.
