# Guia de Contribuição — Agenda UnB

Obrigado pelo interesse em contribuir com o **Agenda UnB**! Este guia orienta os desenvolvedores e colaboradores sobre o fluxo de trabalho, padrões de código e configuração do ambiente.

---

## 1. Pré-requisitos

Antes de iniciar, certifique-se de ter instalado em sua máquina:
* [Git](https://git-scm.com/)
* [Node.js](https://nodejs.org/) (Versão LTS recomendada, v18 ou superior)
* [Python 3.11+](https://www.python.org/) (Necessário para a API FastAPI, testes com pytest e MkDocs)
* [Docker Desktop / Docker Engine](https://www.docker.com/) (Em execução, necessário para o banco de dados e autenticação via Supabase)
* [GNU Make](https://www.gnu.org/software/make/) *(Opcional, mas altamente recomendado para automação de setup e execução em 1 comando)*

---

## 2. Configurando o Ambiente de Desenvolvimento

### 2.1 Clonar o Repositório
```bash
git clone https://github.com/unb-mds/2026-2-AgendaUnB.git
cd 2026-2-AgendaUnB
```

### 2.2 Fluxo Rápido com Makefile (Recomendado)

O projeto disponibiliza um [`Makefile`](../Makefile) na raiz que simplifica toda a rotina de desenvolvimento:

#### Passo 1: Setup completo em 1 comando
Cria o `.env` (a partir de `.env.example`), cria o ambiente virtual Python (`backend/venv`), instala as dependências de produção e de testes do backend, instala os pacotes do frontend e inicializa os containers do Supabase:

```bash
make setup
```

#### Passo 2: Executar todos os serviços juntos
Sobe simultaneamente o Banco de Dados (Supabase), a API FastAPI (`http://localhost:8000`) e a aplicação web React (`http://localhost:5173`) com *live reload*:

```bash
make dev
```

> 💡 **Encerramento limpo:** Pressione `Ctrl+C` no terminal para parar o Backend e o Frontend ao mesmo tempo. Para encerrar os containers do banco de dados, execute `make stop`.  
> 💡 **Nota para Windows:** Recomenda-se utilizar o terminal **Git Bash** ou **WSL** para executar os comandos do Makefile com suporte a execução concorrente de subprocessos.

#### Comandos Úteis do Makefile:
* `make dev` (ou `make run`) — Inicia Banco (Supabase), Backend e Frontend juntos
* `make setup` — Instala todas as dependências (Back + Front) e configura o ambiente
* `make stop` (ou `make down`) — Encerra os containers do banco de dados (Supabase)
* `make backend` — Executa apenas o servidor FastAPI na porta 8000
* `make frontend` — Executa apenas o servidor Vite na porta 5173
* `make docs` — Executa o servidor MkDocs em `http://127.0.0.1:8008`
* `make db-start` — Inicia os containers locais do Supabase
* `make db-stop` — Para os containers do Supabase
* `make db-reset` — Reaplica migrações SQL e o seed inicial no banco
* `make db-status` — Mostra o status e credenciais locais do Supabase
* `make test` — Executa a suíte de testes do Backend com `pytest`
* `make clean` — Limpa caches (`__pycache__`, `.pytest_cache`, `dist`)
* `make help` — Exibe a lista completa de comandos disponíveis

---

### 2.3 Fluxo Manual Passo a Passo (Alternativa sem Makefile)

Caso prefira executar cada serviço manualmente em terminais separados:

#### 2.3.1 Configurar Variáveis de Ambiente
Crie o arquivo `.env` na raiz a partir do `.env.example`:

| Linux / macOS (Bash) | Windows (PowerShell) | Windows (CMD) |
|---|---|---|
| `cp .env.example .env` | `Copy-Item .env.example .env` | `copy .env.example .env` |

#### 2.3.2 Banco de Dados (Supabase Local)
Com o Docker em execução, execute na raiz do repositório:
```bash
npx supabase start      # Inicia PostgreSQL, Auth e Studio
npx supabase db reset   # Aplica migrações e seed
```
* Studio local: [http://localhost:54323](http://localhost:54323)
* API Local: `http://127.0.0.1:54321`

#### 2.3.3 Executar o Backend (FastAPI)
Navegue até a pasta `backend/` e prepare o ambiente virtual:

| Etapa | Linux / macOS | Windows (PowerShell) | Windows (CMD) |
|---|---|---|---|
| **1. Entrar na pasta** | `cd backend` | `cd backend` | `cd backend` |
| **2. Criar ambiente virtual** | `python3 -m venv venv` | `python -m venv venv` | `python -m venv venv` |
| **3. Ativar o venv** | `source venv/bin/activate` | `.\venv\Scripts\Activate.ps1` | `venv\Scripts\activate.bat` |
| **4. Instalar dependências** | `pip install -r requirements.txt` | `pip install -r requirements.txt` | `pip install -r requirements.txt` |
| **5. Instalar dependências dev** | `pip install -r requirements-dev.txt` | `pip install -r requirements-dev.txt` | `pip install -r requirements-dev.txt` |
| **6. Iniciar a API** | `uvicorn src.main:app --reload` | `uvicorn src.main:app --reload` | `uvicorn src.main:app --reload` |

* API local: [http://localhost:8000](http://localhost:8000) | Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

#### 2.3.4 Executar o Frontend
Em outro terminal, a partir da raiz:
```bash
cd frontend
npm install
npm run dev
```
* 🌐 Aplicação web: [http://localhost:5173](http://localhost:5173)

#### 2.3.5 Executar a Documentação (MkDocs — Opcional)
```bash
pip install mkdocs-material
mkdocs serve -a 127.0.0.1:8008
```
* 📚 Documentação local: [http://127.0.0.1:8008](http://127.0.0.1:8008)

#### 2.3.6 Executar os Testes Automatizados
Com o ambiente virtual ativado na pasta `backend/`:
```bash
pytest tests/
```

---

## 3. Política de Branches

Para manter a organização das entregas nas Sprints de MDS, utilizamos branches nomeadas por tipo de tarefa:

* `main`: Código em produção/estável e versão final de cada Sprint.
* `develop` (ou branches de feature direto para a main com Pull Request):
  * `feat/<nome-da-funcionalidade>`: Para novas funcionalidades (ex: `feat/upload-plano-ensino`).
  * `fix/<correcao>`: Para resolução de bugs (ex: `fix/video-background`).
  * `docs/<documentacao>`: Para atualizações na documentação (ex: `docs/arquitetura`).
  * `chore/<tarefa>`: Para tarefas de manutenção ou infraestrutura (ex: `chore/config-mkdocs`).

---

## 4. Padrão de Mensagens de Commit

Seguimos a convenção de **Conventional Commits**:

```
<tipo>(<escopo>): <descrição curta no presente ou imperativo>
```

Exemplos:
* `feat(auth): adiciona autenticação social com o Google`
* `fix(navbar): corrige alinhamento dos botões em telas menores`
* `docs(requisitos): inclui novos requisitos de moderação`
* `refactor(parser): melhora desempenho da extração de datas em PDF`


## 5. Atualizações de banco e verificações

O estado atual inclui eventos salvos, sugestões, moderação, notificações e administração. Aplique todas as migrações em ordem antes de disponibilizar a API/frontend correspondente. Para atualizar o Supabase local já iniciado sem recriar o banco:

```bash
npx supabase migration up --local
```

`make db-reset` recria o banco, reaplica migrações e seed. Use-o somente quando puder descartar os dados locais. Para outros ambientes, siga o fluxo de migrações adotado pela equipe.

Execute as verificações a partir das respectivas pastas:

```bash
# backend, com o ambiente Python ativo
python -m pytest tests -q

# frontend
npm run build
node --test src/lib/calendar.test.js
```

Os testes de API usam SQLite. Para exercitar RLS, RPCs e triggers reais, configure `TEST_SUPABASE_DB_URL` com a conexão PostgreSQL do Supabase local e execute pytest. Os testes de banco só aceitam `localhost`/`127.0.0.1`, desfazem os dados ao terminar e são ignorados quando a variável não está configurada. Não use uma conexão de produção.

Para conferir o site de documentação, com MkDocs Material instalado:

```bash
mkdocs build --strict
```

Ao alterar uma funcionalidade, atualize os guias correspondentes e o estado em [Atualizações pós-R1](atualizacoes.md). Notas de versões anteriores são registros históricos. Registre uso relevante de IA em [AI-USAGE.md](AI-USAGE.md), incluindo o que foi efetivamente verificado.
