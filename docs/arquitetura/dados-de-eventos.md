---
title: "Dados de eventos: datas, coleta e lembretes"
description: "Funcionamento da semântica de datas e intervalos, do coletor institucional da Agenda UnB Notícias e dos lembretes persistentes."
---

Especificação operacional das estruturas de datas, coleta institucional de eventos e lembretes automáticos da agenda. Todas as regras de integridade, deduplicação e acesso são aplicadas no PostgreSQL por chaves únicas, triggers e funções, independentemente do caminho de escrita.

## 1. Datas e intervalos ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes))

`eventos` e `eventos_pessoais` utilizam `data_fim`, `dia_inteiro`, `data_inicio_civil` e `data_fim_civil`. O término de qualquer intervalo é sempre **exclusivo**.

| Tipo | O que gravar | O que o banco preenche |
| --- | --- | --- |
| Com horário (`all_day = false`) | `data_evento`/`data_hora` (instante com fuso) e `data_fim` opcional | — |
| Dia inteiro (`all_day = true`) | `dia_inteiro = true`, `data_inicio_civil`, `data_fim_civil` | `data_evento`/`data_hora` e `data_fim` como meia-noite de `America/Sao_Paulo` das datas civis |

Um evento de 18 a 20/11 inclusive utiliza `data_inicio_civil = 2026-11-18` e `data_fim_civil = 2026-11-21`. Um evento de um único dia utiliza início 18 e fim 19. O banco recusa término menor ou igual ao início, dia inteiro sem datas civis e data civil em evento com horário.

Como eventos de dia inteiro também têm início normalizado em `TIMESTAMPTZ`, ordenação e filtros por interseção funcionam de forma uniforme. **Na resposta da API, eventos de dia inteiro retornam `all_day: true`, `start_date` e `end_date`**, evitando deslocamento de data civil em navegadores fora de `-03:00`. Registros legados com `00:00` não são convertidos automaticamente para dia inteiro.

## 2. Coleta institucional da Agenda UnB Notícias

### Contrato de ingestão por item

```python
import json
from sqlalchemy import text

def registrar_item(db, item: dict) -> dict:
    """Devolve {"id", "acao", "status", "motivo_revisao"}."""
    return db.execute(
        text("select public.registrar_evento_coletado(cast(:p as jsonb))"),
        {"p": json.dumps(item)},
    ).scalar_one()
```

| Campo | Obrigatório | Observação |
| --- | --- | --- |
| `fonte` | Sim | `agenda_unb_noticias` |
| `fonte_id` | Sim | Identificador canônico do item na fonte; forma com `fonte` a chave única de upsert |
| `fonte_url` | Sim | URL canônica do item em `http(s)` |
| `hash` | Sim | SHA-256 do conteúdo normalizado (título, descrição, datas, local e link) |
| `titulo` | Sim | Mínimo de 3 caracteres; truncado em 200 |
| `tipo` | Não | `evento` (padrão) ou `informe` |
| `descricao`, `local`, `link_externo` | Não | Links fora de `http(s)` são descartados sem interromper a coleta |
| `inicio`, `fim` | Não | ISO 8601 **com fuso** (ex.: `2026-11-18T14:00:00-03:00`); sem fuso a função recusa |
| `dia_inteiro`, `data_inicio`, `data_fim` | Não | `data_fim` exclusivo; quando omitido, assume 1 dia |
| `campus`, `categoria` | Não | Nome exato em `campus.nome`/`categories.nome`; valor desconhecido fica nulo |
| `ambiguo` | Não | `true` quando a extração detecta incerteza de data ou horário |

### Decisão de publicação, conciliação e revisão

| Situação | `acao` | Resultado |
| --- | --- | --- |
| Item novo, completo e inequívoco | `criado` | Publicado (`aprovado`) |
| Item novo sem data | `criado` | Encaminhado à revisão (`motivo_revisao = 'incompleto'`) |
| `ambiguo = true` ou término anterior ao início | `criado` | Encaminhado à revisão (`motivo_revisao = 'ambiguo'`) |
| `tipo = 'informe'` | `criado` | Encaminhado à revisão (`motivo_revisao = 'informe'`) |
| Título semelhante próximo em data | `criado` | Encaminhado à revisão (`motivo_revisao = 'possivel_duplicata'`, com `possivel_duplicata_de`) |
| Mesma URL de evento já cadastrado manualmente | `conciliado` | Mantém o evento existente e anexa procedência sem duplicar |
| Mesmo `(fonte, fonte_id)` e mesmo hash | `inalterado` | Atualiza apenas `coletado_em` |
| Mesmo `(fonte, fonte_id)` e hash diferente | `atualizado` | Atualiza o mesmo registro preservando edições locais e moderação |

#### Regra de detecção de possíveis duplicatas
1. **Normalização:** títulos passam por conversão para minúsculas, remoção de acentuação (`NFKD`), eliminação de pontuação e colapso de espaços.
2. **Cálculo de similaridade:** combina razão de sequência (`SequenceMatcher`), sobreposição Jaccard de tokens e contenção de substring com limiares progressivos ($\ge 0{,}80$ na mesma data, $\ge 0{,}85$ em 1 dia de diferença e $\ge 0{,}92$ em 2 dias de diferença).
3. **Preservação de edições/números:** títulos com números distintos (ex.: `"Cálculo 1"` vs `"Cálculo 2"`, ou `"Encontro 2025"` vs `"Encontro 2026"`) não são marcados como duplicata.
4. **Proximidade temporal:** janela máxima de $\le 2$ dias de diferença.
5. **Encaminhamento:** possíveis duplicatas ficam com `status = 'pendente'`, `motivo_revisao = 'possivel_duplicata'` e referência em `possivel_duplicata_de` para decisão humana.

Em atualizações subsequentes, o banco preserva:
- **campos editados localmente** (registrados em `campos_editados` pelo trigger `eventos_registra_edicao_local`);
- **decisões de moderação** (`moderado_em` preenchido impede alteração automática de `status`);
- **suspeita de duplicata** enquanto não houver decisão humana;
- **data conhecida**, quando a fonte externa deixa de informá-la.

Execuções simultâneas são serializadas por `pg_advisory_xact_lock` e índice único `(fonte, fonte_id)`.

### Adaptador e execução em background

O adaptador está em `backend/src/modules/events/collector.py`. A origem é fixa em `https://noticias.unb.br`:

- Consulta `robots.txt` e acessa apenas `/component/agenda/agendas` e `/component/agenda/agenda/{id}` quando permitidos, com `User-Agent` identificável (RNF11).
- Não segue redirecionamentos, não usa cookies nem proxy de ambiente, aplica timeout de 20 segundos, espera mínima de 1 segundo entre requisições e até uma repetição para falhas transitórias respeitando `Retry-After` até 60 segundos.
- Carrega e valida toda a listagem e detalhes antes de abrir o bloco de gravação transacional (limitado a 100 páginas / 900 eventos por rodada), evitando gravações parciais em falha da fonte. Um `pg_try_advisory_lock` impede execuções concorrentes do coletor.
- Nunca remove eventos existentes que deixaram de constar na listagem da fonte.
- Locais identificados nos campi da UnB são normalizados para os cinco nomes oficiais: `Darcy Ribeiro (Plano Piloto)`, `FCTE (Gama)`, `FCTS (Ceilândia)`, `FUP (Planaltina)` e `FAL`.
- Sinais explícitos (`"dia inteiro"`, `"integral"`, `"o dia todo"`, `"jornada inteira"`) geram `dia_inteiro: true`; horários `00:00` sem sinal explícito são encaminhados com `ambiguo: true` à revisão ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)).
- Execuções são registradas em `coletas_eventos` usando apenas `erro_codigo` curto (até 60 caracteres), sem armazenar HTML ou respostas brutas.

**Modos de execução:**
1. **Makefile:** `make events-collect` (rodada única) e `make events-collect-daemon` (loop contínuo local).
2. **CLI direto (`backend/`):** `python -m src.modules.events.collector`, `--interval-hours <h>` (mínimo 1 hora) ou `--daemon`.
3. **GitHub Actions:** job `collector` em `.github/workflows/production-jobs.yml`, agendado diariamente às 07h27 BRT (`27 10 * * *`) e disponível sob demanda via `workflow_dispatch`, habilitado por `PRODUCTION_EVENT_COLLECTION_ENABLED = 'true'` e segredo `DATABASE_URL` no ambiente `production-jobs`.

### Revisão e procedência visível (RF16)

- **Revisão (`listar_revisoes_coleta` / `moderar_sugestao`):** professores e administradores consultam itens coletados em `/sugestoes` (paginação de 20 itens, exibindo `fonte_url`, `motivo_revisao` e `possivel_duplicata_de`) e decidem aprovação ou recusa justificada. Itens sem data não podem ser publicados.
- **Exposição pública:** a API (`/api/v1/events`) expõe `source` (`"agenda_unb_noticias"`), `source_url`, `all_day`, `start_date` e `end_date` em `EventRead`, mantendo metadados internos (`fonte_hash`, `coletado_em`, `motivo_revisao`, `campos_editados`) restritos ao backend. No frontend, `/evento/:id` e os cards de `/eventos` exibem o selo de procedência institucional e o link para a publicação original.

## 3. Lembretes persistentes ([ADR-013](/arquitetura/adrs/adr-013-lembretes-persistentes)) {#3-lembretes}

A tabela `lembretes` é mantida exclusivamente por triggers no PostgreSQL, sem lógica de agendamento na API:

| Acontecimento | Efeito em `lembretes` |
| --- | --- |
| Compromisso criado ou evento público salvo faltando mais de 24 h | Cria aviso `pendente` agendado para 24 h antes do início |
| Entrada na agenda faltando 24 h ou menos | Sem aviso (não gera alerta retroativo) |
| Data de início alterada | Atualiza o aviso `pendente` para o novo horário |
| Compromisso excluído, vínculo removido, evento rejeitado ou sem data | Cancela o aviso `pendente` |
| Evento volta ao catálogo aprovado | Reagenda aviso para quem manteve o vínculo salvo |
| Conta excluída | Remove todos os avisos em cascata |

Para eventos de dia inteiro, o início de referência é a meia-noite de `America/Sao_Paulo` do primeiro dia civil, agendando o aviso para a meia-noite do dia anterior.

### Agendador (`pg_cron`) {#agendador-pg_cron}

O Supabase Cron (`pg_cron`) executa `public.disparar_lembretes()` a cada cinco minutos diretamente no banco, mantendo os disparos ativos mesmo com API e navegador fechados. O arquivo versionado `supabase/snippets/habilitar_lembretes.sql` registra de forma idempotente o job `agenda-unb-lembretes`.

A função `disparar_lembretes()` usa `FOR UPDATE SKIP LOCKED`, revalida a existência do evento e do vínculo antes de marcar `status = 'disparado'`, processa cada aviso uma única vez e descarta pendências cujo evento já iniciou. Em caso de incidente operacional, o agendamento pode ser pausado via `select cron.unschedule('agenda-unb-lembretes')`.

### Central de avisos

| Contrato HTTP | Comportamento |
| --- | --- |
| `GET /api/v1/me/reminders` | Lista avisos `disparado` da conta autenticada, ordenados por `fired_at desc, id desc` |
| `PUT /api/v1/me/reminders/{id}/read` | Marca leitura preservando o primeiro `read_at` (`404` para IDs alheios, pendentes ou inexistentes) |

O componente `NotificationBell` abre os lembretes para qualquer conta autenticada na barra de navegação e inclui a aba **Sugestões** para contas com papel `student`. Consulte os parâmetros e respostas em [Lembretes da agenda](/api-specs#lembretes-da-agenda).

## 4. Matriz de permissões

| Recurso | Visitante | Conta autenticada | Professor / admin | Servidor |
| --- | --- | --- | --- | --- |
| `registrar_evento_coletado` | Não | Não | Não | Sim |
| Colunas de procedência e moderação em `eventos` | Não grava | Não grava | Apenas via RPCs | Sim |
| `coletas_eventos` | Sem acesso | Sem acesso | Sem acesso | Sim |
| `listar_revisoes_coleta`, `moderar_sugestao` | Não | Recusado | Sim | Sim |
| `disparar_lembretes` | Não | Não | Não | Sim |
| `lembretes` | Sem acesso | Lê os próprios disparados e marca leitura | Mesmas regras de destinatário | Sim |

## 5. Verificação automatizada

- **Coletor e API de eventos:** `backend/tests/test_event_collector.py`, `backend/tests/test_events_api.py` e `backend/tests/test_event_collection_database.py` (PostgreSQL local).
- **Lembretes:** `backend/tests/test_reminders_api.py`, `backend/tests/test_reminders_database.py` (PostgreSQL local) e `frontend/tests/reminders.spec.js` (Playwright).
- **Projeção no frontend:** `frontend/tests/` e `frontend/src/lib/*.test.js`.
