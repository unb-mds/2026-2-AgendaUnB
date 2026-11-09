---
title: "Dados de planos: compartilhamento, votos, importação e catálogo"
description: "Como a API usa as funções de planos e de catálogo da Release 2."
---

# Dados de planos: compartilhamento, votos, importação e catálogo

Guia de integração da migração `20261110110000_planos_compartilhamento_votos_importacao.sql`, que completa o modelo da [S7-D01 (#69)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69).

| Issue | O que o banco já faz | O que falta na aplicação |
| --- | --- | --- |
| [S7-B04 (#72)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72) | Confirmação em transação, por usuário, com `Idempotency-Key`, validação de acesso, versão e datas | Ler o cabeçalho, chamar a função e traduzir o retorno |
| [S8-B01 (#77)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77) | Compartilhar, retirar, revisar, validar procedência, votar e contar | Endpoints e respostas |
| [S7-B03 (#70)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/70) | Upsert do catálogo com identidade estável, registro das sincronizações e estado do cache | Adaptador do Followw e endpoint do catálogo |

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

Papel de professor ou admin não abre conteúdo privado. O rascunho de uma revisão pertence a quem a escreveu, inclusive diante do dono do plano original. Use essa função antes de devolver uma versão ou seus candidatos pela API; as políticas RLS usam a mesma regra para o navegador (`pode_ler_versao`).

O vínculo com a turma é autodeclarado: mostre isso na interface.

## 3. Compartilhamento e revisões (#77)

| Contrato | Chamada | Quem pode |
| --- | --- | --- |
| `PUT .../versions/{id}/sharing` | `select (public.compartilhar_versao(:ator, :versao)).id` | Só o autor da versão. O plano precisa ter turma e estar `concluido` |
| `DELETE .../versions/{id}/sharing` | `select (public.retirar_compartilhamento(:ator, :versao)).id` | Autor ou admin |
| `POST .../versions` | `select (public.criar_revisao(:ator, :versao_origem)).id` | Autor da origem; professor e admin, se a origem estiver compartilhada |
| Validar origem institucional | `select (public.validar_procedencia_institucional(:ator, :versao, :url)).id` | Só admin, com URL pública oficial |

Compartilhar e retirar são idempotentes. As funções devolvem a linha de `versoes_plano`; use `(função(...)).*` para ler todos os campos.

**Revisão.** `criar_revisao` cria a próxima versão do plano, **privada**, com os candidatos copiados (menos os descartados), `versao_origem_id` preenchido e `autor_papel` com o papel atual de quem revisa. O fluxo é: criar a revisão, ajustar os candidatos da versão nova e então compartilhá-la. Professor e admin publicam direto as próprias revisões.

**Conteúdo compartilhado não é editado.** Depois de compartilhada, a versão não aceita alteração, exclusão nem inclusão de candidatos (`55000`): votos e importações referem-se àquele conteúdo. Para corrigir, cria-se uma revisão. O `status` do candidato continua editável, porque é a decisão particular do autor.

**Retirada.** Bloqueia novos acessos, votos e importações. Não retira as revisões (cada uma tem a própria visibilidade), não apaga votos nem remove eventos já importados. Ficam registrados `retirada_em` e `retirada_por`.

**Procedência institucional.** `autor_papel` e origem institucional são coisas diferentes. A origem só é atribuída por admin com `fonte_institucional_url`. Uma revisão feita por professor ou admin herda a procedência e a evidência; a de estudante não. O banco recusa `procedencia_institucional = true` sem evidência.

## 4. Votos (#77)

```python
contagem = chamar(db, "select public.votar_avaliacao(:ator, :candidato, :valor)",
                  ator=current_user.id, candidato=candidate_id,
                  valor={"confirm": "confirma", "contest": "contesta"}[payload.value])
# {"avaliacao_id": "...", "confirmam": 3, "contestam": 1, "meu_voto": "confirma"}
```

- Um voto por conta e candidato. Votar de novo troca o próprio voto; repetir o mesmo valor não muda nada.
- Só vota quem pode ler a versão compartilhada.
- `select * from public.resumo_votos_versao(:ator, :versao)` devolve, por candidato, `confirmam`, `contestam` e `meu_voto`, na ordem dos candidatos.
- O voto individual é privado: pelo navegador cada conta lê só os próprios votos. A API expõe contagens.
- Votos **não alteram datas** e não são prova. Mostre a divergência; a correção é uma revisão.

## 5. Confirmação idempotente (#72, ADR-010)

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

**Transição.** O endpoint atual, sem `Idempotency-Key`, continua funcionando sobre as mesmas tabelas e a mesma unicidade. Ao migrá-lo para a função, documente a obrigatoriedade do cabeçalho antes de exigi-lo dos clientes.

## 6. Catálogo de turmas (#70, ADR-009)

```python
resultado = db.execute(text("select public.registrar_oferta_catalogo(cast(:p as jsonb))"),
                       {"p": json.dumps(oferta)}).scalar_one()   # {"id", "acao"}
```

| Campo | Obrigatório | Observação |
| --- | --- | --- |
| `codigo`, `nome` | sim | Código normalizado em maiúsculas |
| `turma` | sim | Texto. `"01"` e `"1"` são turmas diferentes |
| `ano`, `semestre` | sim | |
| `oferta_origem_id` | não | ID da **oferta** na origem. Preferido como identidade quando existir |
| `disciplina_origem_id` | não | ID da disciplina na origem; na falta, a disciplina é identificada por código, unidade e nível |
| `unidade`, `nivel` | não | |
| `professor`, `horarios` | não | Atualizáveis, fora da identidade |
| `atualizado_na_origem_em` | não | |

`acao` é `criada`, `atualizada` ou `inalterada`. Sincronizações repetidas devolvem sempre o mesmo `id`. Chave incompleta devolve `22023` e colisão entre o ID da origem e a chave natural devolve `55000`: nos dois casos a oferta precisa de revisão antes de aparecer.

A sincronização **nunca remove** ofertas nem vínculos. Registre cada execução em `sincronizacoes_catalogo` (como em `coletas_eventos`: `status`, contadores e um `erro_codigo` curto). Para o contrato do catálogo:

```python
estado = db.execute(text("select public.estado_catalogo()")).scalar_one()
# {"atualizado_em": "2026-11-07T18:00:00+00:00", "desatualizado": true, "tem_cache": true}
```

- `source_updated_at` = `atualizado_em`; `stale` = `desatualizado`;
- sem cache (`tem_cache: false`) e com a origem fora do ar, devolva 503;
- a validade padrão do cache é de 24 horas e pode ser passada como segundo argumento: `estado_catalogo('followw', interval '6 hours')`.

`ofertas_turma.semestre` aceita `1` e `2`. Se a origem trouxer período de verão, a decisão de como representá-lo ainda está aberta e precisa ser tomada antes da sincronização completa.

## 7. Extração (#51)

- A tabela de candidatos é **`avaliacoes`**. `candidatos_avaliacao` foi removida na S7-D01.
- O worker grava candidatos com `plano_id` e, de preferência, `versao_id` e `ordem`. Sem `versao_id`, o banco usa a versão mais recente do plano. `(versao_id, ordem)` é único: reprocessar com `ordem` não duplica.
- O worker não grava em versão compartilhada (`55000`).
- O vínculo entre candidato e evento **não fica no candidato**: com versões compartilhadas, várias contas importam o mesmo candidato. Ele está em `eventos_pessoais.origem_avaliacao_id` e em `itens_importacao`.

## 8. Testes

`backend/tests/test_plan_sharing_database.py` cobre os cenários de aceite que dependem do banco: dois seguidores importando para agendas independentes, visitante e usuário sem vínculo recusados, voto repetido e corrigido, versão nova preservando eventos importados, retirada, edição por autor, professor e admin, retries, confirmações concorrentes em conexões reais e rollback sem gravação parcial.

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_plan_sharing_database.py -q
```
