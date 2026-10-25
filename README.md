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
- **Organizador Acadêmico** — Calendário pessoal e privado do estudante, com criação, edição e exclusão de compromissos, e futuramente alimentado por extração automática de datas a partir de planos de ensino e atestado de matrícula.

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
### 📦 Pré-requisitos

Certifique-se de possuir instalado em seu ambiente:
* [Node.js](https://nodejs.org/) (v18+ ou LTS)
* [Python](https://www.python.org/downloads/) (v3.11+ ou v3.12)
* [Docker Desktop / Docker Engine](https://www.docker.com/) (em execução para o Supabase)
* [Git](https://git-scm.com/)
* [GNU Make](https://www.gnu.org/software/make/) *(Recomendado para automação dos comandos em 1 passo)*:
  * **Linux (Ubuntu/Debian):** `sudo apt install make` ou `build-essential`
  * **macOS:** Integrado com as ferramentas de desenvolvedor (`xcode-select --install`)
  * **Windows:** Disponível via [Chocolatey](https://chocolatey.org/install) (`choco install make`), [Scoop](https://scoop.sh/) (`scoop install make`), [winget](https://learn.microsoft.com/pt-br/windows/package-manager/winget/) (`winget install GnuWin32.Make`) ou utilizando o terminal **Git Bash** / **WSL**.

---

<a id="execucao-rapida-via-makefile-recomendado"></a>
### ⚡ Execução Rápida via Makefile (Recomendado)

O projeto conta com um [`Makefile`](Makefile) na raiz que automatiza a configuração do ambiente, a instalação de dependências e a execução integrada de todos os serviços.

> 💡 **Dica para Windows:** No Windows, recomenda-se executar os comandos `make` através do terminal **Git Bash** (instalado junto com o Git) ou **WSL**, garantindo a compatibilidade de execução concorrente dos processos com encerramento seguro via `Ctrl+C`.

#### 1. Configuração completa do ambiente
Cria o `.env` a partir de `.env.example`, cria o ambiente virtual Python (`backend/venv`), instala as dependências do backend (`requirements.txt` e `requirements-dev.txt`), instala os pacotes do frontend (`npm install`) e inicializa os containers do Supabase local (para Windows, é importante lembrar de estar com o Docker aberto):

```bash
make setup
```

#### 2. Iniciar todos os serviços (Banco + Backend + Frontend)
Sobe o banco Supabase, a API FastAPI e o servidor Vite de forma concorrente em um único terminal com recarregamento automático (*live reload*):

```bash
make dev
```

Após iniciar, os serviços estarão disponíveis nos seguintes endereços:

| Serviço | Endereço Local | Descrição |
|---|---|---|
| **Frontend Web** | [http://localhost:5173](http://localhost:5173) | Interface React da aplicação |
| **Backend API** | [http://localhost:8000](http://localhost:8000) | Servidor FastAPI |
| **Swagger / OpenAPI** | [http://localhost:8000/docs](http://localhost:8000/docs) | Documentação interativa dos endpoints |
| **Health Check** | [http://localhost:8000/health](http://localhost:8000/health) | Verificação de integridade da API |
| **Supabase Studio** | [http://localhost:54323](http://localhost:54323) | Dashboard visual do PostgreSQL e Auth |

> **Para encerrar:** Pressione `Ctrl+C` no terminal. O script encerra simultaneamente o Backend e o Frontend de forma limpa. Para parar os containers do banco de dados, execute `make stop`.

---

#### 📌 Guia de Comandos do Makefile

| Comando | Finalidade |
|---|---|
| `make dev` *(ou `make run`)* | Inicia Supabase, Backend e Frontend juntos em um único comando |
| `make setup` | Instala todas as dependências (Back + Front), cria `.env` e sobe o Supabase |
| `make stop` *(ou `make down`)* | Encerra os containers do banco de dados (Supabase) |
| `make backend` | Executa apenas o servidor FastAPI (`http://localhost:8000`) |
| `make frontend` | Executa apenas o servidor Vite do Frontend (`http://localhost:5173`) |
| `make docs` | Executa o servidor local de documentação MkDocs (`http://127.0.0.1:8008`) |
| `make db-start` | Inicia os containers locais do Supabase (PostgreSQL, Auth, Storage) |
| `make db-stop` | Para os containers locais do Supabase |
| `make db-reset` | Reaplica todas as migrações SQL e o seed inicial no banco de dados |
| `make db-status` | Exibe o status e URLs dos serviços locais do Supabase |
| `make test` | Executa a suíte de testes automatizados do Backend com `pytest` |
| `make clean` | Limpa arquivos temporários e caches (`__pycache__`, `.pytest_cache`, `dist`) |
| `make help` *(ou `make`)* | Exibe o menu interativo com os comandos disponíveis |

---

<a id="execucao-manual-passo-a-passo"></a>
### Execução Manual Passo a Passo (Alternativa sem Make)

Caso não utilize o `make` ou prefira executar cada serviço separadamente em terminais dedicados:

<a id="1-configuracao-inicial-e-env"></a>
#### 1. Configuração Inicial e `.env`

Clone o repositório e crie o arquivo de configuração `.env` a partir do modelo `.env.example`:

| Etapa | Linux / macOS (Bash / Zsh) | Windows (PowerShell) | Windows (CMD) |
|---|---|---|---|
| **Clonar repositório** | `git clone https://github.com/unb-mds/2026-2-AgendaUnB.git`<br>`cd 2026-2-AgendaUnB` | `git clone https://github.com/unb-mds/2026-2-AgendaUnB.git`<br>`cd 2026-2-AgendaUnB` | `git clone https://github.com/unb-mds/2026-2-AgendaUnB.git`<br>`cd 2026-2-AgendaUnB` |
| **Copiar variáveis `.env`** | `cp .env.example .env` | `Copy-Item .env.example .env` | `copy .env.example .env` |

---

<a id="2-banco-de-dados-supabase"></a>
#### 2. Banco de Dados (Supabase Local)

O Supabase gerencia o PostgreSQL, autenticação, storage e migrações locais via Docker. Execute na **raiz do repositório**:

| Ação | Comando (Linux / macOS / Windows) | Equivalente Make | Finalidade |
|---|---|---|---|
| **Iniciar containers** | `npx supabase start` | `make db-start` | Sobe PostgreSQL, Supabase Auth, Storage e Studio local |
| **Resetar banco / Migrações** | `npx supabase db reset` | `make db-reset` | Aplica todas as migrações SQL versionadas e o seed inicial |
| **Status dos serviços** | `npx supabase status` | `make db-status` | Exibe chaves anon, porta da API e URLs |
| **Parar containers** | `npx supabase stop` | `make db-stop` | Encerra os serviços locais do Supabase |

> **Supabase Studio (Dashboard Local):** [http://localhost:54323](http://localhost:54323)  
> **API URL Local:** `http://127.0.0.1:54321`

---

<a id="3-backend-fastapi"></a>
#### 3. Backend (API FastAPI)

Abra um terminal, acesse a pasta `backend/`, configure o ambiente virtual Python, instale as dependências e inicie o servidor:

| Etapa | Linux / macOS (Bash / Zsh) | Windows (PowerShell) | Windows (CMD) |
|---|---|---|---|
| **1. Entrar na pasta** | `cd backend` | `cd backend` | `cd backend` |
| **2. Criar ambiente virtual** | `python3 -m venv venv` | `python -m venv venv` | `python -m venv venv` |
| **3. Ativar o venv** | `source venv/bin/activate` | `.\venv\Scripts\Activate.ps1` | `venv\Scripts\activate.bat` |
| **4. Instalar dependências** | `pip install -r requirements.txt` | `pip install -r requirements.txt` | `pip install -r requirements.txt` |
| **5. Instalar dependências dev** | `pip install -r requirements-dev.txt` | `pip install -r requirements-dev.txt` | `pip install -r requirements-dev.txt` |
| **6. Iniciar a API** | `uvicorn src.main:app --reload` | `uvicorn src.main:app --reload` | `uvicorn src.main:app --reload` |

> 💡 **Nota para Windows (PowerShell):** Se a execução de scripts for bloqueada ao ativar o ambiente (`running scripts is disabled`), execute antes no PowerShell:  
> ```powershell
> Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
> ```
> E em seguida execute novamente `.\venv\Scripts\Activate.ps1`.

---

<a id="4-frontend-react"></a>
#### 4. Frontend (React + Vite)

Abra um novo terminal na raiz do projeto, acesse a pasta `frontend/`, instale os módulos e inicie o servidor de desenvolvimento:

| Etapa | Linux / macOS (Bash) | Windows (PowerShell / CMD) | Equivalente Make |
|---|---|---|---|
| **1. Entrar na pasta** | `cd frontend` | `cd frontend` | — |
| **2. Instalar dependências** | `npm install` | `npm install` | `make check-frontend` |
| **3. Iniciar o dev server** | `npm run dev` | `npm run dev` | `make frontend` |
| **4. Gerar build estático** | `npm run build` | `npm run build` | — |

---

<a id="5-documentacao-local-mkdocs"></a>
#### 5. Documentação Local (MkDocs — Opcional)

Para rodar localmente o site de documentação com tema Material:

| Etapa | Linux / macOS | Windows (PowerShell / CMD) | Equivalente Make |
|---|---|---|---|
| **Instalar MkDocs Material** | `pip install mkdocs-material` | `pip install mkdocs-material` | — |
| **Iniciar servidor de docs** | `mkdocs serve -a 127.0.0.1:8008` | `mkdocs serve -a 127.0.0.1:8008` | `make docs` |

> **Documentação local:** [http://127.0.0.1:8008](http://127.0.0.1:8008)

---

<a id="6-testes-automatizados"></a>
#### 6. Testes Automatizados (Backend)

Para executar a suíte de testes unitários e de integração do Backend:

| Ação | Via Makefile | Manualmente (na pasta `backend/` com `venv` ativo) |
|---|---|---|
| **Executar testes** | `make test` | `pytest tests/` |

Para o calendário, execute `node --test src/lib/calendar.test.js` em `frontend/`. Os testes de RLS/RPC/triggers exigem `TEST_SUPABASE_DB_URL` apontando para o Supabase local e são ignorados sem essa configuração. Veja [Contribuição](docs/CONTRIBUTING.md).

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
| Plano de Ensino | `/plano-de-ensino`: página informativa; upload e extração ainda em preparação |
| Criação de Eventos | Modal com DatePicker e TimePicker customizados, campos completos |
| Edição e Exclusão | CRUD completo para eventos pessoais |
| Detalhe do Evento | Página dedicada com descrição, organizador, badges e link externo |
| Tema Dark / Light | Alternância completa visual (temas claro e escuro) |
| NavBar | Glassmorphism, avatar do usuário, navegação contextual |

### Backend (API)

A API atual reúne 15 operações: catálogo público, CRUD privado, sugestões, eventos salvos e saúde. Dez já existiam na R1. Consulte os [contratos completos](docs/api-specs.md) para rotas, payloads, permissões e códigos HTTP; a administração e a moderação usam RPCs Supabase separadas.

### Banco de Dados

O esquema é versionado em **11 migrações SQL**. Além das tabelas da R1, foram adicionadas `eventos_salvos` e `notificacoes`, regras de sugestões/moderação, RPCs administrativas e o bucket privado `syllabus_files` (PDF, até 10 MB). O bucket prepara a infraestrutura; upload e parser ainda não estão disponíveis na aplicação.

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
| [Arquitetura](https://unb-mds.github.io/2026-2-AgendaUnB/Architecture/) | Visão arquitetural, stack e modelos de dados |
| [Requisitos](https://unb-mds.github.io/2026-2-AgendaUnB/requisitos/) | 21 RFs e 13 RNFs especificados |
| [Padrões](https://unb-mds.github.io/2026-2-AgendaUnB/padroes/) | Glossário, naming conventions e rotas da API |
| [Contratos do backend](docs/api-specs.md) | API atual e operações originadas na R1 |
| [Plano de implantação](docs/implantacao.md) | Proposta de hospedagem, CI/CD e homologação; ainda não implantada |
| [Atualizações pós-R1](docs/atualizacoes.md) | Calendário, eventos salvos, sugestões, moderação e administração |
| [Release v0.1.0](https://unb-mds.github.io/2026-2-AgendaUnB/release-notes/v0.1.0/) | Release note da primeira entrega |
| [Sprints](https://unb-mds.github.io/2026-2-AgendaUnB/sprints/sprint-1/) | Acompanhamento ágil por ciclo |

---
