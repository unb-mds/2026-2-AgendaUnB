---
title: "Agenda UnB"
description: "Documentação oficial do Agenda UnB, plataforma centralizada de eventos e organização acadêmica da Universidade de Brasília."
sidebarTitle: "Introdução"
---

Bem-vindo à documentação oficial do projeto **Agenda UnB**, desenvolvido pelo **Grupo G8** na disciplina de **Métodos de Desenvolvimento de Software (MDS)** da Universidade de Brasília (UnB) no semestre **2026/2**.

---

## Sobre o Projeto

O objetivo do **Agenda UnB** é criar uma plataforma centralizada para a comunidade acadêmica da UnB, reunindo em um único ambiente:

1. **Agenda do Campus:** Divulgação e acompanhamento de eventos sociais, acadêmicos e culturais de todos os campi da universidade (Darcy Ribeiro (Plano Piloto), FCTE (Gama), FCTS (Ceilândia), FUP (Planaltina) e FAL).
2. **Organizador Acadêmico Inteligente:** Agenda pessoal em lista ou calendário com compromissos privados, eventos públicos salvos, seleção de turmas pelo catálogo Followw e extração assistida de datas de planos de ensino.
3. **Sugestões e moderação:** Estudantes propõem eventos. Professores e administradores moderam sugestões, e administradores gerenciam papéis e categorias.

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
* [Matriz de Rastreabilidade](/matriz-rastreabilidade) — Relação entre requisitos, módulos/contratos e critérios de verificação.
* [Padrões de Projeto](/produto/padroes) — Glossário e convenções de código e nomenclatura.
* [Sprints](/sprints/sprint-1) — Registro das entregas por ciclo de desenvolvimento.
* [Notas de versão](/processo/release-notes/v0-2-0) — Histórico das versões publicadas do projeto.
* [Como Contribuir](/processo/contribuindo) — Fluxo de trabalho, testes e convenções.

---

## Principais fluxos documentados

* [Eventos salvos](/eventos-salvos) — Vínculos com a agenda pessoal, API e migração.
* [Integração FastAPI/Supabase e autorização](/arquitetura/adrs/adr-001-integracao-fastapi-supabase) — Permissões, moderação, notificações e RPCs administrativas ([ADR-006](/arquitetura/adrs/adr-006-autorizacao-em-camadas)).
* [Interface e design](/arquitetura/frontend) — Navegação e experiência de uso.
* [Hospedagem e ambientes](/arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes) — Infraestrutura gratuita, SMTP, CI reproduzível e isolamento ([ADR-007](/arquitetura/adrs/adr-007-migracoes-sql)).
* [Dados de eventos: datas e coleta](/arquitetura/dados-de-eventos) — Coleta periódica da Agenda UnB Notícias, atualização, deduplicação e procedência ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)).
* **Planos de ensino:** Preparação local de PDF ou texto, sanitização automática e autorização explícita no envio ([ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos)), processamento assíncrono resiliente ([ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia)) e confirmação idempotente versionada ([ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos)).

## Recursos externos

- [Repositório no GitHub](https://github.com/unb-mds/2026-2-AgendaUnB)
- [Figma](https://www.figma.com/board/RlZe9FgO3Bz3gPkxevs8UJ/AGENDA-UNB?node-id=1-217)
- [Miro](https://miro.com/app/board/uXjVHtiWi4U=/)
