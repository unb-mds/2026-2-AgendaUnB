---
title: "Dados de planos: leitura e confirmação"
description: "Como a API usa as funções de planos da Release 2."
---

# Dados de planos: leitura e confirmação

Guia de integração das migrações `20261110141000_planos_confirmacao_idempotente.sql`, que completam o modelo da [S7-D01 (#69)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69).

| Issue | O que o banco e a aplicação fazem |
| --- | --- | --- |
| [S7-B04 (#72)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72) | Confirmação em transação, por usuário, com `Idempotency-Key`, validação de acesso, versão e datas. A rota envia o ator validado, lê a versão aprovada, traduz erros SQLSTATE e devolve eventos e resultados por item. |

## 1. Por que as funções recebem o ator

O back-end conecta com um usuário que ignora RLS. Se a regra de "quem pode" ficasse só na API, um esquecimento em um endpoint exporia conteúdo privado. Por isso cada função recebe `p_ator`, **o id da conta que a API já validou na sessão**, e confere a permissão no banco.

Nunca passe um id vindo do corpo da requisição. Nenhuma dessas funções é chamável pelo navegador.

```python
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from fastapi import HTTPException

STATUS_POR_SQLSTATE = {"42501": 403, "P0002": 404, "22023": 422, "55000": 409, "AG409": 409}

def chamar(db, sql: str, **params):
    """Executa uma função do banco e traduz os erros previstos para HTTP."""
    try:
        resultado = db.execute(text(sql), params).scalar_one()
        db.commit()
        return resultado
    except DBAPIError as exc:
        db.rollback()
        status = STATUS_POR_SQLSTATE.get(getattr(exc.orig, "sqlstate", None))
        if status is None:
            raise
        # A primeira linha da mensagem do banco é escrita para o usuário final.
        raise HTTPException(status, str(exc.orig).splitlines()[0])
```

| SQLSTATE | HTTP | Significado |
| --- | --- | --- |
| `42501` | 403 | Sem permissão sobre a versão |
| `P0002` | 404 | Versão, candidato ou plano inexistente ou indisponível |
| `22023` | 422 | Dados inválidos, inclusive data ambígua sem correção |
| `55000` | 409 | O estado não permite a ação (plano em processamento, sem turma, conteúdo compartilhado) |
| `AG409` | 409 | `Idempotency-Key` reutilizada com outro conteúdo |

## 2. Quem lê uma versão

`ator_pode_ler_versao(ator, versao)`:

- o **autor da versão**, sempre;
- os demais, só se a versão estiver **compartilhada** e a conta **seguir a oferta** do plano.

Papel de professor ou admin não abre conteúdo privado. Quando houver revisões (S8-B01), o rascunho de uma revisão pertencerá a quem a escreveu, inclusive diante do dono do plano original. Use essa função antes de devolver uma versão ou seus candidatos pela API; as políticas RLS usam a mesma regra para o navegador (`pode_ler_versao`).

O vínculo com a turma é autodeclarado: mostre isso na interface.

## 3. Confirmação idempotente (#72, ADR-010)

```python
@router.post("/{syllabus_id}/confirm")
def confirmar(syllabus_id: UUID, payload: ConfirmSyllabusRequest,
              idempotency_key: str = Header(alias="Idempotency-Key"),
              current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    versao_id = payload.version_id or versao_atual_do_autor(db, syllabus_id, current_user.id)
    itens = [item_para_o_banco(c) for c in payload.candidates]
    return chamar(db, "select public.confirmar_importacao(:ator, :chave, :versao, cast(:itens as jsonb))",
                  ator=current_user.id, chave=idempotency_key, versao=versao_id, itens=json.dumps(itens))
```

Cada item: `candidato_id` e, opcionalmente, `titulo`, `descricao`, `categoria` e a data corrigida, como `inicio` (ISO 8601 **com fuso**) ou `dia_inteiro: true` com `data_inicio` e `data_fim` (exclusivo; omitido vale um dia).

Retorno:

```json
{
  "operacao_id": "…",
  "repetida": false,
  "itens": [{"candidato_id": "…", "evento_id": "…", "resultado": "criado", "removido": false}]
}
```

| Situação | Resultado |
| --- | --- |
| Primeira vez | `resultado: criado`, evento na agenda de quem confirmou |
| Mesma chave, mesmo conteúdo | `repetida: true`, mesmo resultado, nada é gravado |
| Mesma chave, conteúdo diferente | `AG409` |
| Outra chave, candidato já na agenda | `resultado: ja_importado`, continua um único evento |
| A pessoa apagou o evento e o cliente repete a chave antiga | `repetida: true`, `evento_id: null`, `removido: true`. **Não recria** |
| "Adicionar novamente" depois de apagar | Chave **nova**: `criado` |
| Candidato de outra versão, repetido, descartado pelo autor ou com data ambígua sem correção | `22023`, e nada é gravado |
| Sem acesso (versão retirada, deixou de seguir, privado alheio) | `42501` |

Regras para o cliente:

- gere a chave **uma vez por ação** do usuário (por exemplo `crypto.randomUUID()` ao clicar em confirmar) e reenvie a mesma em retries. Não gere uma chave nova a cada tentativa;
- a chave tem de 8 a 200 caracteres e vale por conta;
- o conteúdo é comparado pelo JSON dos itens e pela versão: monte os itens sempre na mesma ordem;
- uma ação inválida não é registrada, então a mesma chave pode ser reenviada depois de corrigir os dados.

A operação e os itens são gravados na mesma transação dos eventos, e as confirmações de uma conta são serializadas. Em versão compartilhada, a decisão é de cada conta e não altera o candidato; no fluxo particular, o candidato do autor passa a `confirmado`, como hoje.

**Relação com `revisar_candidatos_plano` (S7-B01).** Hoje existem dois caminhos que criam eventos a partir de candidatos, sobre as mesmas tabelas e a mesma unicidade `(user_id, origem_avaliacao_id)`:

| | `revisar_candidatos_plano(plano, itens)` | `confirmar_importacao(ator, chave, versao, itens)` |
| --- | --- | --- |
| Quem chama | Conta logada (usa `auth.uid()`) | Back-end, com o ator da sessão |
| Escopo | Plano particular do próprio dono, execução atual | Qualquer versão que a conta pode ler, inclusive compartilhada |
| Descartar candidato | Sim | Não (o descarte é do autor) |
| Retry após excluir o evento | Não recria | Não recria, e informa `removido` |
| `Idempotency-Key` | Não | Sim |

Para a S7-B04 ([#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72)), a API usa `confirmar_importacao` tanto para planos privados quanto para versões compartilhadas. A chave é gerada por ação no cliente e reutilizada em retry da mesma carga; depois de excluir um evento, uma ação nova usa uma chave nova para reimportá-lo. O tipo revisado fica em `itens_importacao.tipo_revisado`, separado por conta.

## 4. Extração (#51)

- A tabela de candidatos é **`avaliacoes`**. `candidatos_avaliacao` foi removida na S7-D01.
- O worker grava candidatos com `plano_id` e, de preferência, `versao_id` e `ordem`. Sem `versao_id`, o banco usa a versão mais recente do plano. `(versao_id, ordem)` é único: reprocessar com `ordem` não duplica.
- O worker não grava em versão compartilhada (`55000`).
- O vínculo entre candidato e evento **não fica no candidato**: com versões compartilhadas, várias contas importam o mesmo candidato. Ele está em `eventos_pessoais.origem_avaliacao_id` e em `itens_importacao`.

## 5. Testes

`backend/tests/test_plan_import_database.py` cobre os cenários de aceite que dependem do banco: dois seguidores importando para agendas independentes, conta sem vínculo e visitante recusados, retries com a mesma chave após excluir o evento, seleção inválida sem gravação parcial, histórico privado e confirmações concorrentes em conexões reais. `backend/tests/test_syllabus_review_api.py` cobre o contrato HTTP, a chave obrigatória, o descarte e a preservação da origem.

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_plan_import_database.py -q
```
