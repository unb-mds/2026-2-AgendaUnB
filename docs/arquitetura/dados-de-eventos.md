---
title: "Dados de eventos: datas, coleta e lembretes"
description: "Como a API, o coletor e o agendador usam as estruturas de eventos da Release 2."
---

# Dados de eventos: datas, coleta e lembretes

Guia de integração das migrações `20261111140000_eventos_datas_e_coleta.sql` e `20261110152000_eventos_lembretes.sql`. Elas entregam a parte de dados das issues abaixo; a API, o coletor e o agendador são implementados nas próprias issues.

| Issue | O que o banco já faz | O que falta na aplicação |
| --- | --- | --- |
| [S7-B05 (#75)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75) | Upsert por origem, decisão publicar/revisar, conciliação por URL, proteção de edições locais e de decisões de moderação, registro das execuções | Ler e normalizar a fonte, agendar a execução, tela de revisão |
| [S8-B03 (#81)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81) | Agendar, trocar, cancelar e disparar avisos, sem duplicar | Chamar o disparo periodicamente, endpoints e central de avisos |

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

Um processo periódico (a cada 5 minutos é suficiente) executa:

```sql
select public.disparar_lembretes();   -- devolve quantos avisos foram disparados
```

- Pode rodar quantas vezes for, em um ou vários processos: cada aviso dispara uma única vez (`FOR UPDATE SKIP LOCKED`).
- A elegibilidade é conferida de novo no disparo. Aviso atrasado ainda é entregue se o evento não começou; depois do início é descartado.
- Reiniciar o agendador não perde nem duplica avisos: o estado está na tabela.

### Central de avisos

| Contrato | Consulta |
| --- | --- |
| `GET /api/v1/me/reminders` | `Reminder` com `user_id` da sessão e `status = 'disparado'`, ordenado por `fired_at desc` |
| `PUT /api/v1/me/reminders/{id}/read` | `update lembretes set lido_em = now() where id = :id and user_id = :u and status = 'disparado'` |

O banco mantém o primeiro `lido_em` em retries. No contrato, `event_kind` é `personal` ou `saved_public` (`pessoal`/`publico_salvo` no banco), `event_id` é `evento_pessoal_id` ou `evento_id`, e `scheduled_at` é `agendado_para`. Pelo navegador, a conta só enxerga os próprios avisos já disparados e só altera `lido_em`.

## 4. Quem pode o quê

| Recurso | Visitante | Conta logada (navegador) | Professor / admin | Servidor |
| --- | --- | --- | --- | --- |
| `registrar_evento_coletado` | Não | Não | Não | Sim |
| Colunas de procedência e de moderação em `eventos` | Não grava | Não grava | Só pelas RPCs | Sim |
| `coletas_eventos` | Sem acesso | Sem acesso | Sem acesso | Sim |
| `listar_revisoes_coleta`, `moderar_sugestao` | Não | Recusado | Sim | Sim |
| `disparar_lembretes` | Não | Não | Não | Sim |
| `lembretes` | Sem acesso | Lê os próprios disparados; marca leitura | Sem acesso por papel | Sim |

## 5. Testes

`backend/tests/test_event_collection_database.py` cobre os cenários de aceite que dependem do banco: datas civis e intervalos inválidos, coletas sucessivas no mesmo registro, revisão de itens incompletos, ambíguos e informes, possível duplicata, conciliação por URL, edições locais, decisões de moderação, falha da fonte e procedência que o navegador não forja.

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_event_collection_database.py -q
```

Continuam fora desta entrega e precisam de evidência no ambiente publicado: execução agendada real do coletor, duas execuções concorrentes contra a fonte, o comportamento com a fonte fora do ar e a cobertura multicampus.

`backend/tests/test_reminders_database.py` cobre os cenários de aceite que dependem do banco: aviso 24 h antes, troca ao mudar o início, cancelamento, dia inteiro, evento criado dentro da janela, disparo repetido sem duplicar, revalidação no disparo e isolamento entre contas.

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_reminders_database.py -q
```

Fora desta entrega: o agendador periódico, os endpoints e a central de avisos.
