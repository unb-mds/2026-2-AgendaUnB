<div align="center">

<video src="https://github.com/user-attachments/assets/12817e2b-55d0-460e-9279-62d86f90c694" autoplay loop muted playsinline width="100%"></video>

<br/>

<p style="letter-spacing: 2px; font-size: 14px;">SEJAM BEM-VINDOS AO</p>

# **AGENDA UNB**

**Plataforma centralizada de eventos e organização acadêmica da Universidade de Brasilia**

Metodos de Desenvolvimento de Software — 2026/2 — Grupo G8

<br/>

[Documentacao](https://unb-mds.github.io/2026-2-AgendaUnB/) · [Figma](https://www.figma.com/board/RlZe9FgO3Bz3gPkxevs8UJ/AGENDA-UNB?node-id=1-217&t=USKjIQh4OXxQVwsG-1) · [Miro](https://miro.com/welcomeonboard/b0lMYXFqaEFMTnNpejdUOE1tLy8rOGNHdk5QVndFOUN0ZTFtc1kvWC9UUWdCbUJXVkpFU2JKRXhqUHpRZEYxekt6NUNFZXNzOXkxVDRxRmk0TjI1akdVY0Q5QW0vUENuMVpvYWRaZzdVNFZOd3RuM2RYU0wySUdxdk9jSm9OV3ZzVXVvMm53MW9OWFg5bkJoVXZxdFhRPT0hdjE=?share_link_id=945222608724)

</div>

---

## Sobre o Projeto

A informacao que organiza a rotina de um estudante da UnB esta fragmentada: a grade esta no SIGAA, as datas de prova estao em PDFs de planos de ensino e os eventos circulam por Instagram, cartazes e grupos de WhatsApp. Nao existe um lugar unico onde o estudante veja o que vai acontecer nas proximas semanas.

O **Agenda UnB** resolve esse problema reunindo dois eixos em uma unica aplicacao web:

- **Agenda do Campus** — Catalogo publico de eventos academicos, culturais e esportivos de todos os campi (Darcy Ribeiro, FCTE, FCTS, FUP e FAL), com filtros por area, campus e turno.
- **Organizador Academico** — Calendario pessoal e privado do estudante, com criacao, edicao e exclusao de compromissos, e futuramente alimentado por extracao automatica de datas a partir de planos de ensino.

---

## Sumario

- [Sobre o Projeto](#sobre-o-projeto)
- [Stack Tecnologica](#stack-tecnologica)
- [Como Executar](#como-executar)
  - [Pre-requisitos](#pre-requisitos)
  - [Frontend](#frontend)
  - [Backend](#backend)
  - [Banco de Dados (Supabase)](#banco-de-dados-supabase)
- [Arquitetura](#arquitetura)
- [Funcionalidades Implementadas](#funcionalidades-implementadas)
- [Equipe](#equipe)
- [Documentacao](#documentacao)
- [Licenca](#licenca)

---

## Stack Tecnologica

| Camada | Tecnologia | Finalidade |
|--------|-----------|------------|
| Frontend | React 19, Vite 6, React Router 7 | SPA responsiva com roteamento client-side |
| Backend | Python 3, FastAPI, SQLAlchemy 2, Pydantic 2 | API REST com validacao automatica |
| Banco de Dados | PostgreSQL (Supabase) | Dados relacionais com Row Level Security |
| Autenticacao | Supabase Auth | Google OAuth, login com e-mail/senha, JWT |
| Migracoes | Supabase Migrations (SQL) | 5 migracoes versionadas |
| Ambiente Local | Supabase CLI + Docker | PostgreSQL, Auth e Studio locais |
| Documentacao | MkDocs Material | Site publicado no GitHub Pages |
| Tipografia | Orbitron + Inter (Google Fonts) | Display sci-fi + body legivel |
| Iconografia | Material Symbols | Icones consistentes em toda a UI |

---

## Como Executar

### Pre-requisitos

- [Node.js](https://nodejs.org/pt-br) (v18+)
- [Python](https://www.python.org/downloads/) (v3.11+)
- [Supabase CLI](https://supabase.com/docs/guides/cli/getting-started) (requer Docker)

### Frontend

```bash
git clone https://github.com/unb-mds/2026-2-AgendaUnB.git
cd 2026-2-AgendaUnB
npm install
```

Crie um arquivo `.env` na raiz com as variaveis do Supabase (veja `.env.example`):

```
VITE_SUPABASE_URL=<sua-url>
VITE_SUPABASE_ANON_KEY=<sua-chave>
VITE_API_URL=http://127.0.0.1:8000/api/v1
```

Inicie o servidor de desenvolvimento:

```bash
npm run dev
```

A aplicacao estara disponivel em `http://localhost:5173`.

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

Crie um arquivo `backend/.env` com as variaveis necessarias (veja `backend/.env.example`):

```
DATABASE_URL=postgresql://<usuario>:<senha>@<host>:<porta>/<banco>
SUPABASE_URL=<sua-url>
SUPABASE_ANON_KEY=<sua-chave>
```

Inicie a API:

```bash
uvicorn src.main:app --reload
```

A API estara disponivel em `http://127.0.0.1:8000`. Documentacao interativa em `/docs`.

### Banco de Dados (Supabase)

```bash
supabase start        # Sobe PostgreSQL + Auth + Studio localmente
supabase db reset     # Aplica todas as migracoes e seed
```

O Supabase Studio local estara em `http://localhost:54323`.

---

## Arquitetura

```
Navegador                        Supabase                      Backend
+-----------------+      +---------------------+      +------------------+
| React SPA       |----->| Auth (JWT, OAuth)   |      | FastAPI          |
| Vite + Router   |      | PostgreSQL          |<-----| SQLAlchemy       |
| Supabase JS SDK |----->| Row Level Security  |      | Auth Middleware   |
+-----------------+      +---------------------+      +------------------+
        |                                                      ^
        |              fetch + Bearer JWT                      |
        +------------------------------------------------------+
```

**Fluxo resumido:**

1. O frontend autentica via Supabase Auth (e-mail/senha ou Google OAuth).
2. O Supabase cria a sessao JWT e o trigger `tg_cria_perfil` insere o perfil no banco.
3. Para operacoes de eventos, o frontend chama a API FastAPI com o token JWT.
4. O middleware da API valida o token contra o Supabase e busca o papel do usuario.
5. As rotas aplicam controle de acesso (RBAC): apenas professores/admins gerenciam eventos publicos.

---

## Funcionalidades Implementadas

### Frontend

| Funcionalidade | Descricao |
|---------------|-----------|
| Landing Page | Hero com video shader animado, secoes de funcionalidades, sobre e equipe |
| Cadastro | Modal com seletor Estudante/Professor, validacao de @unb.br para professor |
| Login | Modal de login com e-mail/senha e Google OAuth |
| Pagina de Eventos | Listagem publica e pessoal, filtros por area/campus/turno, busca textual |
| Criacao de Eventos | Modal com DatePicker e TimePicker customizados, campos completos |
| Edicao e Exclusao | CRUD completo para eventos pessoais |
| Detalhe do Evento | Pagina dedicada com descricao, organizador, badges e link externo |
| Tema Dark / Light | Alternancia completa com video de fundo responsivo ao tema |
| NavBar | Glassmorphism, avatar do usuario, navegacao contextual |

### Backend (API)

| Metodo | Rota | Descricao | Autenticacao |
|--------|------|-----------|:------------:|
| GET | `/api/v1/events` | Listar eventos publicos aprovados | Nao |
| GET | `/api/v1/events/{id}` | Detalhe de evento publico | Nao |
| POST | `/api/v1/events` | Criar evento publico | Professor/Admin |
| DELETE | `/api/v1/events/{id}` | Excluir evento publico | Professor/Admin |
| GET | `/api/v1/me/events` | Listar eventos pessoais | Sim |
| GET | `/api/v1/me/events/{id}` | Detalhe de evento pessoal | Sim (dono) |
| POST | `/api/v1/me/events` | Criar evento pessoal | Sim |
| PUT | `/api/v1/me/events/{id}` | Atualizar evento pessoal | Sim (dono) |
| DELETE | `/api/v1/me/events/{id}` | Excluir evento pessoal | Sim (dono) |
| GET | `/health` | Health check | Nao |

### Banco de Dados

7 tabelas criadas com RLS: `profiles`, `campus`, `categories`, `eventos`, `eventos_pessoais`, `planos_ensino`, `avaliacoes`.

Destaques de seguranca:

- Trigger automatico de criacao de perfil no cadastro
- CHECK constraint: professor exige e-mail `@unb.br`
- E-mail imutavel no perfil (impede escalacao de privilegio)
- Eventos pessoais isolados por usuario via RLS

---

## Equipe

| Nome | Papel | GitHub |
|------|:-----:|--------|
| Thomas Augusto Amorim de Araujo | Frontend | [@thomas4ugust0](https://github.com/thomas4ugust0) |
| Gabriel Escramin Lourenco | Frontend | [@Bielziin07](https://github.com/Bielziin07) |
| Heitor Gomes Monteiro | Backend | [@heitormontt](https://github.com/heitormontt) |
| Thomaz Marra Martins | Backend | [@marrathomaz](https://github.com/marrathomaz) |
| Felipe Couto Duque | Banco de Dados | [@felipecduque7](https://github.com/felipecduque7) |
| Luis Davi Pontes da Silva | Banco de Dados | [@pontesluis](https://github.com/pontesluis) |

---

## Documentacao

Toda a documentacao do projeto esta publicada no GitHub Pages:

**[unb-mds.github.io/2026-2-AgendaUnB](https://unb-mds.github.io/2026-2-AgendaUnB/)**

| Documento | Descricao |
|-----------|-----------|
| [Arquitetura](https://unb-mds.github.io/2026-2-AgendaUnB/Architecture/) | Visao arquitetural, stack e modelos de dados |
| [Requisitos](https://unb-mds.github.io/2026-2-AgendaUnB/requisitos/) | 21 RFs e 13 RNFs especificados |
| [Padroes](https://unb-mds.github.io/2026-2-AgendaUnB/padroes/) | Glossario, naming conventions e rotas da API |
| [Release v0.1.0](https://unb-mds.github.io/2026-2-AgendaUnB/release-notes/v0.1.0/) | Release note da primeira entrega |
| [Sprints](https://unb-mds.github.io/2026-2-AgendaUnB/sprints/sprint-0/) | Acompanhamento agil por ciclo |

---

## Licenca

Projeto academico desenvolvido na disciplina de Metodos de Desenvolvimento de Software — Universidade de Brasilia, 2026/2.
