---
title: "Dados de planos: leitura, confirmação, compartilhamento e votos"
description: "Como a API usa as funções de planos da Release 2."
---

Guia de integração das migrações `20261111141000_planos_confirmacao_idempotente.sql` e `20261117150000_planos_compartilhamento_e_votos.sql`, que completam o modelo da [S7-D01 (#69)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/69).

| Issue | O que o banco e a aplicação fazem |
| --- | --- |
| [S7-B04 (#72)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72) | Confirmação em transação, por usuário, com `Idempotency-Key`, validação de acesso, versão e datas. A rota envia o ator validado, lê a versão aprovada, traduz erros SQLSTATE e devolve eventos e resultados por item. |
| [S8-B01 (#77)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77) | Compartilhar voluntariamente, retirar, revisar em nova versão, editar versão privada, validar procedência institucional, votar e consultar contagens/divergências. Rotas FastAPI integradas às funções SQL com validação de acesso por ator e aviso explícito de vínculo autodeclarado. |

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
| `GET /api/v1/class-offerings/{id}/shared-plans` | Seleciona versões `compartilhadas` da oferta + votos | Seguidor autenticado da turma (`403` sem vínculo) |
| `GET /api/v1/syllabus/{id}/versions` e `.../versions/{vid}` | `select public.ator_pode_ler_versao(:ator, :versao)` | Autor da versão (privada ou compartilhada) ou seguidor da oferta se `compartilhada` |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/sharing` | `select (public.compartilhar_versao(:ator, :versao)).id` | Só o autor da versão. O plano precisa ter turma e estar `concluido` |
| `DELETE /api/v1/syllabus/{id}/versions/{vid}/sharing` | `select (public.retirar_compartilhamento(:ator, :versao)).id` | Autor da versão ou admin |
| `POST /api/v1/syllabus/{id}/versions` | `select (public.criar_revisao(:ator, :versao_origem)).id` | Autor da origem; seguidor autenticado da oferta, professor e admin, se a origem estiver `compartilhada` |
| `PUT /api/v1/syllabus/{id}/versions/{vid}` | Atualiza candidatos da versão privada | Só o autor da versão, enquanto `privada` (`409` se `compartilhada`) |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/provenance` | `select (public.validar_procedencia_institucional(:ator, :versao, :url)).id` | Só admin, em versão `compartilhada`, com URL pública oficial `http(s)` |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/candidates/{cid}/vote` | `select public.votar_avaliacao(:ator, :candidato, :valor)` | Quem pode ler a versão `compartilhada` (seguidor da turma ou autor) |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/vote` e `GET .../votes` | `select * from public.resumo_votos_versao(:ator, :versao)` | Quem pode ler a versão |
| `DELETE /api/v1/syllabus/{id}/versions/{vid}/candidates/{cid}` | Marca o candidato como `descartado` na versão | Autor da versão ou admin |

Compartilhar e retirar são idempotentes. As funções devolvem a linha de `versoes_plano`; use `(função(...)).*` para ler todos os campos. Por decisão de produto (PO, 2026-11-17, [ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos)), a versão inicial (`v1`) de planos vinculados a uma oferta concluídos com candidatos é compartilhada automaticamente para os seguidores da turma ao ser consultada/confirmada pelo autor (salvo se já tiver sido retirada com `retirada_em`); revisões posteriores sem publicação imediata e reprocessamentos nascem `privada`.

**Revisão.** `criar_revisao` cria a próxima versão do plano com `versao_origem_id` preenchido e `autor_papel` com o papel atual de quem revisa, sem alterar eventos pessoais já importados por outros usuários. Quando enviada com candidatos para um plano vinculado a oferta (ou com `share: true`), já é publicada como `compartilhada`.

**Conteúdo compartilhado não é editado.** Depois de compartilhada, a versão não aceita alteração de títulos ou datas nem inclusão de novos candidatos (`55000`): votos e importações referem-se àquele conteúdo. Para corrigir, cria-se uma revisão. O `status` do candidato continua editável, permitindo retirada lógica pelo autor da versão ou admin (`DELETE .../candidates/{cid}`).

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
- A RPC de gravação recusa avaliações retiradas (`P0002`). O resumo da versão omite essas avaliações e os votos anteriores permanecem registrados.

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

**Relação com `revisar_candidatos_plano` (S7-B01).** Hoje existem dois caminhos que criam eventos a partir de candidatos, sobre as mesmas tabelas e a mesma unicidade `(user_id, origem_avaliacao_id)`:

| | `revisar_candidatos_plano(plano, itens)` | `confirmar_importacao(ator, chave, versao, itens)` |
| --- | --- | --- |
| Quem chama | Conta logada (usa `auth.uid()`) | Back-end, com o ator da sessão |
| Escopo | Plano particular do próprio dono, execução atual | Qualquer versão que a conta pode ler, inclusive compartilhada |
| Descartar candidato | Sim | Não (o descarte é do autor) |
| Retry após excluir o evento | Não recria | Não recria, e informa `removido` |
| `Idempotency-Key` | Não | Sim |

Para a S7-B04 ([#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72)), a API usa `confirmar_importacao` tanto para planos privados quanto para versões compartilhadas. A chave é gerada por ação no cliente e reutilizada em retry da mesma carga; depois de excluir um evento, uma ação nova usa uma chave nova para reimportá-lo. O tipo revisado fica em `itens_importacao.tipo_revisado`, separado por conta.

## 6. Extração (#51)

- A tabela de candidatos é **`avaliacoes`**. `candidatos_avaliacao` foi removida na S7-D01.
- O worker grava candidatos com `plano_id` e, de preferência, `versao_id` e `ordem`. Sem `versao_id`, o banco usa a versão mais recente do plano. `(versao_id, ordem)` é único: reprocessar com `ordem` não duplica.
- O worker não grava em versão compartilhada (`55000`).
- O vínculo entre candidato e evento **não fica no candidato**: com versões compartilhadas, várias contas importam o mesmo candidato. Ele está em `eventos_pessoais.origem_avaliacao_id` e em `itens_importacao`.

## 7. Testes

`backend/tests/test_plan_import_database.py` cobre os cenários de aceite que dependem do banco: dois seguidores importando para agendas independentes, conta sem vínculo e visitante recusados, retries com a mesma chave após excluir o evento, seleção inválida sem gravação parcial, histórico privado e confirmações concorrentes em conexões reais. `backend/tests/test_syllabus_review_api.py` cobre o contrato HTTP, a chave obrigatória, o descarte e a preservação da origem.

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_plan_import_database.py -q
```

`backend/tests/test_plan_sharing_database.py` cobre os cenários de aceite que dependem do banco: só o autor compartilha e só seguidores leem, conteúdo compartilhado imutável, retirada sem apagar cópias, revisão em versão nova, procedência institucional com evidência, voto repetido e corrigido e votos privados. `backend/tests/test_plan_sharing_api.py` valida os contratos HTTP de compartilhamento, leitura por dois seguidores, importação independente por `versionId`, votação/divergência, revisão por autor/professor/admin, herança de procedência, retirada e isolamento de versões privadas.

```bash
cd backend
PYTHONPATH=. venv/bin/pytest tests/test_plan_sharing_api.py tests/test_syllabus_review_api.py tests/test_class_catalog_api.py -q
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_plan_sharing_database.py -q
```

## 8. Validação e Revisão Técnica — S8-B01 (#77)

Consolidado em **17/11/2026** para a issue [#77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77) (RF05, RF07, RNF02, RNF04 e [ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos)). Responsável principal: `@marrathomaz`. Corresponsável: `@felipecduque7`.

| Critério de Aceite / Cenário | Evidência Técnica e Testes | Resultado |
| --- | --- | --- |
| **1. Dois seguidores da mesma turma leem a versão e importam para agendas privadas independentes; visitante e usuário sem vínculo são recusados; vínculo aparece como autodeclarado** | `GET /api/v1/class-offerings/{id}/shared-plans`, `GET /api/v1/syllabus/{id}/versions/{vid}` e `POST /api/v1/syllabus/{id}/confirm` com `versionId`, `membership_type="autodeclarado"` e `shared_content_notice`, validados em `test_plan_sharing_api.py` e `test_plan_sharing_database.py` | Aprovado |
| **2. Voto repetido mantém a contagem e permite corrigir o próprio voto; versão nova preserva eventos importados** | `PUT .../versions/{vid}/candidates/{cid}/vote`, `PUT .../versions/{vid}/vote` e `GET .../versions/{vid}/votes`, chave primária `(user_id, avaliacao_id)` em `votos_avaliacao`, indicador `divergent` sem alterar datas e preservação de `eventos_pessoais` ao criar revisão | Aprovado |
| **3. Retirar a versão impede novos acessos e importações e preserva cópias particulares já importadas e revisões derivadas** | `DELETE /api/v1/syllabus/{id}/versions/{vid}/sharing` (`public.retirar_compartilhamento`), bloqueando novas leituras, votos e confirmações enquanto preserva `eventos_pessoais` e revisões compartilhadas independentes | Aprovado |
| **4. Edição por autor, professor e admin, publicação pelo autor e retirada por autor ou admin; revisão preserva versão anterior e papel de professor/admin não dá acesso a dados privados alheios** | `POST /api/v1/syllabus/{id}/versions` (`public.criar_revisao`), `PUT /api/v1/syllabus/{id}/versions/{vid}`, `PUT .../provenance`, triggers `tg_avaliacao_compartilhada_imutavel` e verificação `ator_pode_ler_versao` | Aprovado |

### Revisão de Contratos, Permissões e Dados Afetados

- **Revisores:** `@marrathomaz` e `@felipecduque7`.
- **Contratos revisados:** `SharedPlanList` (`GET /api/v1/class-offerings/{id}/shared-plans`), `SyllabusVersionListResponse` (`GET /api/v1/syllabus/{id}/versions`), `VersionStatusResponse` (`GET/PUT /versions/{vid}`, `POST /versions`, `PUT/DELETE /versions/{vid}/sharing`, `PUT /versions/{vid}/provenance`), `CandidateVoteSummaryRead` / `VoteVersionResponse` / `VersionVotesResponse` (`PUT .../vote`, `GET .../votes`) e `ConfirmSyllabusRequest` (`versionId` opcional em `POST /api/v1/syllabus/{id}/confirm`).
- **Permissões e segurança (RLS / Funções SQL):** `votos_avaliacao` com RLS ativo e leitura restrita aos próprios votos pelo navegador; funções `compartilhar_versao`, `retirar_compartilhamento`, `criar_revisao`, `validar_procedencia_institucional`, `votar_avaliacao` e `resumo_votos_versao` restritas a `service_role` e parametrizadas com `p_ator` validado pela sessão; `professor` e `admin` não leem nem publicam versões privadas de terceiros.
- **Tabelas afetadas:** `public.versoes_plano`, `public.avaliacoes`, `public.votos_avaliacao`, `public.operacoes_importacao`, `public.itens_importacao` e `public.eventos_pessoais` (`supabase/migrations/20261117150000_planos_compartilhamento_e_votos.sql`).
- **Pendências abertas rastreadas:** Integração visual completa da biblioteca de planos compartilhados e votação na interface React acompanhada na issue **#78 (`S8-F01`)** (`@Thomas4ugust0` / `@Bielziin07`).
