---
title: "Agenda UnB"
description: "Documentação oficial do Agenda UnB, plataforma centralizada de eventos e organização acadêmica da Universidade de Brasília."
sidebarTitle: "Introdução"
---

Bem-vindo à documentação oficial do projeto **Agenda UnB**, desenvolvido pelo **Grupo G8** na disciplina de **Métodos de Desenvolvimento de Software (MDS)** da Universidade de Brasília (UnB) no semestre **2026/2**.

---

## Sobre o Projeto

O objetivo do **Agenda UnB** é criar uma plataforma centralizada para a comunidade acadêmica da UnB, reunindo em um único ambiente:

1. **Agenda do Campus:** Divulgação e acompanhamento de eventos sociais, acadêmicos e culturais de todos os campi da universidade (Darcy Ribeiro, FCTE/Gama, FCTS/Ceilândia, FUP e FAL).
2. **Organizador Acadêmico Inteligente.** Agenda pessoal em lista ou calendário com compromissos privados e eventos públicos salvos. A Release 2 inclui seleção de turmas pelo catálogo Followw e extração assistida de datas de planos.
3. **Sugestões e moderação.** Estudantes propõem eventos. Professores e admins moderam. Admins gerenciam papéis e categorias.

---

## Equipe G8

| Nome | Frente | GitHub |
| --- | --- | --- |
| Thomas Araujo | Frontend | [@thomas4ugust0](https://github.com/thomas4ugust0) |
| Heitor Monteiro | Backend | [@heitormontt](https://github.com/heitormontt) |
| Luis Davi | Banco de Dados | [@pontesluis](https://github.com/pontesluis) |
| Gabriel Escramin | Frontend | [@Bielziin07](https://github.com/Bielziin07) |
| Thomaz Marra | Backend | [@marrathomaz](https://github.com/marrathomaz) |
| Felipe Duque | Banco de Dados | [@felipecduque7](https://github.com/felipecduque7) |

---

## Mapa da Documentação

Use a navegação do site ou os links abaixo.

* [Execução local](/processo/execucao-local) — Instalação das dependências, configuração e inicialização da aplicação.
* [Visão do Produto](/produto/visao) — Problema, stakeholders, declaração de posicionamento e priorização.
* [Arquitetura](/arquitetura/visao-geral) — Visão arquitetural, tecnologias, frontend, backend e modelos de dados.
* [Decisões arquiteturais (ADRs)](/arquitetura/adrs/index) — Decisões, estados, consequências e orientações para contribuir.
* [Contratos do backend](/api-specs) — Rotas, payloads, respostas e integrações Supabase.
* [Plano de implantação](/implantacao) — Hospedagem, CI/CD e homologação.
* [Requisitos](/produto/requisitos) — Especificação completa de Requisitos Funcionais (RF) e Não Funcionais (RNF).
* [Padrões de Projeto](/produto/padroes) — Glossário e convenções de código e nomenclatura.
* [Sprints](/sprints/sprint-1) — Acompanhamento ágil das entregas por ciclo de desenvolvimento.
* [Como Contribuir](/processo/contribuindo) — Fluxo de trabalho, testes e convenções.


## Estado atual

A [v0.1.0](/processo/release-notes/v0-1-0) registra a entrega de 28/09/2026. Consulte [Atualizações pós-R1](/atualizacoes) para o estado documentado em 19/10/2026, incluindo calendário, eventos públicos salvos e administração.

* [Eventos salvos](/eventos-salvos) — Vínculos com a agenda pessoal, API e migração.
* [Integração FastAPI/Supabase e autorização](/arquitetura/adrs/adr-001-integracao-fastapi-supabase) — Permissões, moderação, notificações e RPCs administrativas ([ADR-006](/arquitetura/adrs/adr-006-autorizacao-em-camadas)).
* [Interface e design](/arquitetura/frontend) — Navegação e experiência de uso.
* [Hospedagem e ambientes](/arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes) — Infraestrutura gratuita, SMTP, CI reproduzível e isolamento ([ADR-007](/arquitetura/adrs/adr-007-migracoes-sql)).
* [Dados de eventos: datas e coleta](/arquitetura/dados-de-eventos) — Coleta periódica da Agenda UnB Notícias, atualização, deduplicação e procedência ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)).

A extração de planos de ensino oferece preparação local de PDF/texto, sanitização automática e autorização no envio ([ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos)), processamento assíncrono resiliente ([ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia)) e confirmação idempotente versionada ([ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos)); a execução externa do provedor permanece controlada por flags operacionais.


## Planejamento e histórico de issues

As páginas de [Sprint 01](/sprints/sprint-1), [Sprint 02](/sprints/sprint-2), [Sprint 03](/sprints/sprint-3), [Sprint 04](/sprints/sprint-4) e [Sprint 05](/sprints/sprint-5) registram as issues existentes, seus textos e estados consultados em 19/10/2026. A [Sprint 06](/sprints/sprint-6) registra o início da jornada de planos de ensino e as realocações de #38 e #40.

Consolidação técnica de 24/10/2026: [Arquitetura e decisões](/arquitetura/visao-geral), [contratos](/api-specs) e [implantação proposta](/implantacao), com referência no commit `e0ecf46` e histórico da tag `R1`.

## Release 2

Consulte as decisões da entrega, os contratos e os cenários de homologação nos [Contratos da Release 2](/atualizacoes#contratos-da-release-2) e [matriz de aceite](/matriz-release-2).

As [Sprint 7](/sprints/sprint-7) e [Sprint 8](/sprints/sprint-8) registram as decisões aprovadas, as issues publicadas, os responsáveis e os critérios de aceite para a entrega de 25/11/2026.

## Recursos externos

- [Repositório no GitHub](https://github.com/unb-mds/2026-2-AgendaUnB)
- [Figma](https://www.figma.com/board/RlZe9FgO3Bz3gPkxevs8UJ/AGENDA-UNB?node-id=1-217&amp;t=USKjIQh4OXxQVwsG-1)
- [Miro](https://miro.com/welcomeonboard/b0lMYXFqaEFMTnNpejdUOE1tLy8rOGNHdk5QVndFOUN0ZTFtc1kvWC9UUWdCbUJXVkpFU2JKRXhqUHpRZEYxekt6NUNFZXNzOXkxVDRxRmk0TjI1akdVY0Q5QW0vUENuMVpvYWRaZzdVNFdQUDB4eFNqVTdGOHAxd2lDUnhTUTBBS2NFMDFkcUNFSnM0d3FEN050ekl3PT0hdjE=?share_link_id=540201941184)
