---
title: "Catálogo de turmas — integração #70 e #71"
description: "Operação do adaptador público Followw, publicação atômica, vínculos e seleção de ofertas nos planos."
---

## Contratos e origem

Implementação baseada na #67, no esquema S7-D01 da #69 e na migração do [PR #104](https://github.com/unb-mds/2026-2-AgendaUnB/pull/104), commit `8a8cf42ef07e7b15278b3b78277b42eea4cf8483`. A migração original foi preservada; a evolução está em `20261111120000_publicacao_catalogo.sql`. RF05, RNF07–09 e RNF11 orientam esta integração.

O servidor permite apenas GET HTTPS em `api.followw.app`, nas rotas `/public/classrooms/units`, `/public/classrooms` e `/public/subjects`. Não usa credenciais, cookies, proxy do ambiente ou redirecionamentos. A busca de disciplinas exige unidade ou código e período. Os contratos observados retornam listas sem paginação remota exposta; não se inventam parâmetros de paginação. A paginação da API do Agenda UnB é local.

A lista ao vivo determina presença. O ID de `subject.sigaa_id` identifica a disciplina. Somente uma correspondência exata por código, unidade, período e número textual permite adotar `classrooms[].sigaa_id` como ID de oferta. `01` permanece `01`, nível desconhecido fica nulo e professor/horário não participam da identidade. Respostas inválidas, identidades incompletas e colisões nunca são convertidas silenciosamente. Identidades rejeitadas ficam nos metadados da execução para revisão.

## Operação

Aplicar as migrações pendentes e implantar backend e frontend juntos: PDF multipart e texto JSON agora exigem `offering_id`. As leituras e a revisão de planos legados continuam disponíveis.

Em `backend`, configurar `DATABASE_URL` de servidor com acesso às tabelas e funções. Usar conexão direta ou pool em modo sessão: a exclusão mútua usa advisory lock de sessão; pool em modo transação não serve para este comando.

```sh
python -m src.database.check_schema
python -m src.modules.classes.sync --period 2026.2
```

O comando consulta todas as unidades descobertas uma vez, em sequência. Períodos adicionais exigem flags repetidas, por exemplo `--period 2026.2 --period 2027.1`, após validar cobertura. Sem flags, somente `2026.2`. Semestres fora de 1/2 são rejeitados com `periodo_nao_suportado`, sem convertê-los; verão não é habilitado.

Limites do adaptador: intervalo mínimo de um segundo entre inícios de chamadas, timeout de 20 segundos por operação HTTP, uma repetição para falhas transitórias. `Retry-After` aceita segundos ou data HTTP até 60 segundos; espera maior interrompe a tentativa. Esses valores não representam cotas confirmadas do Followw.

Uma execução por vez, sem rota HTTP de sincronização. Consultas HTTP leem somente o banco. Após a coleta, uma transação chama `registrar_oferta_catalogo`, associa `publicacao_id` e publica a execução concluída. Leituras do catálogo são protegidas contra publicação concorrente. Uma unidade vazia válida conta como consultada; falha da busca ao vivo em qualquer unidade cancela a publicação inteira. Falha apenas no enriquecimento não retira as ofertas ao vivo: registra a cobertura do enriquecimento e utiliza a identidade natural.

`sincronizacoes_catalogo` contém unidades, períodos, cobertura por unidade/período, quantidades, rejeições e código sanitizado de erro. Não armazena respostas brutas. Ofertas ausentes na nova publicação saem da busca sem exclusão física; vínculos, planos e eventos permanecem. Falha conserva a publicação e a data anteriores. `estado_catalogo` indica `stale` após falha ou 24 horas. Antes da primeira publicação válida, busca e filtros retornam 503; uma publicação vazia válida é cache, retornando 200 com lista vazia.

Não habilitar recorrência antes de medir duração e cobertura de uma varredura integral em homologação. A saída JSON do comando inclui a cobertura; guardar essa saída como evidência operacional.

## API e interface

Todas as rotas abaixo exigem a autenticação Supabase existente:

| Operação | Contrato |
| --- | --- |
| `GET /api/v1/class-offerings` | `year`, `semester`, `unit` (ID/sigla), `subject_code` exato, `q` (nome/código/professor/turma), `limit` 20–100 (mínimo 1), `offset` ≥0 |
| `GET /api/v1/class-offerings/filters` | Unidades e períodos da última publicação, `source_updated_at`, `stale` |
| `GET /api/v1/class-offerings/{id}` | Oferta por UUID, inclusive retirada, com `available` |
| `GET /api/v1/me/class-offerings` | Vínculos da sessão, inclusive ofertas retiradas |
| `PUT /api/v1/me/class-offerings/{id}` | Seguir oferta disponível, idempotente, 204 |
| `DELETE /api/v1/me/class-offerings/{id}` | Remover somente o vínculo da sessão, idempotente, 204 |
| `GET /api/v1/class-offerings/{id}/shared-plans` | Versões compartilhadas para seguidores, paginação 20/100, 403 para não seguidores; não expõe texto privado |
| `GET /api/v1/syllabus?offering_id={id}` | Histórico particular filtrado pela oferta; sem filtro mantém o histórico legado |
| `POST /api/v1/syllabus/upload` e `/text` | `offering_id` obrigatório; 409 se oferta retirada, 503 sem publicação; disciplina/turma/período derivados do catálogo |

A busca devolve `items`, `total`, `limit`, `offset`, `source_updated_at` e `stale`, com ordenação estável por código, unidade, período, turma e UUID. Cada item contém UUID, nome/código da disciplina, turma, ano/semestre, unidade, nível, professor, horário e disponibilidade. Erros seguem `detail` da API existente; filtros inválidos retornam 422.

A rota `/plano-de-ensino?modo=catalogo` exige login. “Minhas turmas” persiste no servidor e abre `?modo=catalogo&oferta={UUID}`. A jornada mostra histórico particular, convite para envio e versões compartilhadas; estas são de consulta nesta entrega. Publicação, votação e importação de versões compartilhadas permanecem nas entregas específicas da R2. A revisão e confirmação de candidatos particulares reutilizam o fluxo existente. A demonstração mantém fixtures e ações locais em modo separado.

“Tentar novamente” repete a leitura local; nunca dispara sincronização do Followw. Em 503 há acesso ao cadastro manual. Deixar de seguir preserva os eventos particulares já importados.

## Evidências locais — 10/11/2026

- Sondagem real: 211 unidades; `code=FGA0108`, `semester=2026.2`: duas ofertas ao vivo, uma disciplina com duas ofertas enriquecidas; duas normalizadas, zero rejeitadas, dois IDs de oferta. Executada com `PYTHONPATH=.` e `python scripts/probe_followw_catalog.py`, sem gravação de catálogo.
- Migrações: aplicadas na cópia isolada `agenda_catalog_7071_verified` do esquema local existente; todas as 28 migrações aplicadas em `agenda_catalog_7071_fresh`, com estruturas internas Auth/Storage e sem tabelas da aplicação. Não equivale a homologar serviços hospedados de Auth/Storage.
- Backend: testes HTTP de autenticação, filtros, paginação, vínculo idempotente/isolado, retirada, cache, privacidade e exigência de oferta; adaptador com timeout, retry, 429, redirecionamento, respostas inválidas, credenciais ausentes e identidade; PostgreSQL com publicação completa, adoção de ID, retirada e falha intermediária. Comandos e resultados finais devem acompanhar o PR.
- Frontend: testes Playwright de vínculo após recarga, oferta correta, paginação, vazio, 503, login, teclado e largura 360/1365; regressão de envio/revisão em 360/768/1365 e temas claro/escuro. Capturas do catálogo inspecionadas em desktop e celular; detector de interface sem achados.

## Pendências de homologação e fechamento

Não foram executados deploy, varredura integral das 211 unidades nem teste de indisponibilidade contra o ambiente hospedado. A amostra de FGA0108 não comprova cobertura global. Registrar versão implantada, saída da varredura, cenário de falha com vínculo existente, links do PR e nome do revisor humano nas issues #70/#71 antes de fechá-las. Nenhuma issue foi fechada ou marcada como homologada por esta implementação.

Reversão: desabilitar o comando operacional e reverter consumidores junto com o backend; preservar tabelas e vínculos. Não apagar ofertas ou reverter migrações destrutivamente para ocultar uma publicação.

## Resultado final da validação local

- Backend: `python -m pytest -q` — 209 passaram, três ignorados (integrações opcionais), com PostgreSQL isolado.
- Navegador: `E2E_PORT=5187 E2E_BROWSER_CHANNEL=chrome npx playwright test --workers=2` — 44 passaram.
- Lógica frontend: `npm test` — 19 passaram.
- `npm run build` passou; aviso de chunk principal acima de 500 kB permanece.
- Build da documentação não executado: MkDocs não está instalado no venv local.
- As 28 migrações passaram em base sem tabelas da aplicação; as duas novas passaram na atualização da cópia isolada.

## Jornada única

A página `/plano-de-ensino` apresenta apenas a Demonstração interativa, agora conectada à API autenticada para catálogo, vínculos, envios e planos. O seletor de variantes foi removido. `make dev` inicia Supabase, aplica migrações locais, verifica o esquema e inicia API e Vite; `BACKEND_PORT` também configura o proxy do frontend. A API inicia sem o recarregador do Uvicorn para compatibilidade com Windows.

### Correção da jornada e inicialização local

A jornada original de quatro etapas foi restaurada. Visitantes usam exemplos locais; usuários autenticados usam catálogo, vínculos, preparação, revisão e confirmação pela API dentro dessas etapas. Não há seletor de variantes. O inicializador `scripts/dev.py`, chamado por `make dev`, escolhe portas livres quando as solicitadas estão ocupadas, informa as URLs efetivas e configura o proxy e CORS correspondentes. Ele espera o health da API e encerra seus próprios processos quando um serviço falha ou a sessão recebe Ctrl+C. Serviços anteriores são preservados.

### Primeira carga no desenvolvimento local

`make dev` verifica a existência de uma publicação concluída. Quando ainda não há
catálogo válido, inicia o comando de sincronização como processo separado da API.
A consulta retorna 503 durante essa carga, e a interface explica a espera e repete
a leitura local a cada 15 segundos. Não chama o Followw pelo navegador.
O comando registra o progresso por unidade no terminal. Ao adquirir o lock de
execução, marca execuções antigas ainda `executando` como interrompidas, pois o
lock comprova que não existe outro sincronizador ativo. Uma nova execução nunca
publica parcialmente para contornar a ausência de cache.

### Carga local concluída

Execução `5a4fa5df-bde0-4c98-902a-bc5dd7c55d06`: 211 unidades consultadas em 2026.2, 9.154 ofertas publicadas. Filtros HTTP 200 com 211 unidades; busca FGA0108/FCTE/2026.2 HTTP 200 com duas ofertas e `stale: false`. Validação HTTP local via TestClient com autenticação substituída para a leitura, banco real local. Não representa deploy.
