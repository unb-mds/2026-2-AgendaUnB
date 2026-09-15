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
git clone https://github.com/unb-mds/G8-2026-2.git
cd G8-2026-2
```

### 2.2 Executar o Frontend
```bash
# Instalar as dependências do projeto
npm install

# Iniciar o servidor de desenvolvimento Vite
npm run dev
```
O aplicativo estará disponível em: `http://localhost:5173`.

### 2.3 Executar a Documentação (MkDocs) Localmente
```bash
# Instalar a dependência do tema Material
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
