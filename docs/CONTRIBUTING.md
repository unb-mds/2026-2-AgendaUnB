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
Para rodar localmente, você precisará das variáveis do Supabase e do banco de dados. Temos um único arquivo de ambiente na raiz:
```bash
cp .env.example .env
```

### 2.3 Executar o Frontend
O frontend foi isolado em um diretório próprio para melhor organização:
```bash
cd frontend
npm install
npm run dev
```
A aplicação estará disponível em: `http://localhost:5173`.

### 2.4 Executar o Backend
O backend (FastAPI/Python) reside na sua respectiva pasta:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn src.main:app --reload
```
A API local estará disponível em `http://localhost:8000` e a documentação do Swagger em `http://localhost:8000/docs`.

### 2.5 Executar a Documentação (MkDocs) Localmente
```bash
# Instalar a dependência do tema Material (pode ser no venv do backend ou global)
pip install mkdocs-material

# Subir o servidor local com hot-reload da documentação
mkdocs serve
```
Acesse no navegador: `http://127.0.0.1:8000`.

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
