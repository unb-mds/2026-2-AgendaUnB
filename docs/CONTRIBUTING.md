# 🤝 Guia de Contribuição — Agenda UnB

Obrigado pelo interesse em contribuir com o **Agenda UnB**! Este guia orienta os desenvolvedores e colaboradores sobre o fluxo de trabalho, padrões de código e configuração do ambiente.

---

## 💻 1. Pré-requisitos

Antes de iniciar, certifique-se de ter instalado em sua máquina:
* [Git](https://git-scm.com/)
* [Node.js](https://nodejs.org/) (Versão LTS recomendada, v20 ou superior)
* [Python 3.10+](https://www.python.org/) (Necessário caso queira rodar o servidor de documentação MkDocs localmente)

---

## 🚀 2. Configurando o Ambiente de Desenvolvimento

### 2.1 Clonar o Repositório
```bash
git clone https://github.com/unb-mds/2026-2-AgendaUnB.git
cd 2026-2-AgendaUnB
```

### 2.2 Configurar as Variáveis de Ambiente
Crie o arquivo `.env` na raiz a partir do `.env.example`:

| Linux / macOS (Bash) | Windows (PowerShell) | Windows (CMD) |
|---|---|---|
| `cp .env.example .env` | `Copy-Item .env.example .env` | `copy .env.example .env` |

### 2.3 Banco de Dados (Supabase Local)
Com o Docker em execução, execute na raiz:
```bash
npx supabase start      # Inicia PostgreSQL, Auth e Studio
npx supabase db reset   # Aplica migrações e seed
```
Acesse o Studio local em `http://localhost:54323`.

### 2.4 Executar o Backend (FastAPI)
Navegue até a pasta `backend/` e prepare o ambiente virtual:

| Etapa | Linux / macOS | Windows (PowerShell) | Windows (CMD) |
|---|---|---|---|
| **1. Entrar na pasta** | `cd backend` | `cd backend` | `cd backend` |
| **2. Criar ambiente virtual** | `python3 -m venv venv` | `python -m venv venv` | `python -m venv venv` |
| **3. Ativar o venv** | `source venv/bin/activate` | `.\venv\Scripts\Activate.ps1` | `venv\Scripts\activate.bat` |
| **4. Instalar dependências** | `pip install -r requirements.txt` | `pip install -r requirements.txt` | `pip install -r requirements.txt` |
| **5. Iniciar a API** | `uvicorn src.main:app --reload` | `uvicorn src.main:app --reload` | `uvicorn src.main:app --reload` |

> 🌐 API local: `http://localhost:8000` | Swagger: `http://localhost:8000/docs`

### 2.5 Executar o Frontend
Em outro terminal:
```bash
cd frontend
npm install
npm run dev
```
A aplicação estará disponível em: `http://localhost:5173`.

### 2.6 Executar a Documentação (MkDocs — Opcional)
```bash
pip install mkdocs-material
mkdocs serve -a 127.0.0.1:8008
```
Acesse no navegador: `http://127.0.0.1:8008`.

---

## 🌿 3. Política de Branches

Para manter a organização das entregas nas Sprints de MDS, utilizamos branches nomeadas por tipo de tarefa:

* `main`: Código em produção/estável e versão final de cada Sprint.
* `develop` (ou branches de feature direto para a main com Pull Request):
  * `feat/<nome-da-funcionalidade>`: Para novas funcionalidades (ex: `feat/upload-plano-ensino`).
  * `fix/<correcao>`: Para resolução de bugs (ex: `fix/video-background`).
  * `docs/<documentacao>`: Para atualizações na documentação (ex: `docs/arquitetura`).
  * `chore/<tarefa>`: Para tarefas de manutenção ou infraestrutura (ex: `chore/config-mkdocs`).

---

## 💬 4. Padrão de Mensagens de Commit

Seguimos a convenção de **Conventional Commits**:

```
<tipo>(<escopo>): <descrição curta no presente ou imperativo>
```

Exemplos:
* `feat(auth): adiciona autenticação social com o Google`
* `fix(navbar): corrige alinhamento dos botões em telas menores`
* `docs(requisitos): inclui novos requisitos de moderação`
* `refactor(parser): melhora desempenho da extração de datas em PDF`
