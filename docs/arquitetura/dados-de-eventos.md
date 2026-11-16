---
title: "Dados de eventos: datas, coleta"
description: "Como a API, o coletor usam as estruturas de eventos da Release 2."
---

# Dados de eventos: datas, coleta

Guia de integração das migrações `20261111140000_eventos_datas_e_coleta.sql`. Elas entregam a parte de dados das issues abaixo; a API, o coletor e o agendador são implementados nas próprias issues.

| Issue | O que o banco já faz | O que falta na aplicação |
| --- | --- | --- |
| [S7-B05 (#75)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75) | Upsert por origem, decisão publicar/revisar, conciliação por URL, proteção de edições locais e de decisões de moderação, registro das execuções | Configurar e homologar a execução recorrente no ambiente hospedado; registrar as evidências operacionais da issue |

**Regra geral:** o que precisa valer em qualquer caminho de escrita está em chaves únicas, triggers e funções. A aplicação chama as funções; não reimplementa as regras. Nada daqui é gravável pelo navegador.

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
| Título semelhante (>= 72% similaridade) e data próxima (<= 2 dias) | `criado` | Revisão, `possivel_duplicata`, com `possivel_duplicata_de` |
| Mesma URL de um evento cadastrado na plataforma | `conciliado` | Mantém o evento manual e anexa a procedência; não cria outro |
| Mesmo `(fonte, fonte_id)` e mesmo hash | `inalterado` | Só renova `coletado_em` |
| Mesmo `(fonte, fonte_id)`, hash diferente | `atualizado` | Atualiza **o mesmo registro** |

#### Regra de Detecção de Possíveis Duplicatas
Para evitar publicação duplicada de eventos com grafias ligeiramente distintas ou datas aproximadas:
1. **Normalização**: títulos passam por conversão para minúsculas, remoção de acentuação (`NFKD`), eliminação de pontuação e colapso de espaços em branco.
2. **Cálculo de Similaridade**: combina sobreposição de bigramas/trigramas e distância de caracteres (limiar de similaridade $\ge 0{,}72$).
3. **Preservação de Dígitos/Edições**: títulos que possuam números distintos (ex.: `"Seminário Módulo 1"` vs `"Seminário Módulo 2"`, ou `"Encontro 2025"` vs `"Encontro 2026"`) **não** são considerados duplicatas, prevenindo falsos positivos.
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

## 3. Quem pode o quê

| Recurso | Visitante | Conta logada (navegador) | Professor / admin | Servidor |
| --- | --- | --- | --- | --- |
| `registrar_evento_coletado` | Não | Não | Não | Sim |
| Colunas de procedência e de moderação em `eventos` | Não grava | Não grava | Só pelas RPCs | Sim |
| `coletas_eventos` | Sem acesso | Sem acesso | Sem acesso | Sim |
| `listar_revisoes_coleta`, `moderar_sugestao` | Não | Recusado | Sim | Sim |

## 4. Testes e Validação Local

A suíte automatizada cobre unitariamente o coletor, a similaridade de duplicatas, o tratamento de dia inteiro, multicampus, os contratos da API e a projeção no frontend:

```bash
# Testes unitários do coletor (30 testes de unidade e regras)
cd backend && PYTHONPATH=. venv/bin/pytest tests/test_event_collector.py

# Testes de contrato da API pública de eventos (10 testes cobrindo procedência RF16)
cd backend && PYTHONPATH=. venv/bin/pytest tests/test_events_api.py

# Testes de frontend (37 testes, incluindo toUiEvent e campos de procedência)
cd frontend && node --test src/lib/*.test.js
```

Para testes de banco de dados contra o Supabase local (quando o container estiver ativo):
```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  venv/bin/pytest tests/test_event_collection_database.py -q
```

## 5. Coletor da Agenda UnB Notícias

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
