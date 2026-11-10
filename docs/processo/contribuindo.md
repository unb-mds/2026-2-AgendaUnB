---
title: "Como contribuir"
description: "Guia completo para configurar o ambiente, executar serviços e seguir os padrões de contribuição do projeto Agenda UnB."
---

Obrigado pelo interesse em contribuir com o **Agenda UnB**! Este guia orienta os desenvolvedores e colaboradores sobre o fluxo de trabalho, padrões de código e configuração do ambiente.

---

<a id="setup-requisitos"></a>

## Pré-requisitos

Antes de iniciar, certifique-se de ter instalado em sua máquina:

- [Git](https://git-scm.com/)
- [Node.js](https://nodejs.org/) (Versão LTS recomendada, v18 ou superior)
- [Python 3.11+](https://www.python.org/) (Necessário para a API FastAPI, testes com pytest e MkDocs)
- [Docker Desktop / Docker Engine](https://www.docker.com/) (Em execução, necessário para o banco de dados e autenticação via Supabase)
- [GNU Make](https://www.gnu.org/software/make/) para automatizar a configuração e a execução. No Linux, instale pelo gerenciador de pacotes. No macOS, use as ferramentas de desenvolvimento. No Windows, use Chocolatey (`choco install make`), Scoop (`scoop install make`) ou winget (`winget install GnuWin32.Make`).

---

## Configurando o Ambiente de Desenvolvimento

### Clonar o Repositório

```bash
git clone https://github.com/unb-mds/2026-2-AgendaUnB.git
cd 2026-2-AgendaUnB
```

### Fluxo Rápido com Makefile (Recomendado)

O projeto disponibiliza um [`Makefile`](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/Makefile) na raiz que simplifica toda a rotina de desenvolvimento:

#### Passo 1: Setup completo em 1 comando

Cria o `.env` (a partir de `.env.example`), cria o ambiente virtual Python (`backend/venv`), instala as dependências de produção e de testes do backend, instala os pacotes do frontend e inicializa os containers do Supabase:

```bash
make setup
```

#### Passo 2: Executar todos os serviços juntos

Sobe simultaneamente o Banco de Dados (Supabase), a API FastAPI (`http://localhost:8000`) e a aplicação web React (`http://localhost:5173`) com _live reload_:

```bash
make dev
```

> 💡 **Encerramento limpo:** Pressione `Ctrl+C` no terminal para parar o Backend e o Frontend ao mesmo tempo. Para encerrar os containers do banco de dados, execute `make stop`.<br />💡 **Nota para Windows:** Com o **Git for Windows** instalado no caminho padrao, o Makefile seleciona seu Bash automaticamente, inclusive ao executar `make` pelo PowerShell ou CMD. Para uma instalacao personalizada, informe o executavel: `make SHELL="C:/caminho/Git/bin/bash.exe" dev`. No WSL, utilize as ferramentas e dependencias instaladas dentro do Linux.

#### Comandos Úteis do Makefile:

- `make dev` (ou `make run`) — Inicia Banco (Supabase), Backend e Frontend juntos
- `make setup` — Instala todas as dependências (Back + Front) e configura o ambiente
- `make stop` (ou `make down`) — Encerra os containers do banco de dados (Supabase)
- `make backend` — Executa apenas o servidor FastAPI na porta 8000
- `make frontend` — Executa apenas o servidor Vite na porta 5173
- `make docs` — Executa o servidor MkDocs em `http://127.0.0.1:8008`
- `make db-start` — Inicia os containers locais do Supabase
- `make db-stop` — Para os containers do Supabase
- `make db-reset` — Reaplica migrações SQL e o seed inicial no banco
- `make db-status` — Mostra o status e credenciais locais do Supabase
- `make test` — Executa a suíte de testes do Backend com `pytest`
- `make clean` — Limpa caches (`__pycache__`, `.pytest_cache`, `dist`)
- `make help` — Exibe a lista completa de comandos disponíveis

---

### Fluxo Manual Passo a Passo (Alternativa sem Makefile)

Caso prefira executar cada serviço manualmente em terminais separados:

<a id="setup-ambiente"></a>

#### Configurar Variáveis de Ambiente

Crie o arquivo `.env` na raiz a partir do `.env.example`:

| Linux / macOS (Bash) | Windows (PowerShell) | Windows (CMD) |
| --- | --- | --- |
| `cp .env.example .env` | `Copy-Item .env.example .env` | `copy .env.example .env` |

<a id="setup-supabase"></a>

#### Banco de Dados (Supabase Local)

Com o Docker em execução, execute na raiz do repositório:

```bash
npx supabase start      # Inicia PostgreSQL, Auth e Studio
npx supabase db reset   # Aplica migrações e seed
```

- Studio local: [http://localhost:14323](http://localhost:14323)
- API Local: `http://127.0.0.1:14321`

<a id="setup-backend"></a>

#### Executar o Backend (FastAPI)

Navegue até a pasta `backend/` e prepare o ambiente virtual:

| Etapa | Linux / macOS | Windows (PowerShell) | Windows (CMD) |
| --- | --- | --- | --- |
| **1. Entrar na pasta** | `cd backend` | `cd backend` | `cd backend` |
| **2. Criar ambiente virtual** | `python3 -m venv venv` | `python -m venv venv` | `python -m venv venv` |
| **3. Ativar o venv** | `source venv/bin/activate` | `.\venv\Scripts\Activate.ps1` | `venv\Scripts\activate.bat` |
| **4. Instalar dependências** | `pip install -r requirements.txt` | `pip install -r requirements.txt` | `pip install -r requirements.txt` |
| **5. Instalar dependências dev** | `pip install -r requirements-dev.txt` | `pip install -r requirements-dev.txt` | `pip install -r requirements-dev.txt` |
| **6. Iniciar a API** | `uvicorn src.main:app --reload` | `uvicorn src.main:app --reload` | `uvicorn src.main:app --reload` |

- API local: [http://localhost:8000](http://localhost:8000)
- Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)
- Verificação básica: [http://localhost:8000/health](http://localhost:8000/health)

Se o PowerShell bloquear a ativação do ambiente, execute os comandos pela coluna CMD ou chame `.\venv\Scripts\python.exe` diretamente, por exemplo `.\venv\Scripts\python.exe -m uvicorn src.main:app --reload`.

Se `python -m venv venv` terminar sem erro mas `venv\Scripts\python.exe` não existir, o `python` ativo no terminal pode ser outro (por exemplo, o do MSYS2). Confira com `where.exe python` e crie o ambiente com o executável correto:

```powershell
& "C:\caminho\do\python.exe" -m venv venv
```

Também é possível usar o ambiente sem ativação:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\venv\Scripts\python.exe -m uvicorn src.main:app --reload
```

<a id="setup-frontend"></a>

#### Executar o Frontend

Em outro terminal, a partir da raiz:

```bash
cd frontend
npm install
npm run dev
```

- Aplicação web: [http://localhost:5173](http://localhost:5173)
- Build estático: `npm run build` em `frontend/`.

<a id="setup-mkdocs"></a>

#### Executar a Documentação (MkDocs — Opcional)

```bash
pip install mkdocs-material mkdocs-redirects
mkdocs serve -f .github/mkdocs.yml -a 127.0.0.1:8008
```

- 📚 Documentação local: [http://127.0.0.1:8008](http://127.0.0.1:8008)

#### Executar os Testes Automatizados

Com o ambiente virtual ativado na pasta `backend/`:

```bash
pytest tests/
```

---

## Adicionar uma página de documentação

Crie a página em `docs/` como `.md` para Markdown comum ou `.mdx` se usar componentes do Mintlify. Para incluí-la no menu do Mintlify, adicione a rota sem extensão ao `docs.json`. Use o mesmo arquivo Markdown para os dois sites sempre que a página for compartilhada.

Para incluir uma página compartilhada no menu do MkDocs, adicione o caminho com extensão à navegação de `.github/mkdocs.yml`. As páginas são organizadas por assunto em `docs/arquitetura/`, `docs/produto/` e `docs/processo/`. Ao mover uma página publicada, atualize os links e configure o redirecionamento nos dois sites.

---

## Política de Branches

Para manter a organização das entregas nas Sprints de MDS, utilizamos branches nomeadas por tipo de tarefa:

- `main`: Código em produção/estável e versão final de cada Sprint.
- `develop` (ou branches de feature direto para a main com Pull Request):
  - `feat/<nome-da-funcionalidade>`: Para novas funcionalidades (ex: `feat/upload-plano-ensino`).
  - `fix/<correcao>`: Para resolução de bugs (ex: `fix/video-background`).
  - `docs/<documentacao>`: Para atualizações na documentação (ex: `docs/arquitetura`).
  - `chore/<tarefa>`: Para tarefas de manutenção ou infraestrutura (ex: `chore/config-mkdocs`).

---

## Padrão de Mensagens de Commit

Seguimos a convenção de **Conventional Commits**:

```text
<tipo>(<escopo>): <descrição curta no presente ou imperativo>
```

Exemplos:

- `feat(auth): adiciona autenticação social com o Google`
- `fix(navbar): corrige alinhamento dos botões em telas menores`
- `docs(requisitos): inclui novos requisitos de moderação`
- `refactor(parser): melhora desempenho da extração de datas em PDF`

<a id="setup-verificacoes"></a>

## Atualizações de banco e verificações

O estado atual inclui eventos salvos, sugestões, moderação, notificações e administração. Aplique todas as migrações em ordem antes de disponibilizar a API/frontend correspondente. Para atualizar o Supabase local já iniciado sem recriar o banco:

```bash
npx supabase migration up --local
```

O mesmo comando está disponível como `make db-migrate`. Revise as migrações antes
de aplicá-las. `supabase start` não atualiza um volume existente automaticamente.
`make dev` e `make backend` verificam as tabelas e colunas usadas pela API antes
de iniciar o servidor; um schema antigo interrompe a inicialização com os nomes
faltantes e a orientação de migração. `make db-check` executa essa verificação
isoladamente, sem alterar dados. Ela não substitui os testes de constraints,
triggers, RLS e RPCs nem aplica migrações em ambientes remotos.

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

Para conferir a documentação com as dependências do MkDocs instaladas:

```bash
mkdocs build -f .github/mkdocs.yml --strict
```

Ao alterar uma funcionalidade, atualize os guias correspondentes e o estado em [Atualizações pós-R1](../atualizacoes.md). Notas de versões anteriores são registros históricos. Registre uso relevante de IA em [AI-USAGE.md](uso-de-ia.md), incluindo o que foi efetivamente verificado.

## Manutenção da documentação

Registre uma decisão técnica significativa em um arquivo numerado em `docs/arquitetura/adrs/`. Inclua estado, contexto, decisão, alternativas e consequências. Vincule o ADR ao [índice de decisões](../arquitetura/visao-geral.md) e ao guia ou contrato correspondente. Quando outra decisão a substituir, mantenha o registro anterior e aponte para o novo.

No mesmo PR que alterar rotas, schemas, autorização, regras, migrações ou operação, atualizar [API](../api-specs.md), [Arquitetura](../arquitetura/visao-geral.md), [Padrões](../produto/padroes.md) e/ou [Implantação](../implantacao.md), conforme o assunto. Preservar notas históricas de release e distinguir estado implementado de proposta. Confira os diagramas renderizados e execute `mint broken-links --check-redirects` ao alterar links ou a navegação do Mintlify.

### Versão de Python observada

Em 08/11/2026, `backend/venv/Scripts/python.exe --version` retornou **Python 3.14.4**, consistente com `backend/venv/pyvenv.cfg`. O Makefile usa esse ambiente virtual, mas cria novos ambientes com o Python disponível na máquina, sem fixar versão. O workflow de documentação configura 3.11; isso não determina a versão do backend. Esta observação local não certifica compatibilidade de toda a faixa 3.11+.
