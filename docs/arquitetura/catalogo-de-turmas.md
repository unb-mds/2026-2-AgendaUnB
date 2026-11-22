---
title: "Catálogo de turmas"
description: "Operação do adaptador público Followw, publicação atômica, vínculos autodeclarados e seleção de ofertas nos planos de ensino."
---

## Contratos e origem

A integração consulta exclusivamente a API pública do Followw (`https://followw.app/api`) via requisições `GET` HTTPS nas rotas `/public/classrooms/units`, `/public/classrooms` e `/public/subjects`, sem credenciais, cookies, proxy de ambiente ou redirecionamentos ([ADR-009](/arquitetura/adrs/adr-009-catalogo-publico-de-turmas)). A busca remota exige unidade ou código e período e retorna listas sem paginação remota exposta; a paginação servida pelo Agenda UnB é aplicada localmente sobre o banco.

A listagem ao vivo determina a disponibilidade atual das ofertas (`available`). `subject.sigaa_id` identifica a disciplina e a correspondência exata por código, unidade, período e número textual da turma permite adotar `classrooms[].sigaa_id` como identificador de oferta na origem. Zeros à esquerda no número da turma (como `"01"`) são preservados, nível desconhecido permanece nulo e professor e horário são tratados como atributos atualizáveis fora da identidade. Respostas inválidas, identidades incompletas e colisões não são convertidas silenciosamente e ficam registradas nos metadados da execução em `sincronizacoes_catalogo`.

## Operação e sincronização

O sincronizador opera fora das rotas HTTP da API usando conexão direta ao PostgreSQL ou pool em modo sessão (`DATABASE_URL`), pois a exclusão mútua entre execuções utiliza advisory lock de sessão.

```sh
python -m src.database.check_schema
python -m src.modules.classes.sync --period 2026.2
```

O comando consulta todas as unidades descobertas em sequência para os períodos informados via `--period` (ex.: `--period 2026.2 --period 2027.1`; quando omitido, utiliza `2026.2` como padrão). Semestres fora de `1` e `2` são rejeitados com `periodo_nao_suportado`.

Limites do adaptador: intervalo mínimo de 1 segundo entre inícios de chamadas, timeout de 30 segundos de leitura e 20 segundos nas demais fases HTTP, com até duas repetições para falhas transitórias e suporte a `Retry-After` limitado a 60 segundos.

A publicação ocorre de forma atômica após a coleta completa: a transação invoca `registrar_oferta_catalogo`, associa `publicacao_id` em `ofertas_turma` e conclui o registro em `sincronizacoes_catalogo` (que não armazena respostas brutas). Falha da busca ao vivo em qualquer unidade cancela a publicação daquela execução sem apagar ofertas anteriores. Ofertas ausentes na nova publicação deixam de aparecer na busca (`available: false`), preservando planos, vínculos e eventos já importados. Em falha da origem ou após 24 horas sem atualização concluída, `estado_catalogo` sinaliza `stale: true` mantendo o último catálogo válido; antes da primeira publicação válida, buscas e filtros retornam `503`.

No desenvolvimento local (`make dev`, via `scripts/dev.py`), quando ainda não existe publicação concluída no banco, o inicializador dispara a sincronização em processo separado em segundo plano. Durante essa carga inicial, a API retorna `503` e a interface orienta a espera repetindo apenas a leitura local a cada 15 segundos, sem acionar o Followw pelo navegador. Ao adquirir o lock de execução, execuções antigas presas em `executando` são marcadas como interrompidas.

Em produção, o job `catalog` em `.github/workflows/production-jobs.yml` permite executar a sincronização sob demanda via `workflow_dispatch`.

## API e interface

Todas as rotas do catálogo exigem autenticação via Supabase Auth com e-mail confirmado:

| Operação | Contrato |
| --- | --- |
| `GET /api/v1/class-offerings` | Filtros `year`, `semester`, `unit` (ID/sigla), `subject_code` exato, `q` (nome/código/professor/turma), `limit` 1–100 (padrão 20), `offset` ≥ 0 |
| `GET /api/v1/class-offerings/filters` | Unidades e períodos da última publicação, `source_updated_at` e `stale` |
| `GET /api/v1/class-offerings/{id}` | Oferta por UUID, inclusive retirada da busca atual, com campo `available` |
| `GET /api/v1/me/class-offerings` | Ofertas seguidas pela sessão, inclusive ofertas retiradas |
| `PUT /api/v1/me/class-offerings/{id}` | Segue oferta disponível; idempotente (`204`) |
| `DELETE /api/v1/me/class-offerings/{id}` | Remove vínculo da sessão; idempotente (`204`) |
| `GET /api/v1/class-offerings/{id}/shared-plans` | Lista versões compartilhadas da oferta para seguidores (`403` sem vínculo), com autoria, procedência, votos, indicador de versão padrão e sinalização de alterações pós-importação, ordenadas por votos positivos e data mais recente |
| `GET /api/v1/syllabus?offering_id={id}` | Lista planos privados do usuário, com filtro opcional de oferta |
| `POST /api/v1/syllabus/upload` e `/text` | Exigem `offering_id` seguido pela conta (`403` sem vínculo, `409` se oferta retirada, `503` sem catálogo); disciplina, turma e período são derivados do catálogo |

A busca devolve `items`, `total`, `limit`, `offset`, `source_updated_at` e `stale`, com ordenação determinística por relevância, código, unidade, período, turma e UUID. Erros seguem o padrão `detail` da API.

Na interface `/plano-de-ensino`, usuários autenticados percorrem o fluxo em duas etapas (**1. Selecionar turmas** e **2. Organizar datas**), gerenciando **Suas turmas** e consultando tanto seus próprios envios quanto os **Planos compartilhados da turma**. O botão **Tentar novamente** repete apenas a leitura local na API sem disparar sincronização no Followw. Quando o catálogo estiver indisponível (`503`), a interface preserva o acesso ao cadastro manual de compromissos em **Meus Eventos**. Deixar de seguir uma oferta não apaga eventos particulares já importados.

## Verificação automatizada

- **Adaptador, API e publicação atômica:** `backend/tests/test_class_catalog_api.py`, `backend/tests/test_followw_catalog_adapter.py` e `backend/tests/test_catalog_publication_database.py` (PostgreSQL isolado).
- **Interface:** `frontend/tests/` (Playwright em desktop e mobile, temas claro e escuro, seleção entre buscas e estados `503`).
