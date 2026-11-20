---
title: "Como contribuir"
description: "Fluxo de trabalho, verificações e convenções de contribuição do Agenda UnB."
---

Obrigado pelo interesse em contribuir com o **Agenda UnB**! Este guia orienta os desenvolvedores e colaboradores sobre o fluxo de trabalho, padrões de código e configuração do ambiente.

---

## Execução local

O [guia de execução local](/processo/execucao-local) reúne os pré-requisitos, as variáveis de ambiente e os comandos para iniciar e encerrar a aplicação.

## Adicionar uma página de documentação

Crie a página em `docs/` como `.md` para Markdown comum ou `.mdx` se usar componentes do Mintlify. Para incluí-la no menu do Mintlify, adicione a rota sem extensão ao `docs.json`. Nos arquivos compartilhados, use links internos a partir da raiz da documentação, sem `/docs` e sem a extensão `.md`. Por exemplo, `[Requisitos](/produto/requisitos)`. Para arquivos de código, configuração e resultados JSON, use o link do arquivo no GitHub.

Para incluir uma página compartilhada no menu do MkDocs, adicione o caminho com extensão à navegação de `.github/mkdocs.yml`. As páginas são organizadas por assunto em `docs/arquitetura/`, `docs/produto/` e `docs/processo/`. Ao mover uma página publicada, atualize os links e configure o redirecionamento nos dois sites. Em `docs.json`, use a rota do arquivo a partir de `docs/`, como `/produto/requisitos`. O Mintlify aplica o prefixo público `/docs`.

---

## Política de Branches

### Fluxo por issue e Pull Request

Cada issue deve ter **uma única branch e um único PR**, reutilizados nas entregas parciais. Antes de iniciar, confira se já existem branch e PR para a issue. Recomenda-se incluir o número da issue no nome da branch, mantendo os tipos adotados pelo projeto (ex.: `feat/123-upload-plano-ensino`).

Ao concluir sua parte, marque na própria issue somente os itens efetivamente concluídos e validados. Atualize o mesmo PR com as entregas, evidências e próximos passos. O checklist da issue é a fonte de verdade do progresso e não deve ser duplicado no PR.

Use `status: <incompleto>` e mantenha o PR como Draft enquanto houver qualquer check da issue pendente. Use `status: <completo>` somente quando todos os checks estiverem concluídos; se algum item for reaberto, volte para incompleto. Enquanto incompleto, vincule com `Relacionado à issue #NUMERO`; quando completo, substitua por `Fixes #NUMERO`. Faça o merge apenas após as verificações e aprovações aplicáveis.

Preencha o [template de PR](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/.github/PULL_REQUEST_TEMPLATE.md) com contexto, mudanças, testes, resultados, impactos e pendências. O template orienta o fluxo; não sincroniza checklists nem bloqueia merges automaticamente.


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

## Atualizações de banco e verificações {#setup-verificacoes}

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

Tabelas e funções novas nascem fechadas para a API do Supabase: siga as [regras para novas migrações](seguranca.md#regras-para-novas-migracoes), ou os testes estruturais de segurança falham.

Os testes de API usam SQLite. Para exercitar RLS, RPCs e triggers reais, configure `TEST_SUPABASE_DB_URL` com a conexão PostgreSQL do Supabase local e execute pytest. Os testes de banco só aceitam `localhost`/`127.0.0.1`, desfazem os dados ao terminar e são ignorados quando a variável não está configurada. Não use uma conexão de produção.

Ao alterar uma funcionalidade, atualize os guias correspondentes e o estado em [Atualizações pós-R1](/atualizacoes). Notas de versões anteriores são registros históricos. Registre uso relevante de IA em [Uso de IA](/processo/uso-de-ia), incluindo o que foi efetivamente verificado.

## Manutenção da documentação

Registre uma decisão técnica significativa em um arquivo numerado em `docs/arquitetura/adrs/`. Inclua estado, contexto, decisão, alternativas e consequências. Vincule o ADR ao [índice de decisões](/arquitetura/visao-geral) e ao guia ou contrato correspondente. Quando outra decisão a substituir, mantenha o registro anterior e aponte para o novo.

No mesmo PR que alterar rotas, schemas, autorização, regras, migrações ou operação, atualizar [API](/api-specs), [Arquitetura](/arquitetura/visao-geral), [Padrões](/produto/padroes) e/ou [Implantação](/implantacao), conforme o assunto. Preservar notas históricas de release e distinguir estado implementado de proposta. Confira os diagramas renderizados e execute `mint broken-links --check-redirects` ao alterar links ou a navegação do Mintlify.

### Visualizar e validar a documentação {#documentacao-local}

Para usar o Mintlify localmente, execute a partir da raiz:

```bash
cd docs
npx mint dev
```

Abra [http://localhost:3000](http://localhost:3000). Na pasta `docs/`, execute `npx mint broken-links --check-redirects` para conferir links e redirecionamentos.

Para visualizar o site do MkDocs, instale as dependências em um ambiente virtual Python e execute na raiz:

```bash
python -m pip install mkdocs-material mkdocs-redirects
make docs
```

Abra [http://127.0.0.1:8008](http://127.0.0.1:8008). Para validar a compilação do MkDocs, use `mkdocs build -f .github/mkdocs.yml --strict`.
