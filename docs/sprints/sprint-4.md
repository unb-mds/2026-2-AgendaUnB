# Sprint 04 - Arquitetura, concepção do protótipo e entrega de MVP

**Período:** 21/09/2026 - 05/10/2026

**Objetivo:** Entregar uma primeira versão funcional do Agenda UnB, estabelecendo a base e o início da implementação.

Ao final da Sprint 04, é esperado que seja possível:
- Acessar a aplicação;
- Pesquisar/filtrar eventos;
- Visualizar os detalhes de um evento;
- Visualizar eventos da UnB criados manualmente.

Para tanto, definem-se as seguintes tarefas primárias, em ordem de relevância:
1. Definir e registrar a arquitetura do projeto;
2. Criar, estruturar e implementar o banco de dados;
3. Implementar API de eventos;
4. Desenvolver catálogo de eventos;
5. Modal de detalhes do evento;
6. Implementar autenticação no banco de dados;
7. Adicionar Skills e Specs ao repositório.

## Definition of Done

A Sprint 04 será considerada concluída quando existir uma versão integrada do Agenda UnB capaz de consultar eventos armazenados no banco de dados através da API, exibi-los no front-end, permitir busca/filtros e visualizar seus detalhes, com a arquitetura documentada e os principais fluxos testados. (Já está concluída).

## Issues da sprint

Consulta ao GitHub em **19/10/2026**. Estado e checklists abaixo reproduzem o registro das issues nessa consulta; uma issue fechada não representa verificação independente de todos os critérios. As atribuições históricas foram preservadas.

| Issue | Estado no GitHub | Responsáveis |
| --- | --- | --- |
| [#10 — Definir e registrar a arquitetura do projeto](https://github.com/unb-mds/2026-2-AgendaUnB/issues/10) | Fechada | @Thomas4ugust0, @marrathomaz, @pontesluis, @heitormontt, @Bielziin07, @felipecduque7 |
| [#11 — Adiconar Skills e Specs ao repositório](https://github.com/unb-mds/2026-2-AgendaUnB/issues/11) | Fechada | @marrathomaz, @heitormontt |
| [#12 — Criar estrutura do banco de dados](https://github.com/unb-mds/2026-2-AgendaUnB/issues/12) | Fechada | @pontesluis, @felipecduque7 |
| [#13 — Implementar API de eventos](https://github.com/unb-mds/2026-2-AgendaUnB/issues/13) | Fechada | @marrathomaz, @pontesluis, @heitormontt, @felipecduque7 |
| [#14 — Desenvolver catálogo de eventos](https://github.com/unb-mds/2026-2-AgendaUnB/issues/14) | Fechada | @Thomas4ugust0, @Bielziin07 |
| [#15 — Página/modal de detalhes do evento](https://github.com/unb-mds/2026-2-AgendaUnB/issues/15) | Fechada | @Thomas4ugust0, @Bielziin07 |
| [#16 — Autenticação no banco de dados](https://github.com/unb-mds/2026-2-AgendaUnB/issues/16) | Fechada | @pontesluis, @felipecduque7 |

## Texto das issues registradas

### #10 — Definir e registrar a arquitetura do projeto

**Origem:** [Issue #10](https://github.com/unb-mds/2026-2-AgendaUnB/issues/10).

**Estado:** Fechada.

**Labels:** 03. ALTA PRIORIDADE, Front-end, Back-end, Banco de dados.

**O documento de arquitetura precisa ser devidamente formulado para que o back-end, banco e hospedagem sejam oficialmente documentados.**

Tasks:

- [x] Definir tecnologia/framework do back-end.
- [x] Definir banco de dados.
- [x] Definir comunicação Front-end ↔ API.
- [x] Definir estrutura básica da API.
- [x] Definir estratégia de autenticação.
- [x] Registrar as decisões em docs/Architecture.md.

### #11 — Adiconar Skills e Specs ao repositório

**Origem:** [Issue #11](https://github.com/unb-mds/2026-2-AgendaUnB/issues/11).

**Estado:** Fechada.

**Labels:** 03. ALTA PRIORIDADE, Back-end.

**Estruturar no repositório os arquivos de contexto, regras e especificações que orientarão ferramentas de IA durante o desenvolvimento do Agenda UnB, garantindo que a IA siga a arquitetura, padrões e decisões do projeto.**

- [x] Criar a estrutura de diretórios para skills e specs.
- [x] Definir regras de código e padrões de desenvolvimento.
- [x] Criar especificações das principais funcionalidades.
- [x] Definir instruções para a IA respeitar requisitos funcionais e não funcionais do projeto.
- [x] Incluir orientações para testes e validação.
- [x] Documentar decisões arquiteturais relevantes para evitar que a IA proponha soluções incompatíveis com o projeto.

### #12 — Criar estrutura do banco de dados

**Origem:** [Issue #12](https://github.com/unb-mds/2026-2-AgendaUnB/issues/12).

**Estado:** Fechada.

**Labels:** 03. ALTA PRIORIDADE, Banco de dados.

**Criar inicialmente as entidades necessárias para o MVP:**

ex: User. Event, Category, Campus

Tasks:

 - [x] Criar tabela com as entidades que serão usadas no MVP
 - [x] Criar relacionamentos.
 - [x] Criar dados iniciais/mock para desenvolvimento.

### #13 — Implementar API de eventos

**Origem:** [Issue #13](https://github.com/unb-mds/2026-2-AgendaUnB/issues/13).

**Estado:** Fechada.

**Labels:** 02. MÉDIA PRIORIDADE, Back-end, Banco de dados.

**A primeira versão para a Release 1 precisa conseguir buscar eventos reais do banco, em vez de depender apenas de dados estáticos no front, além disso, os administradores (professores e comunidade acadêmica responsável) devem ser capazes de criar e deletar eventos, entquanto os discentes devem ser capazes de visualizá-los.**

Tasks:

 - [x] Criar endpoint de detalhes e listagem.
 - [x] Implementar filtros.
 - [x] Validar dados recebidos.
 - [x] Criar tratamento de erros.
 - [x] Conectar API ao banco e ao front-end.
 - [x] Testar endpoints.
 - [x] Implementar CRUD (RF09)

### #14 — Desenvolver catálogo de eventos

**Origem:** [Issue #14](https://github.com/unb-mds/2026-2-AgendaUnB/issues/14).

**Estado:** Fechada.

**Labels:** 02. MÉDIA PRIORIDADE, Front-end.

Desenvolver um catálogo de eventos na segunda página da aplicação que permita a visualização dos eventos, com as devidas informações por meio de filtragem por categoria, tais como: local, data de início e término, detalhamento do evento, entre outros.

 - [x] Criar página de eventos.
 - [x] Criar componente de card.
 - [x] Exibir data/horário.
 - [x] Exibir local/campus.
 - [x] Exibir categoria.
 - [x] Implementar busca.
 - [x] Implementar filtros.
 - [x] Criar estado de carregamento.

### #15 — Página/modal de detalhes do evento

**Origem:** [Issue #15](https://github.com/unb-mds/2026-2-AgendaUnB/issues/15).

**Estado:** Fechada.

**Labels:** 02. MÉDIA PRIORIDADE, Front-end.

**Conforme determina o RF14, o sistema deve forneçer os detalhes completos do evento, portanto, é necessário:**

Tasks:

- [x] Criar página/modal com os detalhes do evento ( descrição, link externo, data. horário, local, campus, categoria ).
- [x] Botão de redirecionamento ao link externo de onde o evento está sendo organizado.
- [x] Integração com o Google OAuth, mostrando a foto e nome de quem criou o evento.

### #16 — Autenticação no banco de dados

**Origem:** [Issue #16](https://github.com/unb-mds/2026-2-AgendaUnB/issues/16).

**Estado:** Fechada.

**Labels:** 02. MÉDIA PRIORIDADE, Banco de dados.

**O usuário deve ser capaz de entrar e se cadastrar na plataforma, de acordo com o  RF01 (e-mail institucional - PROFESSOR ou pessoal - ESTUDANTE.**

Tasks:

- [x] Implementar login.
- [x] Implementar cadastro
- [x] Implementar logout.
- [x] Implementar controle de acesso básico (erros comuns).
