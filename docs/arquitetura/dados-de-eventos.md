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
| Mesmo título (sem acentos e pontuação) no mesmo dia de outro evento | `criado` | Revisão, `possivel_duplicata`, com `possivel_duplicata_de` |
| Mesma URL de um evento cadastrado na plataforma | `conciliado` | Mantém o evento manual e anexa a procedência; não cria outro |
| Mesmo `(fonte, fonte_id)` e mesmo hash | `inalterado` | Só renova `coletado_em` |
| Mesmo `(fonte, fonte_id)`, hash diferente | `atualizado` | Atualiza **o mesmo registro** |

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
- **`00:00` na fonte.** Não invente horário. Se a página indica dia inteiro, envie `dia_inteiro`; se não dá para saber, envie o instante com `ambiguo: true`.
- **`erro_codigo` é um código curto** (até 60 caracteres). Nunca grave HTML, corpo de resposta ou conteúdo da fonte.
- **Frequência moderada**, com `User-Agent` identificável e respeito a `robots.txt` (RNF11).
- O hash deve ser estável: normalize espaços e ordem dos campos antes de calcular, para que a mesma página gere o mesmo hash.

### Revisão por professor e admin

`listar_revisoes_coleta(p_status, p_offset)` devolve `{"items": [...], "total": n}` com 20 itens por página, incluindo `fonte_url`, `motivo_revisao` e `possivel_duplicata_de`. A decisão usa a RPC que já existe, `moderar_sugestao(evento_id, 'aprovado' | 'rejeitado', justificativa)`, que agora também aceita itens coletados e registra `moderado_por` e `moderado_em`. Item sem data não pode ser aprovado.

Procedência visível (RF16): eventos com `fonte` preenchida devem exibir a origem e o link `fonte_url`. `autor_id` é nulo nesses eventos; o ORM e a API já tratam organizador ausente.

## 3. Quem pode o quê

| Recurso | Visitante | Conta logada (navegador) | Professor / admin | Servidor |
| --- | --- | --- | --- | --- |
| `registrar_evento_coletado` | Não | Não | Não | Sim |
| Colunas de procedência e de moderação em `eventos` | Não grava | Não grava | Só pelas RPCs | Sim |
| `coletas_eventos` | Sem acesso | Sem acesso | Sem acesso | Sim |
| `listar_revisoes_coleta`, `moderar_sugestao` | Não | Recusado | Sim | Sim |

## 4. Testes

`backend/tests/test_event_collection_database.py` cobre os cenários de aceite que dependem do banco: datas civis e intervalos inválidos, coletas sucessivas no mesmo registro, revisão de itens incompletos, ambíguos e informes, possível duplicata, conciliação por URL, edições locais, decisões de moderação, falha da fonte e procedência que o navegador não forja.

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_event_collection_database.py -q
```

## 5. Coletor da Agenda UnB Notícias

O adaptador está em `backend/src/modules/events/collector.py`. A origem é fixa em `https://noticias.unb.br`; o cliente consulta `robots.txt` e só acessa a listagem `/component/agenda/agendas` e detalhes `/component/agenda/agenda/{id}` quando permitidos. A política consultada em 11/11/2026 bloqueava `/components/` (plural), não as rotas `/component/` (singular) da agenda. O cliente não segue redirecionamentos, não usa cookies nem proxy do ambiente, tem timeout de 20 segundos e espera pelo menos um segundo entre requisições. Falhas transitórias recebem uma tentativa adicional respeitando `Retry-After` até 60 segundos.

O coletor percorre os offsets publicados pela paginação, deduplica os IDs antes de buscar os detalhes, limita a leitura a 100 páginas/900 eventos e carrega toda a fonte antes de gravar. Assim, uma interrupção ao ler uma página mantém os registros já existentes sem aplicar uma coleta parcial. As gravações e o resultado da execução são confirmados juntos; um advisory lock impede duas execuções simultâneas. O coletor nunca apaga eventos que deixaram de aparecer na fonte.

Os dados vêm da página de detalhes: título, descrição, datas, horário, local, categoria e links externos. Só os tipos `Eventos`, `Cursos` e `Defesas` são classificados como eventos; outras categorias seguem como informes para moderação. O campus só é preenchido quando o local identifica um campus de forma explícita. Um horário `00:00` é tratado como preenchimento incerto e o item vai para revisão; o coletor não deduz que seja um evento de dia inteiro, conforme a ADR-011. Sem ano explícito ou com data/hora incompleta, também não publica automaticamente.

Com `DATABASE_URL` configurada para o banco do ambiente, na pasta `backend`:

```sh
python -m src.modules.events.collector
python -m src.modules.events.collector --interval-hours 6
```

O primeiro comando executa uma coleta. O segundo repete a execução depois do intervalo informado, que precisa ser de pelo menos uma hora. O processo recorrente deve ser iniciado por um serviço de background do ambiente; não há rota HTTP que dispare a coleta nem credencial de banco no navegador. Até homologar a duração de uma leitura completa, configurar cobertura e validar as falhas no ambiente, manter a recorrência desligada.

Testes sem acesso à fonte ou ao banco real:

```sh
cd backend
python -m pytest tests/test_event_collector.py -q
```

Continuam pendentes e precisam de evidência no ambiente hospedado: configurar e demonstrar a recorrência, duas execuções sucessivas e concorrentes, uma indisponibilidade da fonte com preservação dos registros, e cobertura multicampus. Os testes de banco automatizam os contratos de persistência, mas não substituem a homologação do serviço e da fonte reais.
