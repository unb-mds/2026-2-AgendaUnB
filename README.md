<div align="center">

<img src="frontend/public/banner.png" width="100%" alt="Background Agenda UnB" />


# **AGENDA UNB**

**Plataforma centralizada de eventos e organização acadêmica da Universidade de Brasília**

Métodos de Desenvolvimento de Software - 2026/2 - Grupo G8

<br/>

[Documentação](https://unb-mds.github.io/2026-2-AgendaUnB/) · [Figma](https://www.figma.com/board/RlZe9FgO3Bz3gPkxevs8UJ/AGENDA-UNB?node-id=1-217&t=USKjIQh4OXxQVwsG-1) · [Miro](https://miro.com/welcomeonboard/b0lMYXFqaEFMTnNpejdUOE1tLy8rOGNHdk5QVndFOUN0ZTFtc1kvWC9UUWdCbUJXVkpFU2JKRXhqUHpRZEYxekt6NUNFZXNzOXkxVDRxRmk0TjI1akdVY0Q5QW0vUENuMVpvYWRaZzdVNFdQUDB4eFNqVTdGOHAxd2lDUnhTUTBBS2NFMDFkcUNFSnM0d3FEN050ekl3PT0hdjE=?share_link_id=540201941184)

</div>

---

## 📋 Sumário

- [Sobre o Projeto](#sobre-o-projeto)
- [Stack Tecnológica](#stack-tecnologica)
- [Como Executar](#como-executar)
    - [Pré-requisitos](#pre-requisitos)
    - [Execução Rápida via Makefile (Recomendado)](#execucao-rapida-via-makefile-recomendado)
    - [Execução Manual Passo a Passo](#execucao-manual-passo-a-passo)
        - [1. Configuração Inicial e .env](#1-configuracao-inicial-e-env)
        - [2. Banco de Dados (Supabase)](#2-banco-de-dados-supabase)
        - [3. Backend (FastAPI)](#3-backend-fastapi)
        - [4. Frontend (React)](#4-frontend-react)
        - [5. Documentação Local (MkDocs)](#5-documentacao-local-mkdocs)
        - [6. Testes Automatizados](#6-testes-automatizados)
- [Funcionalidades Atuais](#funcionalidades)
- [Equipe](#equipe)
- [Documentação Oficial](#documentacao)

---

<a id="sobre-o-projeto"></a>
## 🚀 Sobre o Projeto

A informação que organiza a rotina de um estudante da UnB está fragmentada: a grade está no SIGAA, as datas de prova estão em PDFs de planos de ensino e os eventos circulam por Instagram, cartazes e grupos de WhatsApp. Não existe um lugar único onde o estudante veja o que vai acontecer nas próximas semanas.

O **Agenda UnB** resolve esse problema reunindo dois eixos em uma única aplicação web:

- **Agenda do Campus** — Catálogo público de eventos acadêmicos, culturais e esportivos de todos os campi (Darcy Ribeiro, FCTE, FCTS, FUP e FAL), com filtros por área, campus e turno.
- **Organizador Acadêmico** — Agenda pessoal com compromissos privados e eventos públicos adicionados. A Release 2 prevê seleção de turmas no catálogo público Followw e extração de avaliações de planos com revisão humana. [Contratos da Release 2](docs/atualizacoes.md#contratos-da-release-2)

---

<a id="stack-tecnologica"></a>
## 🛠️ Stack Tecnológica

| Camada | Tecnologia | Finalidade |
|--------|-----------|------------|
| Frontend | React 19, Vite 6, React Router 7 | SPA responsiva com roteamento client-side |
| Backend | Python 3, FastAPI, SQLAlchemy 2, Pydantic 2 | API REST com validação automática |
| Banco de Dados | PostgreSQL (Supabase) | Dados relacionais com Row Level Security |
| Autenticação | Supabase Auth | Google OAuth, login com e-mail/senha, JWT |
| Migrações | Supabase Migrations (SQL) | Versionamento de migrações |
| Ambiente Local | Supabase CLI + Docker | PostgreSQL, Auth e Studio locais |
| Documentação | MkDocs Material | Site publicado no GitHub Pages |
| Tipografia | Orbitron + Inter (Google Fonts) | Display sci-fi + body legível |
| Iconografia | Material Symbols | Ícones consistentes em toda a UI |

---

<a id="como-executar"></a>
## ⚙️ Como Executar

<a id="pre-requisitos"></a>
### Pré-requisitos

Instale Git, Node.js, Python e Docker. Use GNU Make para executar o projeto com os comandos abaixo. As instruções por sistema estão no [guia de contribuição](docs/processo/contribuindo.md#setup-requisitos).

<a id="execucao-rapida-via-makefile-recomendado"></a>
### Execução rápida

Com o Docker em execução, rode na raiz do repositório:

```bash
make setup
make dev
```

Abra a [aplicação local](http://localhost:5173). Para encerrar, pressione `Ctrl+C` e execute `make stop` para parar os containers do Supabase.

<a id="execucao-manual-passo-a-passo"></a>
### Execução manual e testes

O [guia de contribuição](docs/processo/contribuindo.md) reúne as instruções de execução manual, a lista de comandos Make e as verificações do projeto.

| Etapa | Guia |
| --- | --- |
| <a id="1-configuracao-inicial-e-env"></a>Configuração inicial | [Variáveis de ambiente](docs/processo/contribuindo.md#setup-ambiente) |
| <a id="2-banco-de-dados-supabase"></a>Banco de dados | [Supabase local](docs/processo/contribuindo.md#setup-supabase) |
| <a id="3-backend-fastapi"></a>Backend | [FastAPI](docs/processo/contribuindo.md#setup-backend) |
| <a id="4-frontend-react"></a>Frontend | [React e Vite](docs/processo/contribuindo.md#setup-frontend) |
| <a id="5-documentacao-local-mkdocs"></a>Documentação | [MkDocs local](docs/processo/contribuindo.md#setup-mkdocs) |
| <a id="6-testes-automatizados"></a>Testes | [Verificações automatizadas](docs/processo/contribuindo.md#setup-verificacoes) |

---

<a id="funcionalidades"></a>

## Funcionalidades Atuais 
Funcionalidades atualizadas até o fim da Sprint 05 (18/10)

### Frontend

| Funcionalidade | Descrição |
|---------------|-----------|
| Landing Page | Hero section, funcionalidades, sobre e equipe |
| Cadastro | Modal com seletor Estudante/Professor, validação de @unb.br para professor |
| Login | Modal de login com e-mail/senha e Google OAuth |
| Página de Eventos | `/eventos`: catálogo público e Meus Eventos, busca e filtros por área/campus/turno |
| Calendário | Visualização mensal e semanal, navegação por período e botão Hoje, com os mesmos filtros da lista |
| Eventos Públicos Salvos | Adicionar/remover eventos públicos da agenda pessoal sem copiar ou alterar o original |
| Sugestões | Estudantes enviam propostas pelo formulário Criar Evento; professores e admins analisam em `/sugestoes` |
| Notificações | Sino para estudantes com confirmação de envio, aprovação e recusa com justificativa |
| Administração | `/admin`: busca e filtros de usuários, confirmação de e-mail, último acesso e alteração de cargos |
| Plano de Ensino | `/plano-de-ensino`: página informativa; backend tem upload/worker Gemini e políticas/revisão transacional S6-D02 validadas em PostgreSQL isolado; ativação depende de homologar o ambiente de destino |
| Criação de Eventos | Modal com DatePicker e TimePicker customizados, campos completos |
| Edição e Exclusão | CRUD completo para eventos pessoais |
| Detalhe do Evento | Página dedicada com descrição, organizador, badges e link externo |
| Tema Dark / Light | Alternância completa visual (temas claro e escuro) |
| NavBar | Glassmorphism, avatar do usuário, navegação contextual |

### Backend (API)

A API inclui catálogo público, CRUD privado, sugestões, eventos salvos, administração, upload/consulta de planos e saúde. Consulte os [contratos](docs/api-specs.md) e o [guia do worker Gemini](docs/processamento-planos.md). A extração salva candidatos para revisão, sem criar compromissos; permanece desativada por padrão até validar as políticas S6-D02.

### Banco de Dados

O esquema é versionado em migrações SQL. Além das tabelas da R1, inclui `eventos_salvos`, `notificacoes`, candidatos a avaliações, regras de moderação, RPCs administrativas e o bucket privado `syllabus_files` (PDF, até 10 MB). Upload, modelo de candidatos e fila do worker exigem as migrações #40/S6-D01/S6-B01; as políticas S6-D02 precisam ser validadas antes de usar dados reais.

Destaques de segurança:

- Perfil criado automaticamente no cadastro; e-mail imutável no perfil.
- Cadastro e autopromoção para professor exigem `@unb.br`; admins podem atribuir esse papel a contas de outro domínio.
- Eventos privados, vínculos salvos e notificações são restritos ao próprio usuário.
- Sugestões estudantis nascem pendentes; decisões de moderação são atômicas e recusas exigem justificativa.
- Somente admins alteram cargos de terceiros; não podem remover o próprio acesso administrativo.

Antes de disponibilizar API e frontend atualizados, aplique as migrações pendentes. No ambiente local já inicializado, execute `npx supabase migration up --local`. Consulte os guias de [eventos salvos](docs/eventos-salvos.md) e [moderação](docs/painel-administrativo.md).

---

<a id="equipe"></a>
## 👥 Equipe

| Nome | Papel | GitHub |
|------|:-----:|--------|
| Thomas Augusto Amorim de Araujo | Frontend | [@thomas4ugust0](https://github.com/thomas4ugust0) |
| Gabriel Escramin Lourenço | Frontend | [@Bielziin07](https://github.com/Bielziin07) |
| Heitor Gomes Monteiro | Backend | [@heitormontt](https://github.com/heitormontt) |
| Thomaz Marra Martins | Backend | [@marrathomaz](https://github.com/marrathomaz) |
| Felipe Couto Duque | Banco de Dados | [@felipecduque7](https://github.com/felipecduque7) |
| Luis Davi Pontes da Silva | Banco de Dados | [@pontesluis](https://github.com/pontesluis) |

---

<a id="documentacao"></a>
## 📚 Documentação

Toda a documentação do projeto está publicada no GitHub Pages:

**[unb-mds.github.io/2026-2-AgendaUnB](https://unb-mds.github.io/2026-2-AgendaUnB/)**

| Documento | Descrição |
|-----------|-----------|
| [Arquitetura](https://unb-mds.github.io/2026-2-AgendaUnB/arquitetura/visao-geral/) | Visão arquitetural, stack e modelos de dados |
| [Requisitos](https://unb-mds.github.io/2026-2-AgendaUnB/produto/requisitos/) | 21 RFs e 13 RNFs especificados |
| [Padrões](https://unb-mds.github.io/2026-2-AgendaUnB/produto/padroes/) | Glossário, naming conventions e rotas da API |
| [Contratos do backend](docs/api-specs.md) | API atual e operações originadas na R1 |
| [Plano de implantação](docs/implantacao.md) | Proposta de hospedagem, CI/CD e homologação; ainda não implantada |
| [Atualizações pós-R1](docs/atualizacoes.md) | Calendário, eventos salvos, sugestões, moderação e administração |
| [Release v0.1.0](https://unb-mds.github.io/2026-2-AgendaUnB/processo/release-notes/v0-1-0/) | Release note da primeira entrega |
| [Sprints](https://unb-mds.github.io/2026-2-AgendaUnB/sprints/sprint-1/) | Acompanhamento ágil por ciclo |

---
