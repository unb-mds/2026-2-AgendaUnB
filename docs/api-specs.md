# Contratos do backend

## Referência e limites

A API possui **15 operações HTTP de aplicação**, incluindo `/health`: 10 presentes na R1 e cinco posteriores. `/docs`, `/redoc` e `/openapi.json` são recursos de documentação gerados pelo FastAPI, não operações de negócio. Consulte também [Arquitetura](Architecture.md), [Padrões](padroes.md) e [Implantação](implantacao.md).

Fontes: `backend/src/main.py`, `modules/events/router.py`, `modules/events/schemas.py`, `middlewares/auth.py` e `database/models.py` (os quatro últimos relativos a `backend/src/`). O OpenAPI ajuda a conferir campos e rotas, mas não descreve integralmente os handlers de erro personalizados.

## Convenções comuns

- Base local: `http://127.0.0.1:8000/api/v1`.
- Corpos JSON usam `Content-Type: application/json`. Rotas autenticadas exigem `Authorization: Bearer <token>` do Supabase Auth.
- Papéis persistidos: `student`, `professor`, `admin`. O servidor obtém o ID da sessão e consulta o papel em `profiles`; o cliente não escolhe a identidade.
- `{event_id}` é UUID. UUID malformado gera falha de validação; UUID válido ausente recebe o comportamento indicado em cada operação.
- GET e DELETE não têm corpo definido; PUT de evento salvo também não. Listas retornam arrays, sem envelope ou total, e listas vazias retornam `[]`.
- Os schemas ignoram campos extras; enviar `status` ou `author_id` não altera os valores definidos pelo servidor. Isso não equivale a rejeitar esses campos com 422.

## Payloads e respostas

### Entrada de evento

`EventCreate` é usado na criação pública e na sugestão. `PersonalEventCreate` e `PersonalEventUpdate` usam os mesmos campos comuns, sem `external_url`.

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `title` | string | Sim | 3–200 caracteres após remoção de espaços nas extremidades; não aceita null |
| `starts_at` | datetime | Sim | Data/hora ISO 8601 com fuso, por exemplo `2026-11-10T14:00:00-03:00`; não aceita null |
| `description` | string ou null | Não | Até 10.000 caracteres; padrão null |
| `campus` | string ou null | Não | Nome existente, 2–120 caracteres; padrão null |
| `category` | string ou null | Não | Nome existente, 2–80 caracteres; padrão null |
| `location` | string ou null | Não | Até 250 caracteres; padrão null; ver limitação dos eventos pessoais |
| `external_url` | URL HTTP/HTTPS ou null | Não | Somente evento público/sugestão; validado por `HttpUrl`; padrão null |

Strings são aparadas. Strings vazias ou contendo somente espaços em `description`, `campus`, `category` e `location` viram null. Isso não se aplica a `external_url`: para ausência de link, omitir ou enviar null. Campus e categoria são resolvidos por nome, ignorando maiúsculas/minúsculas, e não por UUID. Nome desconhecido na escrita retorna 422.

O PUT pessoal exige `title` e `starts_at`, assim como o POST. Não é uma atualização parcial: omitir descrição, campus ou categoria substitui esses valores por null. Não existe PATCH nem rota de atualização pública, embora exista um schema `EventUpdate` sem rota associada.

Exemplo `EventCreate`:

```json
{
  "title": "Encontro de extensão",
  "description": "Apresentação de projetos da comunidade acadêmica.",
  "starts_at": "2026-11-10T14:00:00-03:00",
  "campus": null,
  "category": null,
  "location": "Auditório",
  "external_url": "https://example.org/encontro"
}
```

### Objetos retornados

`EventRead` contém todos os campos abaixo. `id` é UUID e `starts_at` é datetime; `title` é string. Os demais campos aceitam null. A criação pública e a sugestão persistem descrição ausente como string vazia. Autoria e status não aparecem na resposta, embora sejam definidos no banco.

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "title": "Encontro de extensão",
  "description": "Apresentação de projetos da comunidade acadêmica.",
  "starts_at": "2026-11-10T17:00:00Z",
  "campus": null,
  "category": null,
  "location": "Auditório",
  "external_url": "https://example.org/encontro",
  "organizer_name": "Pessoa de exemplo",
  "organizer_avatar": null
}
```

`PersonalEventRead` retorna `id`, `title`, `description`, `starts_at`, `campus`, `category` e `location`, com os mesmos tipos. Não retorna URL externa nem organizador. **Limitação atual:** `location` é aceito na entrada pessoal, mas as rotas não o persistem e o serializador o retorna como null. O cliente não deve esperar que esse valor seja recuperado.

`SavedEventStatus` é `{ "saved": true }` ou `{ "saved": false }`. Respostas 204 não contêm JSON nem outro corpo.

## Inventário HTTP

Nas tabelas, as rotas iniciadas por `/api/v1` usam os schemas acima. Todas as operações que acessam dados podem retornar **503** em falha SQLAlchemy. As autenticadas também podem retornar **401** (sessão ausente/inválida), **403** (perfil ausente) e **503** (validação de sessão indisponível). Esses erros comuns somam-se aos erros específicos listados. Escritas podem retornar **409** se uma constraint produzir `IntegrityError`.

### Eventos públicos — R1

| Método e rota | Acesso | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- | --- |
| `GET /api/v1/events` | Público | Filtros abaixo | 200, `EventRead[]`, somente aprovados, ordenados por início crescente | 422, filtros inválidos |
| `GET /api/v1/events/{event_id}` | Público | UUID no caminho | 200, `EventRead` aprovado | 422, UUID; 404, ausente ou não aprovado |
| `POST /api/v1/events` | Professor/admin | `EventCreate` | 201, `EventRead`; autoria da sessão e status `aprovado` | 403, papel; 422, payload/referências; 409 |
| `DELETE /api/v1/events/{event_id}` | Professor/admin | UUID no caminho | 204; exclui o evento e vínculos em cascata | 403, papel; 422, UUID; 404, ausente; 409 |

A exclusão pública não exige que o gestor seja o autor e não filtra status. A autorização é por papel.

| Query de listagem pública | Tipo e padrão | Semântica |
| --- | --- | --- |
| `campus` | string opcional, 2–120 caracteres | Nome exato sem diferenciar caixa, aparado; nome desconhecido produz lista vazia |
| `category` | string opcional, 2–80 caracteres | Mesma regra de campus |
| `startDate` | datetime opcional | Limite inferior inclusivo sobre `starts_at`; exige fuso |
| `endDate` | datetime opcional | Limite superior inclusivo; exige fuso e não pode preceder `startDate` |
| `q` | string opcional, 1–120 caracteres | Busca no título via `ILIKE '%texto%'`; `%` e `_` conservam semântica de curingas SQL |
| `limit` | inteiro, padrão 50 | De 1 a 100 |
| `offset` | inteiro, padrão 0 | Maior ou igual a zero |

Não há filtro de turno no backend: ele é aplicado pela interface. O frontend percorre páginas de 100; a API não fornece total nem cursor. A ordenação pública usa apenas data, sem desempate por ID.

### Agenda pessoal — R1

Todas as operações exigem sessão e restringem os dados ao usuário autenticado.

| Método e rota | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- |
| `GET /api/v1/me/events` | Sem parâmetros definidos | 200, `PersonalEventRead[]`, início crescente, sem paginação | Erros comuns |
| `GET /api/v1/me/events/{event_id}` | UUID | 200, `PersonalEventRead` | 422, UUID; 404, ausente ou de outro usuário |
| `POST /api/v1/me/events` | `PersonalEventCreate` | 201, `PersonalEventRead` | 422, payload/referências; 409 |
| `PUT /api/v1/me/events/{event_id}` | UUID + `PersonalEventUpdate` | 200, `PersonalEventRead` | 422, UUID/payload/referências; 404, ausente ou de outro usuário; 409 |
| `DELETE /api/v1/me/events/{event_id}` | UUID | 204 | 422, UUID; 404, ausente ou de outro usuário; 409 |

### Sugestões — pós-R1

| Método e rota | Acesso e entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- |
| `POST /api/v1/suggestions` | Somente `student`; `EventCreate` | 201, `EventRead`; autoria da sessão, status `pendente`, notificação via trigger | 403, papel; 422, payload/referências; 409 |

Receber 201 não significa aprovação. O item não aparece no catálogo até ser aprovado pela RPC de moderação.

### Eventos salvos — pós-R1

Todas as operações exigem sessão. O vínculo não copia o evento e não constitui inscrição.

| Método e rota | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- |
| `GET /api/v1/me/saved-events` | Sem parâmetros definidos | 200, `EventRead[]`, somente aprovados vinculados; ordem por início e ID; sem paginação | Erros comuns |
| `GET /api/v1/me/saved-events/{event_id}` | UUID | 200, `SavedEventStatus`; false se vínculo ausente, evento inexistente ou não aprovado | 422, UUID |
| `PUT /api/v1/me/saved-events/{event_id}` | UUID, sem corpo | 200, `{ "saved": true }`, inclusive se já salvo | 422, UUID; 404, evento ausente/não aprovado; 409, conflito não recuperável |
| `DELETE /api/v1/me/saved-events/{event_id}` | UUID | 204, inclusive se não houver vínculo/evento | 422, UUID; 409 |

PUT e DELETE são idempotentes. O PUT recupera colisão de inserção concorrente quando o vínculo já foi criado. DELETE só remove o vínculo do usuário atual.

### Saúde — R1

`GET /health`: público, sem parâmetros ou corpo, retorna 200 com `{ "status": "ok" }`. Não consulta banco nem Auth; não é uma verificação de prontidão de todas as dependências.

## Erros FastAPI

| HTTP | Situação | Formato |
| --- | --- | --- |
| 401 | Bearer ausente, sessão expirada/inválida ou identidade inválida retornada pelo Auth | `{"detail":"mensagem"}` |
| 403 | Perfil não encontrado ou papel sem permissão | `{"detail":"mensagem"}` |
| 404 | Recurso não disponível conforme as regras da operação | `{"detail":"mensagem"}` |
| 409 | `IntegrityError` não recuperado pela operação | `{"detail":"A operação conflita com os dados existentes."}` |
| 422 | Validação automática de payload/path/query | `detail` textual e array `errors` de erros Pydantic |
| 422 | Regra explícita: campus/categoria desconhecido ou intervalo inválido | Somente `detail` textual |
| 503 | Falha SQLAlchemy ou comunicação/configuração do Auth | `{"detail":"mensagem"}` |

Exemplo de validação de título curto:

```json
{
  "detail": "Título: deve ter pelo menos 3 caracteres",
  "errors": [{
    "type": "string_too_short",
    "loc": ["body", "title"],
    "msg": "String should have at least 3 characters",
    "input": "AB",
    "ctx": {"min_length": 3}
  }]
}
```

O conteúdo auxiliar de `errors` depende da versão do Pydantic, que não está fixada nas dependências. Erros inesperados não têm envelope de aplicação garantido. **Dívida conhecida:** o handler passa `exc.errors()` diretamente a `JSONResponse`; erros de validadores com objetos não serializáveis em `ctx` podem resultar em 500, apesar da intenção de retornar 422. A especificação não promete 422 para esse caso sem correção e teste específicos. Não há contrato implementado de processamento assíncrono com 202.

## Exemplos cURL

Exemplos para Bash/Git Bash, com IDs fictícios. Substitua o token e use o ID real devolvido por um POST; não envie dados pessoais reais em demonstrações.

```bash
API='http://127.0.0.1:8000/api/v1'
TOKEN='<token-da-sessao>'
EVENT_ID='11111111-1111-4111-8111-111111111111'

curl --get "$API/events" --data-urlencode 'startDate=2026-11-01T00:00:00-03:00' --data-urlencode 'limit=20'
curl "$API/events/$EVENT_ID"
curl -X POST "$API/events" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Encontro de extensão","starts_at":"2026-11-10T14:00:00-03:00"}'
curl -i -X DELETE "$API/events/$EVENT_ID" -H "Authorization: Bearer $TOKEN"

curl "$API/me/events" -H "Authorization: Bearer $TOKEN"
curl "$API/me/events/$EVENT_ID" -H "Authorization: Bearer $TOKEN"
curl -X POST "$API/me/events" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Estudo em grupo","starts_at":"2026-11-10T14:00:00-03:00"}'
curl -X PUT "$API/me/events/$EVENT_ID" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Estudo revisado","starts_at":"2026-11-11T14:00:00-03:00","description":null}'
curl -i -X DELETE "$API/me/events/$EVENT_ID" -H "Authorization: Bearer $TOKEN"

curl -X POST "$API/suggestions" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"Proposta de encontro","starts_at":"2026-11-10T14:00:00-03:00"}'
curl "$API/me/saved-events" -H "Authorization: Bearer $TOKEN"
curl "$API/me/saved-events/$EVENT_ID" -H "Authorization: Bearer $TOKEN"
curl -X PUT "$API/me/saved-events/$EVENT_ID" -H "Authorization: Bearer $TOKEN"
curl -i -X DELETE "$API/me/saved-events/$EVENT_ID" -H "Authorization: Bearer $TOKEN"
curl 'http://127.0.0.1:8000/health'
```

## Contratos Supabase separados da API FastAPI

O frontend usa o SDK autenticado, conforme `frontend/src/lib/moderation.js`. As quatro RPCs abaixo são definidas na migração `20261018000000_moderacao_e_notificacoes.sql`. Não existem rotas FastAPI `/admin` ou de decisão de sugestão. Funções auxiliares/legadas do banco não são enumeradas como operações da interface.

| RPC | Acesso | Parâmetros | Resultado |
| --- | --- | --- | --- |
| `listar_sugestoes` | Professor/admin | `p_status` texto, padrão `pendente`, valores `pendente/aprovado/rejeitado`; `p_busca` texto, padrão vazio; `p_offset` inteiro ≥0, padrão 0 | `{items, total, pending}`; páginas de 20, ordem por criação crescente e ID; busca título/autor; `pending` é contagem global de sugestões pendentes |
| `moderar_sugestao` | Professor/admin | `p_evento_id` UUID e `p_status` texto obrigatórios (`aprovado/rejeitado`); `p_justificativa` texto opcional, padrão null | Retorno SQL void; só decide sugestão pendente; recusa exige texto aparado de 1–2.000 caracteres; aprovação limpa justificativa |
| `admin_buscar_usuarios` | Admin | `p_busca` texto vazio; `p_papel` vazio ou `student/professor/admin`; `p_confirmado` vazio ou `sim/nao`; `p_offset` inteiro ≥0, padrão 0 | `{items, total, all, unconfirmed}`; 20 por página, criação decrescente e ID; busca nome/e-mail; `all` e `unconfirmed` independem dos filtros |
| `admin_definir_papel` | Admin | `p_usuario_id` UUID, `p_novo_papel` e `p_papel_atual` textos obrigatórios; papéis `student/professor/admin` | Retorno SQL void; bloqueia linha, compara cargo atual e chama `admin_alterar_papel`; impede rebaixar a própria conta admin |

Enviar filtros opcionais omitidos ou com seus padrões, não null como substituto indiscriminado. Itens de sugestão: `id`, `titulo`, `descricao`, `data_evento`, `localizacao`, `link_externo`, `status`, `justificativa_recusa`, `criado_em`, `autor_nome`, `campus`, `categoria`. Itens de usuário: `id`, `email`, `nome_completo`, `papel`, `criado_em`, `ultimo_login` (pode ser null), `email_confirmado` booleano. Listas vazias têm `items: []` e contagens numéricas.

Exemplo de chamada e resposta vazia:

```javascript
const { data, error } = await supabase.rpc('listar_sugestoes', {
  p_status: 'pendente', p_busca: '', p_offset: 0,
});
// data: { items: [], total: 0, pending: 0 }
// Sempre verificar error antes de usar data.
```

Erros SQL explícitos incluem `42501` (permissão), `22023` (filtro, papel ou decisão inválidos) e `P0002` (sugestão indisponível/já decidida ou perfil alterado/ausente). O SDK também pode retornar erros de sessão, como `PGRST301`. São códigos do Supabase/PostgreSQL, não códigos HTTP nem o envelope FastAPI; o consumidor verifica `error.code`/`error.message`. A migração `20261018000100` permite ao admin atribuir professor a e-mail externo, preservando a restrição institucional no cadastro/autopromoção.

### Notificações

O SDK consulta `notificacoes` diretamente, filtrando `usuario_id`, com contagem exata, ordem `criado_em` decrescente e ID crescente, e intervalo inclusivo `page*20` a `page*20+19`. Uma segunda consulta conta não lidas (`lida_em IS NULL`). O wrapper retorna `{items, total, unread}`.

Cada item tem `id`, `usuario_id`, `evento_id`, `tipo` (`submissao/aprovacao/recusa`), `titulo_evento`, `justificativa`, `criado_em` e `lida_em`. O banco permite ao destinatário apenas leitura e atualização de `lida_em`; a interface marca IDs próprios ainda não lidos com timestamp ISO. RLS e permissões de coluna fazem a proteção, não apenas o filtro do cliente. Triggers geram avisos na mesma transação da submissão/decisão. Não são lembretes programados.

## Verificação e manutenção

Conferir inventário com `app.openapi()` e revisar manualmente handlers, permissões e SQL. Os testes de eventos, sugestões e salvos usam SQLite e substituem dependências de autenticação: não comprovam integração real com Auth nem RLS. Os testes de moderação de banco exigem Supabase local descartável. Ver [Contribuição](CONTRIBUTING.md) e o registro de validação em [Arquitetura](Architecture.md#9-verificacao).

Qualquer alteração de rota, schema, autorização, erro ou RPC deve atualizar este documento no mesmo PR. Upload/parser, inscrições, categorias REST e atualização pública não são contratos disponíveis.
