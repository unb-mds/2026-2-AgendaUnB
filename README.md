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
    - [Frontend](#frontend)
    - [Backend](#backend)
    - [Banco de Dados](#banco-de-dados)
- [Funcionalidades da R1](#funcionalidades)
- [Equipe](#equipe)
- [Documentação](#documentacao)

---

<a id="sobre-o-projeto"></a>
## 🚀 Sobre o Projeto

A informação que organiza a rotina de um estudante da UnB está fragmentada: a grade está no SIGAA, as datas de prova estão em PDFs de planos de ensino e os eventos circulam por Instagram, cartazes e grupos de WhatsApp. Não existe um lugar único onde o estudante veja o que vai acontecer nas próximas semanas.

O **Agenda UnB** resolve esse problema reunindo dois eixos em uma única aplicação web:

- **Agenda do Campus** — Catálogo público de eventos acadêmicos, culturais e esportivos de todos os campi (Darcy Ribeiro, FCTE, FCTS, FUP e FAL), com filtros por área, campus e turno.
- **Organizador Acadêmico** — Calendário pessoal e privado do estudante, com criação, edição e exclusão de compromissos, e futuramente alimentado por extração automática de datas a partir de planos de ensino.

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

### <a id="pre-requisitos"></a>Pré-requisitos

- [Node.js](https://nodejs.org/pt-br) (v18+)
- [Python](https://www.python.org/downloads/) (v3.11+)
- [Supabase CLI](https://supabase.com/docs/guides/cli/getting-started) (requer Docker)

### <a id="frontend"></a>Frontend

~~~bash
git clone https://github.com/unb-mds/2026-2-AgendaUnB.git
cd 2026-2-AgendaUnB/frontend
npm install
~~~

Crie um arquivo `.env` na raiz do projeto configurando as variáveis de ambiente do Supabase e do banco de dados. A partir da raiz do repositório, execute:

~~~bash
cp .env.example .env
~~~

Inicie o servidor de desenvolvimento do frontend:

~~~bash
cd frontend
npm run dev
~~~

A aplicação estará disponível em `http://localhost:5173`.

### <a id="banco-de-dados"></a>Banco de Dados (Supabase)

~~~bash
npx supabase start        # Sobe PostgreSQL + Auth + Studio localmente
npx supabase db reset     # Aplica todas as migrações e seed
~~~

O Supabase Studio local estará em `http://localhost:54323`.

---

### <a id="backend"></a>Backend

~~~bash
cd backend

# 1. Criar o ambiente virtual do Python
python3 -m venv venv

# 2. Ativar o ambiente virtual
source venv/bin/activate

# 3. Instalar as bibliotecas Python
pip install -r requirements.txt

# 4. Iniciar a API em modo desenvolvimento
uvicorn src.main:app --reload
~~~

> 🌐 *API FastAPI:* [http://localhost:8000](http://localhost:8000)  
> 📖 *Swagger (documentação interativa):* [http://localhost:8000/docs](http://localhost:8000/docs)


<a id="funcionalidades"></a>
## ✨ Funcionalidades da R1

### Frontend

| Funcionalidade | Descrição |
|---------------|-----------|
| Landing Page | Hero section, funcionalidades, sobre e equipe |
| Cadastro | Modal com seletor Estudante/Professor, validação de @unb.br para professor |
| Login | Modal de login com e-mail/senha e Google OAuth |
| Página de Eventos | Listagem pública e pessoal, filtros por área/campus/turno, busca textual |
| Criação de Eventos | Modal com DatePicker e TimePicker customizados, campos completos |
| Edição e Exclusão | CRUD completo para eventos pessoais |
| Detalhe do Evento | Página dedicada com descrição, organizador, badges e link externo |
| Tema Dark / Light | Alternância completa visual (temas claro e escuro) |
| NavBar | Glassmorphism, avatar do usuário, navegação contextual |

### Backend (API)

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|:------------:|
| GET | `/api/v1/events` | Listar eventos públicos aprovados | Não |
| GET | `/api/v1/events/{id}` | Detalhe de evento público | Não |
| POST | `/api/v1/events` | Criar evento público | Professor/Admin |
| DELETE | `/api/v1/events/{id}` | Excluir evento público | Professor/Admin |
| GET | `/api/v1/me/events` | Listar eventos pessoais | Sim |
| GET | `/api/v1/me/events/{id}` | Detalhe de evento pessoal | Sim (dono) |
| POST | `/api/v1/me/events` | Criar evento pessoal | Sim |
| PUT | `/api/v1/me/events/{id}` | Atualizar evento pessoal | Sim (dono) |
| DELETE | `/api/v1/me/events/{id}` | Excluir evento pessoal | Sim (dono) |
| GET | `/health` | Health check | Não |

### Banco de Dados

7 tabelas criadas com RLS: `profiles`, `campus`, `categories`, `eventos`, `eventos_pessoais`, `planos_ensino`, `avaliacoes`.

Destaques de segurança:

- Trigger automático de criação de perfil no registro
- CHECK constraint: professor exige e-mail `@unb.br`
- E-mail imutável no perfil (impede escalada de privilégios)
- Eventos pessoais isolados por usuário via RLS

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
| [Release v0.1.0](https://unb-mds.github.io/2026-2-AgendaUnB/release-notes/v0.1.0/) | Release note da primeira entrega |
| [Sprints](https://unb-mds.github.io/2026-2-AgendaUnB/sprints/sprint-0/) | Acompanhamento ágil por ciclo |

---
