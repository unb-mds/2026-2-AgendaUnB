---
title: "Dados de planos: leitura, confirmação, compartilhamento e votos"
description: "Integração da API FastAPI com as funções SQL de planos de ensino, versionamento, compartilhamento, votos e confirmação idempotente."
---

Guia de integração da API com as funções SQL de leitura, confirmação idempotente, compartilhamento, revisão, procedência institucional e votação de planos de ensino.

## 1. Por que as funções recebem o ator

O backend conecta ao PostgreSQL com um papel que ignora RLS. Se a verificação de acesso ficasse restrita à camada HTTP, qualquer rota incompleta poderia expor conteúdo privado. Por isso cada função recebe `p_ator` (**o ID da conta validado pela API na sessão**) e confere a permissão diretamente no banco.

Nunca envie um identificador de conta vindo do corpo da requisição. Nenhuma dessas funções é chamável diretamente pelo navegador.

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
| `42501` | 403 | Sem permissão sobre a versão ou turma |
| `P0002` | 404 | Versão, candidato ou plano inexistente ou indisponível |
| `22023` | 422 | Dados inválidos, inclusive data ambígua sem correção |
| `55000` | 409 | O estado não permite a ação (plano em processamento, sem turma, conteúdo compartilhado) |
| `AG409` | 409 | `Idempotency-Key` reutilizada com outro conteúdo |

## 2. Controle de leitura de versões

A função `ator_pode_ler_versao(ator, versao)` autoriza o acesso apenas para:

- o **autor da versão**, em qualquer estado;
- **seguidores da oferta** vinculada ao plano, apenas quando a versão estiver **`compartilhada`**.

Os papéis `professor` e `admin` não concedem acesso a conteúdo privado de terceiros. O rascunho privado de uma revisão pertence exclusivamente a quem a escreveu, inclusive diante do dono do plano original. As políticas RLS aplicam a mesma regra para consultas diretas via `pode_ler_versao`.

O vínculo com a oferta é autodeclarado, sendo essa condição explicitada nos contratos (`membership_type: "autodeclarado"` e `shared_content_notice`).

## 3. Compartilhamento e revisões

| Contrato HTTP | Operação no banco | Quem pode |
| --- | --- | --- |
| `GET /api/v1/class-offerings/{id}/shared-plans` | Seleciona versões `compartilhadas` da oferta + contagens de votos | Seguidor autenticado da turma (`403` sem vínculo) |
| `GET /api/v1/syllabus/{id}/versions` e `.../versions/{vid}` | `select public.ator_pode_ler_versao(:ator, :versao)` | Autor da versão (privada ou compartilhada) ou seguidor da oferta se `compartilhada` |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/sharing` | `select (public.compartilhar_versao(:ator, :versao)).id` | Só o autor da versão; plano precisa ter turma e estar `concluido` |
| `DELETE /api/v1/syllabus/{id}/versions/{vid}/sharing` | `select (public.retirar_compartilhamento(:ator, :versao)).id` | Autor da versão ou `admin` |
| `POST /api/v1/syllabus/{id}/versions` | `select (public.criar_revisao(:ator, :versao_origem)).id` | Autor da origem; seguidor autenticado da oferta, `professor` ou `admin` se a origem estiver `compartilhada` |
| `PUT /api/v1/syllabus/{id}/versions/{vid}` | Atualiza candidatos da versão privada | Só o autor da versão, enquanto `privada` (`409` se `compartilhada`) |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/provenance` | `select (public.validar_procedencia_institucional(:ator, :versao, :url)).id` | Só `admin`, em versão `compartilhada`, com URL pública oficial `http(s)` |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/candidates/{cid}/vote` | `select public.votar_avaliacao(:ator, :candidato, :valor)` | Quem pode ler a versão `compartilhada` (seguidor da turma ou autor) |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/vote` e `GET .../votes` | `select * from public.resumo_votos_versao(:ator, :versao)` | Quem pode ler a versão |
| `DELETE /api/v1/syllabus/{id}/versions/{vid}/candidates/{cid}` | Marca o candidato como `descartado` na versão | Autor da versão ou `admin` |

Compartilhar e retirar compartilhamento são operações idempotentes. A versão inicial (`v1`) de planos vinculados a uma oferta e concluídos com candidatos extraídos é compartilhada automaticamente para os seguidores da turma quando consultada (`GET /api/v1/syllabus/{id}`) ou confirmada (`POST /api/v1/syllabus/{id}/confirm`) pelo autor, salvo se tiver sido retirada anteriormente (`retirada_em` preenchido). Reprocessamentos (`v2+`) e rascunhos de revisão iniciam como `privada`.

**Revisão.** `criar_revisao` cria a próxima versão do plano com `versao_origem_id` preenchido e `autor_papel` com o papel atual de quem revisa, sem alterar eventos pessoais já importados por outros usuários. Quando enviada com candidatos para um plano vinculado a oferta (ou com `share: true`), é publicada como `compartilhada`.

**Conteúdo compartilhado imutável.** Depois de compartilhada, a versão não aceita alteração de títulos ou datas nem inclusão de novos candidatos (`55000`), garantindo consistência para votos e importações. Correções devem ser feitas criando uma revisão. O `status` do candidato permanece editável para permitir retirada lógica pelo autor da versão ou administrador (`DELETE .../candidates/{cid}`).

**Retirada.** Bloqueia novos acessos, votos e importações da versão retirada. Não retira revisões derivadas (cada uma mantém sua própria visibilidade), não apaga votos nem remove eventos pessoais já importados, registrando `retirada_em` e `retirada_por`.

**Procedência institucional.** `autor_papel` e origem institucional são atributos independentes. A procedência institucional só é atribuída por administrador mediante `fonte_institucional_url` pública oficial. Uma revisão feita por professor ou administrador herda a procedência e a evidência da origem; revisões feitas por estudantes não a herdam automaticamente. O banco recusa `procedencia_institucional = true` sem evidência.

## 4. Votos

```python
contagem = chamar(db, "select public.votar_avaliacao(:ator, :candidato, :valor)",
                  ator=current_user.id, candidato=candidate_id,
                  valor={"confirm": "confirma", "contest": "contesta"}[payload.value])
# {"avaliacao_id": "...", "confirmam": 3, "contestam": 1, "meu_voto": "confirma"}
```

- Um voto por conta e candidato (`(user_id, avaliacao_id)`). Votar novamente substitui o próprio voto; repetir o mesmo valor mantém a contagem inalterada.
- Apenas quem pode ler a versão compartilhada pode votar.
- `resumo_votos_versao(:ator, :versao)` devolve `confirmam`, `contestam` e `meu_voto` por candidato.
- O voto individual é privado: pelo navegador, cada conta lê apenas os próprios votos; a API expõe somente contagens agregadas e o indicador `divergent`.
- Votos **não alteram datas automaticamente**; correções exigem criação de uma revisão.
- A gravação recusa avaliações retiradas (`P0002`), e o resumo da versão as omite mantendo os registros anteriores intactos.

## 5. Confirmação idempotente ([ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos))

Na camada HTTP, `POST /api/v1/syllabus/{syllabus_id}/confirm` recebe `ConfirmSyllabusRequest` em `camelCase` (`versionId` opcional e `candidates[]` com `candidateId`, `title`, `description`, `type`, `startsAt`, `allDay`, `start_date`, `end_date`, `category`) e o cabeçalho obrigatório `Idempotency-Key` (8 a 200 caracteres). A API traduz os campos para os parâmetros em português esperados pela função SQL `public.confirmar_importacao(p_ator, p_chave, p_versao, p_itens)` e devolve `ConfirmSyllabusResponse` em `camelCase`.

```python
@router.post("/{syllabus_id}/confirm", response_model=ConfirmSyllabusResponse)
def confirm_syllabus_candidates(
    syllabus_id: UUID,
    payload: ConfirmSyllabusRequest,
    idempotency_key: str = Header(alias="Idempotency-Key", min_length=8, max_length=200),
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConfirmSyllabusResponse:
    # Traduz ConfirmCandidateInput (candidateId, title, type, startsAt, allDay, start_date, end_date)
    # para o JSON esperado por public.confirmar_importacao(:actor_id, :key, :version_id, :items)
    ...
```

Formato da resposta HTTP (`200 OK`):

```json
{
  "syllabusId": "33333333-3333-4333-8333-333333333333",
  "operationId": "11111111-1111-4111-8111-111111111111",
  "repeated": false,
  "items": [
    {
      "candidateId": "44444444-4444-4444-8444-444444444444",
      "eventId": "55555555-5555-4555-8555-555555555555",
      "result": "criado",
      "removed": false,
      "type": "Prova"
    }
  ],
  "events": []
}
```

| Situação | Resultado na resposta |
| --- | --- |
| Primeira confirmação válida | `result: "criado"`, evento gravado em `eventos_pessoais` |
| Mesma chave e mesmo conteúdo | `repeated: true`, mesmo resultado, sem duplicar gravação |
| Mesma chave e conteúdo diferente | HTTP `409` (`AG409`) |
| Outra chave para candidato já importado | `result: "ja_importado"`, mantendo evento único |
| Usuário excluiu o evento e o cliente repete a chave antiga | `repeated: true`, `eventId: null`, `removed: true` (**não recria**) |
| Reimportar após exclusão ("Adicionar novamente") | Exige chave **nova**, retornando `result: "criado"` |
| Candidato de outra versão, repetido, descartado ou data ambígua sem correção | HTTP `422` (`22023`), sem gravação parcial |
| Sem acesso (versão retirada, sem vínculo ou privado alheio) | HTTP `403` (`42501`) |

Regras para clientes HTTP:

- Gere uma chave única por ação do usuário (como `crypto.randomUUID()` ao acionar confirmação) e reutilize a mesma chave apenas em retries daquela ação.
- A chave possui de 8 a 200 caracteres e é isolada por conta.
- A equivalência de conteúdo considera a versão e o payload normalizado dos itens.
- Ações recusadas por validação não são persistidas, permitindo corrigir os dados e reutilizar a mesma chave.

A operação, os itens (`itens_importacao`, incluindo `tipo_revisado`) e os eventos pessoais são gravados na mesma transação, com serialização de confirmações concorrentes por conta. Em versões compartilhadas, a importação e a revisão de tipo pertencem exclusivamente a quem confirma; no fluxo privado do autor, o candidato passa a `confirmado`.

A função SQL `revisar_candidatos_plano(p_plano_id, p_itens)` permanece no banco apenas como compatibilidade interna restrita ao dono autenticado e verificada pela inicialização de segurança (`syllabus/privacy.py`). A API utiliza exclusivamente `confirmar_importacao` para planos privados e versões compartilhadas.

## 6. Extração e persistência de candidatos

- A tabela física única de candidatos é `avaliacoes`.
- O worker grava candidatos com `plano_id`, `versao_id` e `ordem`. Quando `versao_id` é omitido, um trigger associa a versão mais recente do plano. A unicidade `(versao_id, ordem)` evita duplicação em reprocessamentos.
- O worker não grava em versões já compartilhadas (`55000`).
- O vínculo entre candidato e evento pessoal criado nunca altera o candidato compartilhado: é registrado por conta em `eventos_pessoais.origem_avaliacao_id`, `eventos_pessoais.origem_versao_id` e `itens_importacao`.

## 7. Testes

- **Banco (PostgreSQL local):** `backend/tests/test_plan_import_database.py` e `backend/tests/test_plan_sharing_database.py` cobrem importação concorrente, idempotência, isolamento por conta, imutabilidade de versões compartilhadas, retirada sem apagar cópias, revisão, procedência institucional e votos privados (exigem `TEST_SUPABASE_DB_URL` local).
- **API (HTTP):** `backend/tests/test_syllabus_review_api.py`, `backend/tests/test_plan_sharing_api.py` e `backend/tests/test_class_catalog_api.py` cobrem os contratos HTTP, validações e permissões.
