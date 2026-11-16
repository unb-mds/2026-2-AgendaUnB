<div align="center">

<img src="frontend/public/banner.png" width="100%" alt="Background Agenda UnB" />


# **AGENDA UNB**

**Plataforma centralizada de eventos e organização acadêmica da Universidade de Brasília**

Métodos de Desenvolvimento de Software - 2026/2 - Grupo G8

<br/>

[Acesse o Agenda UnB](https://agendaunb.com.br/) · [Documentação](https://agendaunb.com.br/docs) · [Figma](https://www.figma.com/board/RlZe9FgO3Bz3gPkxevs8UJ/AGENDA-UNB?node-id=1-217&t=USKjIQh4OXxQVwsG-1) · [Miro](https://miro.com/welcomeonboard/b0lMYXFqaEFMTnNpejdUOE1tLy8rOGNHdk5QVndFOUN0ZTFtc1kvWC9UUWdCbUJXVkpFU2JKRXhqUHpRZEYxekt6NUNFZXNzOXkxVDRxRmk0TjI1akdVY0Q5QW0vUENuMVpvYWRaZzdVNFdQUDB4eFNqVTdGOHAxd2lDUnhTUTBBS2NFMDFkcUNFSnM0d3FEN050ekl3PT0hdjE=?share_link_id=540201941184)

</div>

---

## Sumário

- [Sobre o Projeto](#sobre-o-projeto)
- [Stack Tecnológica](#stack-tecnologica)
- [Como Executar](#como-executar)
    - [Execução rápida](#execucao-rapida-via-makefile-recomendado)
- [Funcionalidades Atuais](#funcionalidades)
- [Equipe](#equipe)
- [Documentação Oficial](#documentacao)

---

<a id="sobre-o-projeto"></a>
## Sobre o Projeto

A informação que organiza a rotina de um estudante da UnB está fragmentada: a grade está no SIGAA, as datas de prova estão em PDFs de planos de ensino e os eventos circulam por Instagram, cartazes e grupos de WhatsApp. Não existe um lugar único onde o estudante veja o que vai acontecer nas próximas semanas.

O **Agenda UnB** resolve esse problema reunindo dois eixos em uma única aplicação web:

- **Agenda do Campus** — Catálogo público de eventos acadêmicos, culturais e esportivos de todos os campi (Darcy Ribeiro, FCTE, FCTS, FUP e FAL), com filtros por área, campus e turno.
- **Organizador Acadêmico** — Agenda pessoal com compromissos privados e eventos públicos adicionados. A Release 2 prevê seleção de turmas no catálogo público Followw e extração de avaliações de planos com revisão humana. [Contratos da Release 2](https://agendaunb.com.br/docs/atualizacoes#contratos-da-release-2)

---

<a id="stack-tecnologica"></a>
## Stack Tecnológica

| Camada | Tecnologia | Finalidade |
|--------|-----------|------------|
| Frontend | React 19, Vite 6, React Router 7 | SPA responsiva com roteamento client-side |
| Backend | Python 3, FastAPI, SQLAlchemy 2, Pydantic 2 | API REST com validação automática |
| Banco de Dados | PostgreSQL (Supabase) | Dados relacionais com Row Level Security |
| Autenticação | Supabase Auth | Google OAuth, login com e-mail/senha, JWT |
| Migrações | Supabase Migrations (SQL) | Versionamento de migrações |
| Ambiente Local | Supabase CLI + Docker | PostgreSQL, Auth e Studio locais |
| Documentação | Mintlify | Documentação publicada em `agendaunb.com.br/docs` |
| Tipografia | Orbitron + Inter (Google Fonts) | Display sci-fi + body legível |
| Iconografia | Material Symbols | Ícones consistentes em toda a UI |

---

<a id="como-executar"></a>
## ⚙️ Como Executar

Instale Git, Node.js 22 ou superior, Python 3.11, Docker e GNU Make. Clone a branch `dev` e abra a raiz do repositório.

<a id="execucao-rapida-via-makefile-recomendado"></a>

### Execução rápida

Com o Docker em execução, instale as dependências e suba o Supabase local:

```bash
make setup
npx supabase status -o env
```

Preencha o `.env` conforme o [guia de execução local](docs/processo/execucao-local.md), que também cobre a instalação manual. Depois, inicie a aplicação:

```bash
make dev
```

Abra a [aplicação local](http://localhost:5173). Para encerrar, pressione `Ctrl+C` e execute `make stop`.

O [guia de contribuição](https://agendaunb.com.br/docs/processo/contribuindo) descreve as verificações do projeto.

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

A API inclui catálogo público, CRUD privado, sugestões, eventos salvos, administração, upload/consulta de planos e saúde. Consulte os [contratos](https://agendaunb.com.br/docs/api-specs), a [ADR-003 (minimização e privacidade de planos)](https://agendaunb.com.br/docs/arquitetura/adrs/adr-003-minimizar-dados-de-planos) e a [ADR-014 (processamento assíncrono com IA)](https://agendaunb.com.br/docs/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia). A extração salva candidatos para revisão, sem criar compromissos, e permanece condicionada às flags operacionais e travas de privacidade.

### Banco de Dados

O esquema é versionado em migrações SQL. Além das tabelas da R1, inclui `eventos_salvos`, `notificacoes`, candidatos a avaliações, regras de moderação, RPCs administrativas e o bucket privado `syllabus_files` (PDF, até 10 MB). Upload, modelo de candidatos e fila do worker exigem as migrações #40/S6-D01/S6-B01; as políticas S6-D02 precisam ser validadas antes de usar dados reais.

Destaques de segurança:

- Perfil criado automaticamente no cadastro; e-mail imutável no perfil.
- Cadastro e autopromoção para professor exigem `@unb.br`; admins podem atribuir esse papel a contas de outro domínio.
- Eventos privados, vínculos salvos e notificações são restritos ao próprio usuário.
- Sugestões estudantis nascem pendentes; decisões de moderação são atômicas e recusas exigem justificativa.
- Somente admins alteram cargos de terceiros; não podem remover o próprio acesso administrativo.

Antes de disponibilizar API e frontend atualizados, aplique as migrações pendentes. No ambiente local já inicializado, execute `npx supabase migration up --local`. Consulte os guias de [eventos salvos](https://agendaunb.com.br/docs/eventos-salvos), [integração e rotas](https://agendaunb.com.br/docs/arquitetura/adrs/adr-001-integracao-fastapi-supabase) e [autorização e moderação](https://agendaunb.com.br/docs/arquitetura/adrs/adr-006-autorizacao-em-camadas).

---

<a id="equipe"></a>
## Equipe

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
## Documentação

A [documentação do Agenda UnB no Mintlify](https://agendaunb.com.br/docs) reúne os guias do projeto.

| Documento | Descrição |
|-----------|-----------|
| [Arquitetura](https://agendaunb.com.br/docs/arquitetura/visao-geral) | Visão arquitetural, stack e modelos de dados |
| [Requisitos](https://agendaunb.com.br/docs/produto/requisitos) | 21 RFs e 13 RNFs especificados |
| [Padrões](https://agendaunb.com.br/docs/produto/padroes) | Glossário, naming conventions e rotas da API |
| [Contratos do backend](https://agendaunb.com.br/docs/api-specs) | API atual e operações originadas na R1 |
| [Plano de implantação](https://agendaunb.com.br/docs/implantacao) | Hospedagem, CI/CD e homologação |
| [Atualizações pós-R1](https://agendaunb.com.br/docs/atualizacoes) | Calendário, eventos salvos, sugestões, moderação e administração |
| [Release v0.1.0](https://agendaunb.com.br/docs/processo/release-notes/v0-1-0) | Release note da primeira entrega |
| [Sprints](https://agendaunb.com.br/docs/sprints/sprint-1) | Acompanhamento ágil por ciclo |

---
