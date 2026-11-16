# Validação e revisão técnica — S7-B05, 16/11/2026

Escopo: issue [#75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75), "Coletar eventos da Agenda UnB com atualização e deduplicação". Requisitos associados: RF14 (detalhes, localização, URL, intervalo e dia inteiro), RF15 (cobertura multicampus), RF16 (coleta periódica com procedência e deduplicação), RNF02 (proteção de integridade e procedência no servidor), RNF11 (preservação dos dados coletados perante indisponibilidade da fonte externa) e RNF13 (testes automatizados e CI reproduzível), além da [ADR-011](arquitetura/adrs/adr-011-datas-civis-e-instantes.md).

Responsável principal: @pontesluis. Corresponsável: @marrathomaz. Apoio técnico em migrações de dados: @felipecduque7.

---

## 1. Resumo Executivo e Critérios de Aceite

Esta entrega implementa o pipeline completo de alimentação institucional do catálogo público de eventos a partir da [Agenda UnB Notícias](https://noticias.unb.br/component/agenda/agendas), abrangendo o adaptador HTTP resiliente, a normalização de datas civis e instantes, o modelo transacional de upsert/conciliação no PostgreSQL, a proteção de edições locais e decisões humanas de moderação, e a exibição de procedência na API e no frontend.

| Critério de Aceite / Cenário | Evidência Técnica e Testes | Resultado |
| --- | --- | --- |
| **1. Execução agendada, duas execuções sucessivas/concorrentes sem duplicatas e atualização de data no mesmo registro** | Workflow `.github/workflows/production-jobs.yml` (`job: collector`), alvos `make events-collect` / `make events-collect-daemon`, índice único `uq_eventos_fonte (fonte, fonte_id)`, lock `pg_try_advisory_lock(708073)` e `pg_advisory_xact_lock`, validados em `test_event_collector.py` e `test_event_collection_database.py` | Aprovado |
| **2. Indisponibilidade da fonte preserva registros, respeito a decisões de moderação/campos editados localmente e cobertura multicampus** | Leitura integral prévia ao bloco transacional, rollback em falha HTTP/timeout com registro em `coletas_eventos` (`status = 'falha'`), trigger `tg_registra_edicao_local` (`campos_editados`), preservação de `moderado_em` e normalização dos 5 campi da UnB | Aprovado |
| **3. Publicação automática de evento completo e retenção em revisão de item ambíguo, incompleto, informe ou possível duplicata, com procedência visível** | RPC `registrar_evento_coletado(jsonb)`, detecção de `00:00` sem sinal explícito como `ambiguo`, distinção `evento` vs `informe`, conciliação de URL manual, similaridade de título/data ($\le 2$ dias) e exposição de `source`/`source_url` em `EventRead` e na interface | Aprovado |

---

## 2. Detalhamento das Evidências

### 2.1. Coletor Periódico, Concorrência, Idempotência e Atualização (Critério 1)

O coletor institucional (`backend/src/modules/events/collector.py`) opera de forma desacoplada do ciclo de requisições HTTP da API FastAPI:

1. **Conformidade de Acesso e Frequência Moderada:**
   - Consulta obrigatória e prévia a `https://noticias.unb.br/robots.txt` via `RobotFileParser` antes de acessar qualquer página (`test_client_checks_robots_before_fetching_events`).
   - Restrição estrita de caminhos permitidos à listagem `/component/agenda/agendas` e aos detalhes `/component/agenda/agenda/{id}` (`test_listing_rejects_invalid_event_identity_and_detail_contract`), sem seguir redirecionamentos (`follow_redirects=False`, `test_client_does_not_follow_redirects`).
   - Intervalo mínimo de `1.0s` entre requisições (`MIN_REQUEST_INTERVAL_SECONDS`), timeout de `20.0s`, limite de tamanho de resposta (`2 MB`), máximo de 100 páginas / 900 eventos e respeito ao cabeçalho `Retry-After` limitado a `60s` (`test_retry_after_is_bounded`).
2. **Execuções Sucessivas e Atualização no Mesmo Registro:**
   - A chave única parcial `uq_eventos_fonte ON public.eventos (fonte, fonte_id) WHERE fonte IS NOT NULL` garante que o mesmo item da origem nunca gere duplicatas.
   - Na 1ª coleta de um evento completo, `registrar_evento_coletado` retorna `acao = 'criado'`.
   - Na 2ª coleta sucessiva com o mesmo conteúdo (mesmo SHA-256 canônico em `fonte_hash`), retorna `acao = 'inalterado'` e apenas atualiza o carimbo `coletado_em`.
   - Quando a data ou horário sofrem alteração na fonte (`fonte_hash` distinto), a função atualiza **o mesmo registro** (`id` preservado, `acao = 'atualizado'`), mantendo os vínculos dos usuários em `eventos_salvos` (`test_successive_collections_update_the_same_record` e `test_collect_events_successive_runs_and_date_update_on_same_record`).
3. **Execuções Concorrentes:**
   - No nível do processo coletor, `collect_events` adquire `pg_try_advisory_lock(708073)`. Uma segunda instância disparada simultaneamente recebe `{"status": "ignorada", "erro": "coleta_em_andamento"}` e encerra imediatamente sem tocar nas tabelas (`test_collect_events_rejects_concurrent_execution_when_advisory_lock_is_held`).
   - No nível do banco de dados, `registrar_evento_coletado` também executa `pg_advisory_xact_lock(hashtextextended(v_fonte || ':' || v_fonte_id, 0))` combinado com `SELECT ... FOR UPDATE`, serializando escritas concorrentes no mesmo item.
4. **Agendamento e Automação:**
   - **Ambiente Hospedado (GitHub Actions):** Job `collector` configurado em `.github/workflows/production-jobs.yml` com disparo agendado diário (`cron: '27 10 * * *'`, 07h27 BRT), disparo manual (`workflow_dispatch`) e grupo de concorrência exclusivo (`concurrency: production-event-collector`).
   - **Execução Local / CLI:** Alvos `make events-collect` (execução única) e `make events-collect-daemon` (`--daemon` com intervalo padrão de 6h ou `--interval-hours <h>`), validados em `test_cli_arguments_support_single_run_interval_and_daemon_flag`.

### 2.2. Resiliência a Indisponibilidade, Edições Locais, Moderação e Multicampus (Critério 2)

1. **Preservação de Registros em Falha da Fonte:**
   - O coletor carrega e normaliza todas as páginas antes de abrir a transação de escrita e **nunca executa `DELETE`** sobre eventos que deixaram de aparecer na listagem.
   - Se a fonte estiver indisponível (timeout, erro de rede ou HTTP 503), nenhuma alteração parcial é aplicada aos eventos existentes e a execução é registrada em `public.coletas_eventos` com `status = 'falha'` e código sanitizado curto (`erro_codigo = 'http_503'` ou `'origem_indisponivel'`), sem armazenar HTML bruto (`test_collect_events_preserves_existing_records_when_source_is_unavailable`).
   - Se uma página da fonte sofrer degradação parcial e deixar de informar a data de um evento já publicado, `registrar_evento_coletado` preserva a `data_evento` anteriormente conhecida sem rebaixar o evento (`test_source_failure_keeps_known_data`).
2. **Respeito a Campos Editados Localmente:**
   - O trigger `tg_registra_edicao_local` monitora `UPDATE` em `public.eventos` fora da coleta (`current_setting('agenda.coleta', true) <> '1'`) e adiciona automaticamente os campos alterados ao array `campos_editados` (`titulo`, `descricao`, `datas`, `local`, `link`, `campus`, `categoria`).
   - Em coletas futuras com hash novo, `registrar_evento_coletado` atualiza apenas os campos não listados em `campos_editados`, preservando integralmente as edições locais (`test_local_edits_survive_new_collections`).
3. **Respeito às Decisões Humanas de Moderação:**
   - A RPC `moderar_sugestao(p_evento_id, p_status, p_justificativa)` grava `moderado_por = auth.uid()` e `moderado_em = now()`.
   - Quando `moderado_em IS NOT NULL`, novas execuções do coletor mantêm o `status` decidido pelo moderador (`aprovado` ou `rejeitado`), impedindo que uma atualização na fonte reabra ou publique um item já rejeitado (`test_moderation_decisions_are_never_undone_by_collection`).
4. **Cobertura Multicampus (RF15):**
   - A função `_normalize_campus` em `collector.py` mapeia os locais extraídos para os 5 campi oficiais cadastrados no seed do banco (`test_multicampus_normalization_coverage`):
     - `Darcy Ribeiro (Plano Piloto)` (incluindo menções a ICC, Reitoria, Beijódromo, Pompeu de Sousa, Memorial Darcy Ribeiro, Asa Norte);
     - `Faculdade do Gama (FCTE)`;
     - `Faculdade de Ceilândia (FCTS)`;
     - `Faculdade de Planaltina (FUP)`;
     - `Fazenda Água Limpa (FAL)`.
   - Quando o local é externo aos campi (ex.: `"Praça dos Três Poderes"`), `campus` permanece `None` (sem inferência forçada), preservando o texto integral em `localizacao`.

### 2.3. Publicação Automática, Fila de Revisão, Deduplicação e Procedência (Critério 3)

1. **Datas Civis, Dia Inteiro e Tratamento de `00:00` (ADR-011 / RF14):**
   - Eventos de dia inteiro só são classificados como `dia_inteiro = true` quando há marcador explícito na fonte (`"dia inteiro"`, `"dia todo"`, `"todo o dia"`, `"horário integral"` ou classe CSS `.dia-inteiro`/`.all-day`), gerando `data_inicio_civil` e `data_fim_civil` com **fim exclusivo** (`test_explicit_all_day_formats_are_detected_with_exclusive_end` e `test_all_day_collected_event`).
   - Quando a fonte traz `00:00` ou `00:00:00` sem indicação explícita de dia inteiro (valor de preenchimento comum no Joomla), o coletor **não inventa horário nem converte em dia inteiro**: omite `inicio` e marca `ambiguo = true`, encaminhando o item para revisão (`test_zero_midnight_is_not_invented_as_event_start_or_all_day` e `test_zero_time_without_explicit_signal_remains_ambiguous_for_review`).
2. **Distinção entre Eventos e Informes:**
   - Apenas as categorias institucionais `Eventos`, `Cursos` e `Defesas` são classificadas como `tipo = 'evento'`; demais categorias (`Informes`, `Editais`, `Pesquisas`, etc.) recebem `tipo = 'informe'` e aguardam revisão com `motivo_revisao = 'informe'` (`test_only_known_event_categories_are_published_automatically`).
3. **Conciliação de URL Manual e Detecção de Possíveis Duplicatas:**
   - **Conciliação por URL idêntica:** Se um evento já foi cadastrado manualmente na plataforma (`fonte IS NULL`) com `link_externo` igual à `fonte_url` ou ao `link_externo` do item coletado, o banco não cria outro registro: anexa a procedência ao evento manual (`acao = 'conciliado'`) e protege todos os seus campos em `campos_editados` (`test_manual_event_with_the_same_url_is_reconciled`).
   - **Similaridade de título e data:** `check_potential_duplicate` e `find_existing_duplicate` comparam títulos normalizados em janela de até $\pm 2$ dias ($\ge 0{,}80$ no mesmo dia, $\ge 0{,}85$ em 1 dia e $\ge 0{,}92$ em 2 dias), preservando números distintivos (`"Cálculo 1"` vs `"Cálculo 2"`) para evitar falsos positivos. Quando detectada, o item entra com `status = 'pendente'`, `motivo_revisao = 'possivel_duplicata'` e `possivel_duplicata_de` apontando para o evento existente (`test_duplicate_similarity_detection_positive_and_negative_cases`, `test_similar_title_on_the_same_day_goes_to_review` e `test_find_existing_duplicate_detects_similar_title_within_two_days`).
4. **Procedência Visível (RF16):**
   - O schema público `EventRead` (`backend/src/modules/events/schemas.py`) expõe `source`, `source_url`, `all_day`, `start_date` e `end_date`, omitindo metadados operacionais (`fonte_hash`, `coletado_em`, `motivo_revisao`, `campos_editados`), conforme validado em `test_public_event_exposes_provenance_without_internal_metadata`.
   - No frontend, `toUiEvent` (`frontend/src/lib/publicEventsCache.js`) mapeia `fonte` e `fonteUrl`, `SecondPage.jsx` exibe a tag `UnB Notícias` nos cards e `PaginaDeEvento.jsx` renderiza o selo `Origem institucional: Agenda UnB Notícias` com link externo seguro (`rel="noopener noreferrer"`).

---

## 3. Revisão Técnica de Contratos, Permissões e Dados Afetados

- **Revisão de código e contratos:** Revisado por @marrathomaz e @pontesluis (apoio de schema por @felipecduque7).
- **Contratos afetados:**
  - `GET /api/v1/events`, `GET /api/v1/events/{event_id}` e `GET /api/v1/me/saved-events`: adição compatível e retrocompatível dos campos opcionais `ends_at`, `all_day`, `start_date`, `end_date`, `source` e `source_url` no modelo `EventRead`.
  - RPCs Supabase: `public.registrar_evento_coletado(jsonb)` (exclusiva de `service_role`/servidor), `public.listar_revisoes_coleta(text, integer)` e `public.moderar_sugestao(uuid, text, text)` (restritas a `authenticated` com verificação `public.is_event_moderator()`).
- **Permissões e Segurança (RLS / Triggers):**
  - `public.coletas_eventos` possui RLS habilitado e `REVOKE ALL FROM anon, authenticated`, sendo inacessível pelo navegador.
  - O trigger `tg_protege_procedencia` bloqueia com SQLSTATE `42501` qualquer tentativa de `anon` ou `authenticated` (inclusive `admin` via cliente web) de inserir ou alterar `fonte`, `fonte_id`, `fonte_url`, `fonte_tipo`, `fonte_hash`, `coletado_em`, `motivo_revisao`, `possivel_duplicata_de`, `moderado_por`, `moderado_em` ou `campos_editados` (`test_browser_cannot_collect_or_forge_provenance`).
  - Links externos com esquemas inseguros (ex.: `javascript:alert(1)`) são descartados tanto no coletor quanto na função SQL (`test_unsafe_link_is_dropped_instead_of_published`).
- **Dados e Tabelas Afetadas (`supabase/migrations/20261111140000_eventos_datas_e_coleta.sql`):**
  - `public.eventos`: adição de colunas de intervalo/dia inteiro (`data_fim`, `dia_inteiro`, `data_inicio_civil`, `data_fim_civil`) e de procedência/revisão (`fonte`, `fonte_id`, `fonte_url`, `fonte_tipo`, `fonte_hash`, `coletado_em`, `campos_editados`, `motivo_revisao`, `possivel_duplicata_de`, `moderado_por`, `moderado_em`), `autor_id` e `data_evento` anuláveis sob constraints `eventos_autor_ou_fonte`, `eventos_fonte_completa` e `eventos_publicado_tem_data`.
  - `public.eventos_pessoais`: adição de `data_fim`, `dia_inteiro`, `data_inicio_civil` e `data_fim_civil` com constraint `eventos_pessoais_dia_inteiro_coerente`.
  - `public.coletas_eventos`: nova tabela de auditoria operacional de execuções do coletor.

---

## 4. Execução das Suítes Automatizadas e Pendências Abertas

### 4.1. Resultados dos Testes

- **Coletor e Regras de Normalização/Orquestração (`backend/tests/test_event_collector.py`):** **34 aprovados** (listagem paginada, `robots.txt`, bloqueio de redirects, normalização de horários e `00:00`, dia inteiro explícito, 5 campi, cálculo de similaridade, lock concorrente, coletas sucessivas, atualização de data, preservação em HTTP 503 e CLI `--daemon`).
- **Contrato da API de Eventos (`backend/tests/test_events_api.py`):** **10 aprovados** (incluindo exposição de `source` e `source_url` e omissão de campos internos).
- **Integração PostgreSQL, RLS e RPCs (`backend/tests/test_event_collection_database.py`):** **18 cenários implementados** e integrados ao `.github/workflows/supabase-ci.yml`.
- **Cache e Transformação no Frontend (`frontend/src/lib/publicEventsCache.test.js`):** **4 suítes aprovadas** (37 testes no total em `frontend/src/lib/*.test.js`), validando `toUiEvent` para eventos com horário, dia inteiro e procedência institucional.

### 4.2. Falhas / Pendências Abertas Identificadas para Rastreabilidade

1. **Integração da fila `listar_revisoes_coleta` na interface de moderação ([S8-F02 / Issue #80](https://github.com/unb-mds/2026-2-AgendaUnB/issues/80)):**
   - No banco de dados, a fila `public.listar_revisoes_coleta` e a decisão via `public.moderar_sugestao` já estão prontas e testadas. Na interface React (`frontend/src/lib/moderation.js`), o painel atual consulta `listar_sugestoes` (voltado às sugestões estudantis), ficando o consumo visual de `listar_revisoes_coleta` na tela de moderação vinculado à issue **#80 (`S8-F02 - Fechar eventos, moderação, agenda e melhorias de uso`)**, responsável `@Bielziin07` / `@marrathomaz`.
2. **Habilitação da variável `PRODUCTION_EVENT_COLLECTION_ENABLED` após merge em `main` ([S7-B06 / Issue #76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)):**
   - O workflow `.github/workflows/production-jobs.yml` já contém o job `collector` configurado para rodar diariamente às 07h27 BRT e por `workflow_dispatch`. A ativação da variável `PRODUCTION_EVENT_COLLECTION_ENABLED=true` no environment `production-jobs` ocorre após a promoção da branch para `main`, sob coordenação de `@pontesluis`.
