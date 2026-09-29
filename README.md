<div align="center">

<video src="https://github.com/user-attachments/assets/12817e2b-55d0-460e-9279-62d86f90c694" autoplay loop muted playsinline width="100%"></video>


# **AGENDA UNB**

**Plataforma centralizada de eventos e organização acadêmica da Universidade de Brasilia**

Metodos de Desenvolvimento de Software - 2026/2 - Grupo G8

<br/>

[Documentacao](https://unb-mds.github.io/2026-2-AgendaUnB/) · [Figma](https://www.figma.com/board/RlZe9FgO3Bz3gPkxevs8UJ/AGENDA-UNB?node-id=1-217&t=USKjIQh4OXxQVwsG-1) · [Miro](https://miro.com/welcomeonboard/b0lMYXFqaEFMTnNpejdUOE1tLy8rOGNHdk5QVndFOUN0ZTFtc1kvWC9UUWdCbUJXVkpFU2JKRXhqUHpRZEYxekt6NUNFZXNzOXkxVDRxRmk0TjI1akdVY0Q5QW0vUENuMVpvYWRaZzdVNFZOd3RuM2RYU0wySUdxdk9jSm9OV3ZzVXVvMm53MW9OWFg5bkJoVXZxdFhRPT0hdjE=?share_link_id=945222608724)

</div>

---

## Sobre o Projeto

A informacao que organiza a rotina de um estudante da UnB esta fragmentada: a grade esta no SIGAA, as datas de prova estao em PDFs de planos de ensino e os eventos circulam por Instagram, cartazes e grupos de WhatsApp. Nao existe um lugar unico onde o estudante veja o que vai acontecer nas proximas semanas.

O **Agenda UnB** resolve esse problema reunindo dois eixos em uma unica aplicacao web:

- **Agenda do Campus** - Catalogo publico de eventos academicos, culturais e esportivos de todos os campi (Darcy Ribeiro, FCTE, FCTS, FUP e FAL), com filtros por area, campus e turno.
- **Organizador Academico** - Calendario pessoal e privado do estudante, com criacao, edicao e exclusao de compromissos, e futuramente alimentado por extracao automatica de datas a partir de planos de ensino.

---

## Sumario

- [Sobre o Projeto](#sobre-o-projeto)
- [Stack Tecnologica](#stack-tecnologica)
- [Como Executar](#como-executar)
  - [Pre-requisitos](#pre-requisitos)
  - [Frontend](#frontend)
  - [Backend](#backend)
  - [Banco de Dados](#banco-de-dados-supabase)
- [Equipe](#equipe)
- [Documentacao](#documentacao)

---

## Stack Tecnologica

| Camada | Tecnologia |
|--------|-----------|
| Frontend | React 19, Vite 6, React Router 7 |
| Backend | Python 3, FastAPI, SQLAlchemy 2, Pydantic 2 |
| Banco de Dados | PostgreSQL (Supabase) |
| Autenticacao | Supabase Auth |
| Migracoes | Supabase Migrations (SQL) |
| Ambiente Local | Supabase CLI + Docker |
| Documentacao | MkDocs Material 
| Tipografia | Orbitron + Inter (Google Fonts) |
| Iconografia | Material Symbols |

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

