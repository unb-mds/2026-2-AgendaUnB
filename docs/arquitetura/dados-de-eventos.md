---
title: "Dados de eventos: datas, coleta e lembretes"
description: "Como a API, o coletor e o agendador usam as estruturas de eventos da Release 2."
---

Guia de integração das migrações de datas, coleta e lembretes. A tabela resume o que as migrações entregam e as etapas pendentes de operação.

| Issue | O que o banco já faz | O que falta na aplicação |
| --- | --- | --- |
| [S7-B05 (#75)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75) | Upsert por origem, decisão publicar/revisar, conciliação por URL, proteção de edições locais e de decisões de moderação, registro das execuções | Configurar e homologar a execução recorrente no ambiente hospedado; registrar as evidências operacionais da issue |
| [S8-B03 (#81)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81) | Agendar, trocar, cancelar e disparar avisos com unicidade por conta e início | Homologar o Supabase Cron, a API e a central no ambiente hospedado |

As chaves únicas, os gatilhos e as funções aplicam as regras a todos os caminhos de escrita. O destinatário pode registrar a leitura do próprio aviso disparado.

## 1. Datas (ADR-011)

`eventos` e `eventos_pessoais` ganharam `data_fim`, `dia_inteiro`, `data_inicio_civil` e `data_fim_civil`. O fim é sempre **exclusivo**.

| Tipo | O que gravar | O que o banco preenche |
| --- | --- | --- |
| Com horário | `data_evento`/`data_hora` (instante) e, se houver, `data_fim` | — |
| Dia inteiro | `dia_inteiro = true`, `data_inicio_civil`, `data_fim_civil` | Início e fim como meia-noite de Brasília dos dias civis |

Um evento de 18 a 20/11 inclusive é `data_inicio_civil = 2026-11-18` e `data_fim_civil = 2026-11-21`. Um único dia é início 18 e fim 19. O banco recusa fim menor ou igual ao início, dia inteiro sem as datas civis e data civil em evento com horário.

Como o início de dia inteiro também é preenchido como instante, ordenar e filtrar por `data_evento`/`data_hora` continua funcionando para os dois tipos. **Na resposta da API, um dia inteiro deve sair como `start_date`/`end_date`**, não como o instante: quem está em outro fuso veria o dia errado.

No ORM: `ends_at`, `all_day`, `start_date` e `end_date` em `PublicEvent` e `PersonalEvent`. Registros antigos não foram reclassificados: `00:00` em um evento legado não prova dia inteiro.

## 2. Coleta da Agenda UnB Notícias (#75)

### Uma chamada por item

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
| `fonte` | sim | `agenda_unb_noticias` |
| `fonte_id` | sim | Identificador canônico do item na fonte. Com `fonte`, é a chave do upsert |
| `fonte_url` | sim | URL canônica do item, `http(s)` |
| `hash` | sim | SHA-256 do conteúdo **normalizado** (título, descrição, datas, local, link). Hash igual = nada mudou |
| `titulo` | sim | Mínimo de 3 caracteres; cortado em 200 |
| `tipo` | não | `evento` (padrão) ou `informe` |
| `descricao`, `local`, `link_externo` | não | Link fora de `http(s)` é descartado, sem derrubar a coleta |
| `inicio`, `fim` | não | ISO 8601 **com fuso** (`2026-11-18T14:00:00-03:00`). Sem fuso a função recusa |
| `dia_inteiro`, `data_inicio`, `data_fim` | não | `data_fim` exclusivo; se omitido, vale um dia |
| `campus`, `categoria` | não | Nome exato de `campus.nome`/`categories.nome`; desconhecido fica nulo |
| `ambiguo` | não | `true` quando o coletor não tem certeza da data ou do horário |

### O que a função decide

| Situação | `acao` | Resultado |
| --- | --- | --- |
| Item novo, completo e inequívoco | `criado` | Publicado (`aprovado`) |
| Item novo sem data | `criado` | Revisão, `incompleto` |
| `ambiguo = true` ou fim antes do início | `criado` | Revisão, `ambiguo` |
| `tipo = informe` | `criado` | Revisão, `informe` |
| Título semelhante ($\ge 80\%$ no mesmo dia, $\ge 85\%$ em 1 dia ou $\ge 92\%$ em 2 dias) | `criado` | Revisão, `possivel_duplicata`, com `possivel_duplicata_de` |
| Mesma URL de um evento cadastrado na plataforma | `conciliado` | Mantém o evento manual e anexa a procedência; não cria outro |
| Mesmo `(fonte, fonte_id)` e mesmo hash | `inalterado` | Só renova `coletado_em` |
| Mesmo `(fonte, fonte_id)`, hash diferente | `atualizado` | Atualiza **o mesmo registro** |

#### Regra de Detecção de Possíveis Duplicatas
Para evitar publicação duplicada de eventos com grafias ligeiramente distintas ou datas aproximadas:
1. **Normalização**: títulos passam por conversão para minúsculas, remoção de acentuação (`NFKD`), eliminação de pontuação e colapso de espaços em branco.
2. **Cálculo de Similaridade**: combina razão de sequência (`SequenceMatcher`), sobreposição Jaccard de tokens e contenção de substring (limiares progressivos: $\ge 0{,}80$ para mesma data, $\ge 0{,}85$ para 1 dia de diferença e $\ge 0{,}92$ para 2 dias de diferença).
3. **Preservação de Dígitos/Edições**: títulos que possuam números distintos (ex.: `"Cálculo 1"` vs `"Cálculo 2"`, ou `"Encontro 2025"` vs `"Encontro 2026"`) **não** são considerados duplicatas, prevenindo falsos positivos.
4. **Proximidade Temporal**: datas de início devem coincidir no mesmo dia ou diferir em no máximo 2 dias ($\le 2$ dias de afastamento).
5. **Encaminhamento**: quando uma possível duplicata é detectada, o registro é salvo com `status = 'pendente'`, `motivo_revisao = 'possivel_duplicata'` e `possivel_duplicata_de = <id_candidato>`, permitindo decisão por moderador humano sem falso auto-descarte.

Em uma atualização, a função preserva:

- **campos editados na plataforma.** O banco registra em `campos_editados` qualquer alteração feita fora da coleta (`titulo`, `descricao`, `datas`, `local`, `link`, `campus`, `categoria`). Esses campos não são sobrescritos;
- **decisões de moderação.** Depois que uma pessoa aprova ou rejeita (`moderado_em` preenchido), a coleta não muda o status;
- **suspeita de duplicata**, até alguém decidir;
- **a data conhecida**, quando a fonte deixa de informá-la (página alterada ou leitura parcial).

Duas execuções simultâneas do mesmo item são serializadas (`pg_advisory_xact_lock` + chave única `(fonte, fonte_id)`).

### Esqueleto do coletor

```python
def executar_coleta(db, itens):
    run_id = db.execute(text(
        "insert into public.coletas_eventos(fonte) values ('agenda_unb_noticias') returning id"
    )).scalar_one()
    db.commit()
    contagem = {"criado": 0, "atualizado": 0, "inalterado": 0, "conciliado": 0}
    lidos = revisao = 0
    try:
        for item in itens:                      # itens já normalizados
            resultado = registrar_item(db, item)
            db.commit()                         # um item por transação
            lidos += 1
            contagem[resultado["acao"]] += 1
            # itens que ENTRARAM na fila de revisão nesta execução
            revisao += resultado["acao"] == "criado" and resultado["status"] == "pendente"
        status, erro = "concluida", None
    except FonteIndisponivel as exc:            # exceção do próprio coletor
        db.rollback()
        status, erro = "falha", exc.codigo      # ex.: "http_503", "timeout"
    db.execute(text("""
        update public.coletas_eventos
           set status = :s, concluida_em = now(), erro_codigo = :e, itens_lidos = :l,
               criados = :c, atualizados = :a, inalterados = :i, conciliados = :k, para_revisao = :r
         where id = :id"""),
        {"s": status, "e": erro, "l": lidos, "c": contagem["criado"], "a": contagem["atualizado"],
         "i": contagem["inalterado"], "k": contagem["conciliado"], "r": revisao, "id": run_id})
    db.commit()
```

Pontos de atenção para o coletor:

- **Falha da fonte não apaga nada.** A função só cria ou atualiza. Não remova eventos que "sumiram" da listagem.
- **Detecção de dia inteiro vs `00:00`:** O coletor inspeciona a marcação e texto da fonte por termos explícitos (`"dia inteiro"`, `"integral"`, `"o dia todo"`, `"jornada inteira"`). Quando o sinal explícito existe, emite `dia_inteiro: True` com datas civis (`data_inicio` e `data_fim` exclusivo). Se a fonte contiver apenas `00:00` sem indicativo explícito de dia inteiro, **não** assume dia inteiro; emite o instante com `ambiguo: True`, encaminhando o item à moderação conforme a ADR-011.
- **Normalização multicampus:** Locais identificados como pertencentes aos campi Darcy Ribeiro (ICC, Reitoria, Beijódromo, BSAN, CDT), FCTE (Gama), FCTS (Ceilândia), FUP (Planaltina) ou FAL são normalizados com o nome exato do campus no banco.
- **`erro_codigo` é um código curto** (até 60 caracteres). Nunca grave HTML, corpo de resposta ou conteúdo da fonte.
- **Frequência moderada**, com `User-Agent` identificável e respeito a `robots.txt` (RNF11).
- O hash deve ser estável: normalize espaços e ordem dos campos antes de calcular, para que a mesma página gere o mesmo hash.

### Revisão por professor e admin

`listar_revisoes_coleta(p_status, p_offset)` devolve `{"items": [...], "total": n}` com 20 itens por página, incluindo `fonte_url`, `motivo_revisao` e `possivel_duplicata_de`. A decisão usa a RPC que já existe, `moderar_sugestao(evento_id, 'aprovado' | 'rejeitado', justificativa)`, que agora também aceita itens coletados e registra `moderado_por` e `moderado_em`. Item sem data não pode ser aprovado.

### Procedência visível (RF16)

Eventos coletados expõem institucionalmente a sua procedência:
- Na API pública (`/api/v1/events`), os contratos (`EventRead`) expõem os campos `source` (`"agenda_unb_noticias"`) e `source_url` (link HTTPS canônico), além de `all_day`, `start_date` e `end_date`. Metadados internos como `fonte_hash`, `coletado_em` e `motivo_revisao` permanecem estritamente privados no backend.
- Na interface frontend, `PaginaDeEvento.jsx` exibe o box de procedência institucional com link direto para a publicação original na Agenda UnB Notícias e atribui o organizador institucional quando `autor_id` for ausente. Nos cards de listagem (`SecondPage.jsx`), é exibida a badge informativa de origem.

## 3. Lembretes (#81, ADR-013)

A tabela `lembretes` é mantida por triggers. A API **não cria nem cancela** avisos:

| Acontecimento | Efeito |
| --- | --- |
| Compromisso criado ou evento público salvo, faltando mais de 24 h | Aviso `pendente` para 24 h antes do início |
| Entrou na agenda faltando 24 h ou menos | Sem aviso (não há alerta retroativo) |
| Início alterado | Aviso pendente trocado pelo novo horário |
| Compromisso excluído, vínculo removido, evento rejeitado ou sem data | Aviso pendente cancelado |
| Evento volta ao catálogo | Aviso reagendado para quem o mantém salvo |
| Conta excluída | Avisos removidos |

Para dia inteiro, o início é a meia-noite de Brasília do primeiro dia, então o aviso sai à meia-noite do dia anterior.

### Agendador

O Supabase Cron (`pg_cron`) executa `public.disparar_lembretes()` a cada cinco minutos. A pendência fica elegível 24 h antes e aparece na próxima execução que a processar. A tabela guarda as pendências e o job roda no PostgreSQL mesmo com a API e o navegador fechados.

Após aplicar as migrações da #81, execute o arquivo versionado `supabase/snippets/habilitar_lembretes.sql` como `postgres` no projeto Supabase do ambiente alvo. O arquivo verifica a função, habilita a extensão se necessário e registra o job de nome `agenda-unb-lembretes`. Reexecutar o arquivo no mesmo projeto com o mesmo papel mantém um único job. Valide primeiro no banco de homologação com contas e eventos sintéticos.

Para testar manualmente e acompanhar o histórico no ambiente em validação, execute estas consultas.

```sql
select public.disparar_lembretes(); -- quantidade de avisos disparados nesta chamada

select jobid, schedule, active
from cron.job where jobname = 'agenda-unb-lembretes';

select r.start_time, r.end_time, r.status, r.return_message
from cron.job_run_details r
join cron.job j on j.jobid = r.jobid
where j.jobname = 'agenda-unb-lembretes'
order by r.runid desc
limit 20;
```

Em incidente, execute `select cron.unschedule('agenda-unb-lembretes')` como o dono do job. As pendências e leituras permanecem na tabela. Confira a compatibilidade do schema antes de reativar com o mesmo arquivo. O disparo revalida o evento e o vínculo, retoma pendências elegíveis antes do início e descarta pendências após o início. A chave de unicidade contém conta, tipo e ID do evento e início de referência. A antecedência fixa de 24 horas é implícita nessa chave. A transação de disparo usa `FOR UPDATE SKIP LOCKED` para processar cada aviso uma única vez.

### Central de avisos

| Contrato | Consulta |
| --- | --- |
| `GET /api/v1/me/reminders` | `Reminder` com `user_id` da sessão e `status = 'disparado'`, ordenado por `fired_at desc` |
| `PUT /api/v1/me/reminders/{id}/read` | Atualização atômica do próprio lembrete disparado preservando o primeiro `read_at` |

O sino da navegação abre os lembretes para qualquer conta autenticada. Para estudantes, a opção Sugestões dá acesso aos avisos de moderação. O [contrato da API](/api-specs#lembretes-da-agenda) descreve os campos e as respostas.

## 4. Quem pode o quê

| Recurso | Visitante | Conta logada (navegador) | Professor / admin | Servidor |
| --- | --- | --- | --- | --- |
| `registrar_evento_coletado` | Não | Não | Não | Sim |
| Colunas de procedência e de moderação em `eventos` | Não grava | Não grava | Só pelas RPCs | Sim |
| `coletas_eventos` | Sem acesso | Sem acesso | Sem acesso | Sim |
| `listar_revisoes_coleta`, `moderar_sugestao` | Não | Recusado | Sim | Sim |
| `disparar_lembretes` | Não | Não | Não | Sim |
| `lembretes` | Sem acesso | Lê os próprios disparados e marca leitura | As mesmas permissões de destinatário | Sim |

## 5. Testes e Validação Local

A suíte automatizada cobre unitariamente o coletor, a similaridade de duplicatas, o tratamento de dia inteiro, multicampus, os contratos da API e a projeção no frontend:

```bash
# Testes unitários do coletor (34 testes de unidade, orquestração, concorrência e regras)
cd backend && PYTHONPATH=. venv/bin/pytest tests/test_event_collector.py

# Testes de contrato da API pública de eventos (10 testes cobrindo procedência RF16)
cd backend && PYTHONPATH=. venv/bin/pytest tests/test_events_api.py

# Testes de frontend (37 testes, incluindo toUiEvent e campos de procedência)
cd frontend && node --test src/lib/*.test.js
```

Para testes de banco de dados contra o Supabase local (18 testes cobrindo triggers, RLS, RPCs e idempotência):
```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  venv/bin/pytest tests/test_event_collection_database.py -q
```

`backend/tests/test_reminders_database.py` cobre os cenários de aceite que dependem do banco: aviso 24 h antes, troca ao mudar o início, cancelamento, dia inteiro, evento criado dentro da janela, disparo repetido sem duplicar, revalidação no disparo e isolamento entre contas.

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_reminders_database.py -q
```

Os contratos HTTP usam `backend/tests/test_reminders_api.py`. Os testes da central em `frontend/tests/reminders.spec.js` exercitam dois perfis, retorno à sessão, estados de leitura, erro, paginação e navegação por teclado. Consulte o [registro local de aceite](#aceite-local-da-s8-b03).

## 6. Coletor da Agenda UnB Notícias

O adaptador está em `backend/src/modules/events/collector.py`. A origem é fixa em `https://noticias.unb.br`; o cliente consulta `robots.txt` e só acessa a listagem `/component/agenda/agendas` e detalhes `/component/agenda/agenda/{id}` quando permitidos. O cliente não segue redirecionamentos, não usa cookies nem proxy do ambiente, tem timeout de 20 segundos e espera pelo menos um segundo entre requisições. Falhas transitórias recebem uma tentativa adicional respeitando `Retry-After` até 60 segundos.

O coletor percorre os offsets publicados pela paginação, deduplica os IDs antes de buscar os detalhes, limita a leitura a 100 páginas/900 eventos e carrega toda a fonte antes de gravar. Assim, uma interrupção ao ler uma página mantém os registros já existentes sem aplicar uma coleta parcial. As gravações e o resultado da execução são confirmados juntos; um advisory lock impede duas execuções simultâneas. O coletor nunca apaga eventos que deixaram de aparecer na fonte.

### Execução Recorrente em Background

O processo pode ser executado manualmente ou em background recorrente:
1. **Makefile:**
   - `make events-collect`: executa uma única rodada de coleta.
   - `make events-collect-daemon`: executa em loop contínuo como daemon local.
2. **CLI Direto:**
   - `python -m src.modules.events.collector`: execução pontual.
   - `python -m src.modules.events.collector --interval-hours 6`: repete a execução no intervalo mínimo de 1 hora.
   - `python -m src.modules.events.collector --daemon`: roda continuamente em background.
3. **GitHub Actions (Ambiente Hospedado):**
   - Configurado em `.github/workflows/production-jobs.yml` no job `collector`.
   - Disparo agendado diariamente via cron (`27 10 * * *` - 07h27 BRT) ou manual via `workflow_dispatch` (selecionando `job: collector`).
   - Requer `github.ref == 'refs/heads/main'`, segredo `DATABASE_URL` e variável `PRODUCTION_EVENT_COLLECTION_ENABLED = 'true'` no environment `production-jobs`.

### Limitações e Evidências Pendentes no Ambiente Hospedado

Os contratos de código, migração e testes unitários locais estão completos. Contudo, as seguintes etapas dependem de acesso ao ambiente remoto de produção/homologação e credenciais de infraestrutura:
- **Execução hospedada no GitHub Actions:** Habilitar a variável `PRODUCTION_EVENT_COLLECTION_ENABLED = 'true'` e disparar o workflow no ambiente `production-jobs`.
- **Validação de concorrência e idempotência em banco remoto:** Executar duas instâncias simultâneas do coletor para registrar o bloqueio via advisory lock e a atualização sem duplicatas.
- **Validação de resiliência a falhas da fonte:** Simular timeout ou HTTP 503 na conexão com `noticias.unb.br` em execução real e comprovar a preservação intacta dos dados já gravados.
- **Homologação humana:** Realizar a revisão e moderação de itens marcados como `possivel_duplicata`, `ambiguo` ou `informe` por um usuário com papel professor/admin na interface administrativa.

## 7. Validação e Revisão Técnica — S7-B05 (#75)

Consolidado em **16/11/2026** para a issue [#75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75) (RF14, RF15, RF16, RNF02, RNF11, RNF13 e [ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)). Responsável principal: `@pontesluis`. Corresponsável: `@marrathomaz`. Apoio em migrações: `@felipecduque7`.

| Critério de Aceite / Cenário | Evidência Técnica e Testes | Resultado |
| --- | --- | --- |
| **1. Execução agendada, duas execuções sucessivas/concorrentes sem duplicatas e atualização de data no mesmo registro** | Workflow `.github/workflows/production-jobs.yml` (`job: collector`), alvos `make events-collect` / `make events-collect-daemon`, índice único `uq_eventos_fonte (fonte, fonte_id)`, `pg_try_advisory_lock(708073)` e `pg_advisory_xact_lock`, validados em `test_event_collector.py` e `test_event_collection_database.py` | Aprovado |
| **2. Indisponibilidade da fonte preserva registros, respeito a decisões de moderação/campos editados localmente e cobertura multicampus** | Leitura integral prévia ao bloco transacional, rollback em falha HTTP/timeout com registro em `coletas_eventos` (`status = 'falha'`), trigger `tg_registra_edicao_local` (`campos_editados`), preservação de `moderado_em` e normalização dos 5 campi da UnB | Aprovado |
| **3. Publicação automática de evento completo e retenção em revisão de item ambíguo, incompleto, informe ou possível duplicata, com procedência visível** | RPC `registrar_evento_coletado(jsonb)`, tratamento de `00:00` sem sinal explícito como `ambiguo`, distinção `evento` vs `informe`, conciliação de URL manual, similaridade de título/data ($\le 2$ dias) e exposição de `source`/`source_url` em `EventRead` e na interface | Aprovado |

### Revisão de Contratos, Permissões e Dados Afetados

- **Revisores:** `@marrathomaz` e `@pontesluis` (apoio em migrações: `@felipecduque7`).
- **Contratos revisados:** `EventRead` (`GET /api/v1/events`, `GET /api/v1/events/{event_id}`, `GET /api/v1/me/saved-events`) com `ends_at`, `all_day`, `start_date`, `end_date`, `source` e `source_url`, mantendo privados `fonte_hash`, `coletado_em`, `motivo_revisao` e `campos_editados` (`test_public_event_exposes_provenance_without_internal_metadata`).
- **Permissões e segurança (RLS / Triggers):** `public.coletas_eventos` com RLS ativo e `REVOKE ALL FROM anon, authenticated`; `public.registrar_evento_coletado(jsonb)` restrita a `service_role`; `public.listar_revisoes_coleta(text, integer)` e `public.moderar_sugestao(uuid, text, text)` restritas a moderadores (`public.is_event_moderator()`); trigger `tg_protege_procedencia` bloqueando forja de procedência pelo navegador com SQLSTATE `42501` (`test_browser_cannot_collect_or_forge_provenance`).
- **Tabelas afetadas:** `public.eventos`, `public.eventos_pessoais` e `public.coletas_eventos` (`supabase/migrations/20261111140000_eventos_datas_e_coleta.sql`).
- **Pendências abertas rastreadas:**
  1. Integração visual da RPC `listar_revisoes_coleta` na tela de moderação do frontend acompanhada na issue **#80 (`S8-F02`)** (`@Bielziin07` / `@marrathomaz`).
  2. Ativação da variável `PRODUCTION_EVENT_COLLECTION_ENABLED=true` no environment `production-jobs` após promoção para `main`, acompanhada na issue **#76 (`S7-B06`)** (`@pontesluis`).

## Aceite local da S8-B03

Validação de 18/11/2026 no commit `3db3e29`, em Supabase local descartável, PostgreSQL 17, FastAPI e Chromium, com contas e eventos sintéticos. Os testes aceleraram o vencimento de pendências sintéticas para observar o disparo.

| Cenário da #81 | Evidência local | Resultado |
| --- | --- | --- |
| Compromisso privado e evento público salvo | Criação de compromisso, criação e salvamento de evento público pela API real. O PostgreSQL gravou os dois avisos com antecedência de 24 h e o cron os tornou visíveis. | Passou |
| Dia inteiro e entrada tardia | A suíte PostgreSQL verificou a meia-noite do primeiro dia em Brasília e a ausência de aviso tardio. Um compromisso criado pela API 12 h antes do início também ficou sem aviso. | Passou |
| Cancelamento e mudança de início | Exclusão de compromisso e alteração de horário verificadas pela API real. Uma conta removeu o próprio vínculo duas vezes e a outra manteve seu aviso. A suíte PostgreSQL também cobriu retirada do catálogo e salvamento simultâneo à mudança de horário nas duas ordens. | Passou |
| Reinício, repetição e revalidação | O SQL de ativação foi repetido com um único job. Com a aplicação fechada, o banco foi parado antes do vencimento e iniciado depois dele. Duas execuções do cron terminaram com sucesso e houve um único aviso disparado. A suíte verificou o descarte após o início. | Passou |
| Retorno e estados de leitura | Chromium abriu o sino com a sessão real, marcou o lembrete e confirmou a leitura depois de sair e entrar novamente. Duas requisições HTTP simultâneas preservaram o mesmo primeiro `read_at`. | Passou |
| Isolamento | Uma segunda conta autenticada recebeu lista vazia e 404 ao tentar marcar o aviso alheio. O navegador confirmou que a central da segunda conta não incluía dados da primeira. A suíte PostgreSQL também verificou as permissões de visitante e do destinatário. | Passou |

A revisão técnica local cobriu os contratos GET e PUT, a filtragem por sessão e status, RLS, permissões de coluna, a sincronização do vínculo público e o papel executor do cron. A API lê títulos autorizados de `eventos` e `eventos_pessoais`. Registra a primeira leitura em `lembretes`. O job atualiza o estado de disparo na mesma tabela e revalida `eventos_salvos` quando aplicável.

O [PR #105](https://github.com/unb-mds/2026-2-AgendaUnB/pull/105) acompanha a [issue #81](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81). Versão hospedada, evidências de homologação e nome do revisor humano seguem pendentes.
