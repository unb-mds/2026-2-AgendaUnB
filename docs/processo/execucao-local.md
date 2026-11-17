---
title: "Execução local"
description: "Instale as dependências e rode o Agenda UnB com React, FastAPI e Supabase local."
---

## Pré-requisitos

- [Git](https://git-scm.com/)
- [Node.js](https://nodejs.org/) 22 ou superior com npm, para o frontend e a CLI do Supabase
- [Python](https://www.python.org/) 3.11, versão usada no CI do backend, com `pip` e `venv`
- [Docker Desktop ou Docker Engine](https://www.docker.com/) em execução
- [GNU Make](https://www.gnu.org/software/make/) para a execução automatizada. No Windows, use Git Bash com Make instalado ou instale os pré-requisitos no WSL.

Clone a branch de desenvolvimento:

```bash
git clone --branch dev https://github.com/unb-mds/2026-2-AgendaUnB.git
cd 2026-2-AgendaUnB
```

## Execução com Make {#com-make}

Na raiz do repositório, rode `make setup`. Ele cria o `.env` se necessário, instala as dependências do backend em `backend/venv`, instala o frontend com `npm ci` e inicia o Supabase local. A primeira execução baixa as imagens do Docker.

```bash
make setup
npx supabase status -o env
```

Configure o [arquivo de ambiente](#variaveis-de-ambiente) com os valores exibidos pela CLI. Em seguida, inicie a aplicação:

```bash
make dev
```

O Make aplica as migrações pendentes, verifica o esquema e inicia a API e o frontend. Use as portas informadas no terminal se as portas padrão estiverem ocupadas. Pressione `Ctrl+C` para encerrar a API e o frontend e execute `make stop` para parar o Supabase.

## Execução manual {#execucao-manual}

Na raiz do projeto, copie `.env.example` para `.env` na primeira execução. No PowerShell, use `Copy-Item .env.example .env`.

```bash
cp .env.example .env
npx supabase start
npx supabase migration up --local
npx supabase status -o env
```

Preencha o [arquivo de ambiente](#variaveis-de-ambiente). Depois, instale as dependências e execute a API a partir da raiz:

```bash
cd backend
python3 -m venv venv
./venv/bin/python -m pip install -r requirements-dev.txt
./venv/bin/python -m uvicorn src.main:app --reload --port 8000
```

No PowerShell, use `python -m venv venv` e substitua `./venv/bin/python` por `./venv/Scripts/python.exe`. O arquivo `requirements-dev.txt` inclui as dependências da API e o pytest.

Em outro terminal, também a partir da raiz, instale e execute o frontend:

```bash
cd frontend
npm ci
npm run dev -- --port 5173 --strictPort
```

Pressione `Ctrl+C` em cada terminal e rode `npx supabase stop` na raiz para encerrar. Se o catálogo de turmas estiver vazio, carregue o período em uso com `python -m src.modules.classes.sync --period 2026.2` a partir de `backend/`, usando o Python do ambiente virtual. `make dev` tenta fazer essa primeira carga automaticamente.

## Variáveis de ambiente {#variaveis-de-ambiente}

Edite o `.env` da raiz com os valores de `npx supabase status -o env`:

| Variável no `.env` | Valor |
| --- | --- |
| `APP_ENV`, `VITE_DEPLOYMENT_ENV` | `local` |
| `DATABASE_URL` | `DB_URL`, trocando o esquema `postgresql://` por `postgresql+psycopg://` |
| `SUPABASE_URL`, `VITE_SUPABASE_URL` | `API_URL` |
| `SUPABASE_ANON_KEY` | `ANON_KEY` |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | `PUBLISHABLE_KEY`. Se a CLI exibir apenas `ANON_KEY`, use `VITE_SUPABASE_ANON_KEY` com a chave anônima. |
| `SUPABASE_SERVICE_ROLE_KEY` | `SERVICE_ROLE_KEY`, usada pelo backend nas operações de armazenamento de planos |
| `VITE_API_URL` | Em branco para usar o proxy local do Vite para a API |

Use somente as credenciais do Supabase local. Mantenha a chave `service_role` no backend, sem prefixo `VITE_`.

O fluxo básico de cadastro por e-mail, login e consulta de eventos usa os serviços locais. Para testar **Continuar com Google**, configure no Google Cloud o callback `http://127.0.0.1:14321/auth/v1/callback` e defina `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID` e `SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET` no `.env`. O Make carrega essas variáveis ao iniciar o Supabase. Para a execução manual, exporte-as no terminal antes de rodar `npx supabase start`. Reinicie o Supabase se ele já estiver em execução e abra o frontend em `http://127.0.0.1:5173` para testar esse login.

## Serviços locais {#servicos-locais}

| Serviço | Endereço padrão |
| --- | --- |
| Aplicação React | [http://localhost:5173](http://localhost:5173) |
| Swagger da API FastAPI | [http://localhost:8000/docs](http://localhost:8000/docs) |
| Verificação da API | [http://localhost:8000/health](http://localhost:8000/health) |
| Supabase Studio | [http://localhost:14323](http://localhost:14323) |
| Caixa de e-mails de teste para cadastro e recuperação de senha | [http://localhost:14324](http://localhost:14324) |

Consulte os [testes automatizados](/processo/contribuindo#setup-verificacoes) e as [instruções para visualizar a documentação](/processo/contribuindo#documentacao-local).
