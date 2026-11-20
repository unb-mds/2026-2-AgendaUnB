# Contratos do backend

## Referência e limites

Este inventário descreve o backend atual. Para as decisões de produto e os fluxos integrados, consulte [Release 2](/atualizacoes#contratos-da-release-2).

A API possui operações HTTP de aplicação (inventário abaixo), incluindo `/health`. `/docs`, `/redoc` e `/openapi.json` são recursos de documentação gerados pelo FastAPI, não operações de negócio. Consulte também [Arquitetura](/arquitetura/visao-geral), [Padrões](/produto/padroes) e [Implantação](/implantacao).

Fontes: `backend/src/main.py`, `modules/events/router.py`, `modules/events/schemas.py`, `modules/google_calendar/router.py`, `middlewares/auth.py` e `database/models.py` (relativos a `backend/src/`). O OpenAPI ajuda a conferir campos e rotas, mas não descreve integralmente os handlers de erro personalizados.

## Convenções comuns

- Base local: `http://127.0.0.1:8000/api/v1`.
- Corpos JSON usam `Content-Type: application/json`. Rotas autenticadas exigem `Authorization: Bearer <token>` do Supabase Auth.
- Papéis persistidos: `student`, `professor`, `admin`. O servidor obtém o ID da sessão e consulta o papel em `profiles`; o cliente não escolhe a identidade.
- Toda rota autenticada exige e-mail confirmado no Supabase Auth. Metadata nunca concede `admin`; `professor` só é aceito como solicitação após confirmação do endereço real `@unb.br` da conta Auth. Uma pessoa pode mudar o próprio papel de estudante para professor com esse e-mail confirmado; papel de terceiros só muda pela RPC de admin.
- `{event_id}` é UUID. UUID malformado gera falha de validação; UUID válido ausente recebe o comportamento indicado em cada operação.
- Toda resposta leva cabeçalhos de proteção (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`); respostas com dados da conta levam `Cache-Control: no-store`. O CORS aceita somente as origens de `CORS_ORIGINS` e os cabeçalhos `Authorization`, `Content-Type`, `Accept` e `Idempotency-Key`. Detalhes em [Verificação de segurança](processo/seguranca.md).
- A busca `q` trata `%` e `_` como texto.
- GET e DELETE não têm corpo definido; PUT de evento salvo também não. Listas de eventos retornam arrays, e listas vazias retornam `[]`. A listagem de planos usa um envelope de paginação.
- Os schemas ignoram campos extras; enviar `status` ou `author_id` não altera os valores definidos pelo servidor. Isso não equivale a rejeitar esses campos com 422.

## Payloads e respostas

### Entrada de evento

`EventCreate` é usado na criação pública e na sugestão. `PersonalEventCreate` e `PersonalEventUpdate` usam os mesmos campos comuns, sem `external_url`.

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `title` | string | Sim | 3–200 caracteres após remoção de espaços nas extremidades; não aceita null |
| `all_day` | boolean | Não | Padrão `false`. Quando `true`, exige `start_date` (e `end_date` exclusivo opcional) e recusa `starts_at`/`ends_at` |
| `starts_at` | datetime ou null | Condicional | Obrigatório quando `all_day = false`; data/hora ISO 8601 com fuso, por exemplo `2026-11-10T14:00:00-03:00` |
| `ends_at` | datetime ou null | Não | Somente quando `all_day = false`; data/hora ISO 8601 com fuso e posterior a `starts_at` |
| `start_date` | date (`YYYY-MM-DD`) ou null | Condicional | Obrigatório quando `all_day = true`; início civil em `America/Sao_Paulo` |
| `end_date` | date (`YYYY-MM-DD`) ou null | Não | Somente quando `all_day = true`; fim civil exclusivo posterior a `start_date` (padrão `start_date + 1 dia`) |
| `description` | string ou null | Não | Até 10.000 caracteres; padrão null |
| `campus` | string ou null | Não | Nome existente, 2–120 caracteres; padrão null |
| `category` | string ou null | Não | Nome existente, 2–80 caracteres; padrão null |
| `location` | string ou null | Não | Até 250 caracteres; persistido em eventos públicos e pessoais (`20261117200000`). |
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

`PersonalEventRead` retorna `id`, `title`, `description`, `starts_at`, `ends_at`, `all_day`, `start_date`, `end_date`, `campus`, `category`, `location` e `origin`, com persistência completa de `location` e intervalos após a migração `20261117200000`. Não retorna URL externa nem organizador. Eventos de dia inteiro preenchem `all_day = true`, `start_date` e `end_date` exclusivo em `America/Sao_Paulo`, além de manterem `starts_at`/`ends_at` normalizados na meia-noite de Brasília para ordenação e filtros ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)).

`EventRead` inclui também `ends_at`, `all_day`, `start_date`, `end_date`, `source`, `source_url` e `outbound_clicks_count`.

`SavedEventStatus` é `{ "saved": true }` ou `{ "saved": false }`. Respostas 204 não contêm JSON nem outro corpo.

## Inventário HTTP

Nas tabelas, as rotas iniciadas por `/api/v1` usam os schemas acima. Todas as operações que acessam dados podem retornar **503** em falha SQLAlchemy. As autenticadas também podem retornar **401** (sessão ausente/inválida), **403** (perfil ausente) e **503** (validação de sessão indisponível). Esses erros comuns somam-se aos erros específicos listados. Escritas podem retornar **409** se uma constraint produzir `IntegrityError`.

### Eventos públicos — R1

| Método e rota | Acesso | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- | --- |
| `GET /api/v1/events` | Público | Filtros abaixo | 200, `EventRead[]`, somente aprovados, ordenados por início crescente | 422, filtros inválidos |
| `GET /api/v1/events/{event_id}` | Público | UUID no caminho | 200, `EventRead` aprovado | 422, UUID; 404, ausente ou não aprovado |
| `POST /api/v1/events/{event_id}/outbound-clicks` | Público | UUID + `{"click_id": UUID}` | 200, `{external_url, outbound_clicks_count, incremented}` (deduplicado por `click_id`) | 422, sem link oficial; 404, ausente/não aprovado |
| `POST /api/v1/events` | Professor/admin | `EventCreate` | 201, `EventRead`; autoria da sessão e status `aprovado` | 403, papel; 422, payload/referências; 409 |
| `DELETE /api/v1/events/{event_id}` | Professor/admin | UUID no caminho | 204; exclui o evento e vínculos em cascata | 403, papel; 422, UUID; 404, ausente; 409 |
| `GET /api/v1/categories` | Público | — | 200, `CategoryRead[]` | — |
| `POST /api/v1/categories` | Admin | `CategoryCreate` (`name`, `color`) | 201, `CategoryRead` | 403, papel; 409, nome duplicado; 422 |
| `DELETE /api/v1/categories/{category_id}` | Admin | UUID no caminho | 204 | 403, papel; 404, ausente; 409, categoria em uso |

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

### Eventos salvos — pós-R1 {#eventos-salvos-pos-r1}

Todas as operações exigem sessão. O vínculo não copia o evento e não constitui inscrição.

| Método e rota | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- |
| `GET /api/v1/me/saved-events` | Sem parâmetros definidos | 200, `EventRead[]`, somente aprovados vinculados; ordem por início e ID; sem paginação | Erros comuns |
| `GET /api/v1/me/saved-events/{event_id}` | UUID | 200, `SavedEventStatus`; false se vínculo ausente, evento inexistente ou não aprovado | 422, UUID |
| `PUT /api/v1/me/saved-events/{event_id}` | UUID, sem corpo | 200, `{ "saved": true }`, inclusive se já salvo | 422, UUID; 404, evento ausente/não aprovado; 409, conflito não recuperável |
| `DELETE /api/v1/me/saved-events/{event_id}` | UUID | 204, inclusive se não houver vínculo/evento; cancela lembretes futuros pendentes do vínculo | 422, UUID; 409 |

PUT e DELETE são idempotentes. O PUT recupera colisão de inserção concorrente quando o vínculo já foi criado. DELETE só remove o vínculo do usuário atual.

### Planos de ensino

As operações exigem autenticação. Planos privados ficam restritos ao autor; versões compartilhadas podem ser consultadas e importadas por contas que seguem a oferta da turma.

| Operação | Entrada | Resposta |
| --- | --- | --- |
| `POST /api/v1/syllabus/upload` | `multipart/form-data` com `file` (PDF), `disciplina`, `turma`, `ano` (2000 a 2100) e `semestre` (1 ou 2). `file` e `offering_id` são obrigatórios; disciplina, turma e período são derivados da oferta disponível. | 202, plano registrado como `pendente`. Ano e semestre são persistidos quando informados. |
| `GET /api/v1/syllabus` | `limit` de 1 a 100 (padrão 20), `offset` a partir de 0 (padrão 0). | 200, `{ "items": [], "total": 0, "limit": 20, "offset": 0 }` para uma lista vazia. Ordena por criação e ID decrescentes. |
| `GET /api/v1/syllabus/{syllabus_id}` | UUID do plano. | 200, dados e candidatos da versão aprovada. Para compartilhamento, aplica a permissão por autor/seguidor; 404 para versões indisponíveis. |
| `POST /api/v1/syllabus/{syllabus_id}/confirm` | Cabeçalho `Idempotency-Key` (8 a 200 caracteres) e `candidates` selecionados, com `candidateId`, `title`, `description`, `type`, `startsAt` e `category` opcionais. Datas com instante incluem fuso ISO 8601. | 200, `{ operationId, repeated, items, events }`. A resposta indica candidatos criados/importados, evento removido e procedência. Reutilize a mesma chave somente ao repetir a mesma ação; use chave nova para uma nova confirmação após excluir o evento. |
| `DELETE /api/v1/syllabus/{syllabus_id}/candidates/{candidate_id}` | UUIDs do plano privado concluído e do candidato. | 204, marca o candidato como descartado sem remover sua evidência. Não descarta decisões de versões compartilhadas. |

A listagem e o detalhe retornam `ano` e `semestre`, derivados da oferta para novos envios. O limite é de 10 envios em cinco dias (429 ao exceder). O backend guarda texto sanitizado e dados de acompanhamento após descartar o PDF. `filePath` é sempre `null`, inclusive em planos legados.

### Conta e privacidade — S8-D01

| Método | Rota | Acesso | Resposta |
| --- | --- | --- | --- |
| `GET` | `/api/v1/me/legal-documents` | Autenticado | 200 com a versão vigente e a aceita de cada documento |
| `PUT` | `/api/v1/me/legal-acceptances/{terms\|privacy}` | Autenticado | 204; 409 se a versão enviada não é a vigente |
| `GET` | `/api/v1/me/consents` | Autenticado | 200 com os consentimentos opcionais registrados |
| `DELETE` | `/api/v1/me/consents/{purpose}` | Autenticado | 204; revoga consentimento opcional (ex.: `google_agenda`) |
| `GET` | `/api/v1/me/data-export` | Autenticado | 200 com o JSON dos dados da conta, para download |
| `DELETE` | `/api/v1/me` | Autenticado | 204; 422 sem a frase de confirmação; 409 para o último administrador |

Detalhes em [Privacidade e ciclo de vida dos dados](/processo/privacidade#direitos-do-titular-na-api-e-na-interface).

### Saúde — R1

`GET /health`: público, sem parâmetros ou corpo, retorna 200 com `{ "status": "ok" }`. Não consulta banco nem Auth; não é uma verificação de prontidão de todas as dependências.

### Exportação para o Google Calendar

O login Google do Supabase solicita identidade. A permissão do Calendar é opcional e começa em **Meus Eventos**, para qualquer sessão com e-mail confirmado, inclusive por senha. O cliente OAuth do Calendar usa um projeto Google Cloud separado do login. Todas as respostas deste grupo aplicam `Cache-Control: no-store`.

| Operação | Entrada | Resposta |
| --- | --- | --- |
| `POST /api/v1/me/google-calendar/authorization` | Bearer Supabase. | 200 com `authorization_url` e `expires_in_seconds`. O desafio de uso único usa `state` e PKCE S256 e expira em 10 minutos. |
| `GET /api/v1/me/google-calendar/callback` | Query string do Google com `state` e `code` ou `error`. O POST com formulário continua aceito para autorizações em trânsito. | 303 para a URL configurada com `google_calendar` indicando o resultado. Confere o escopo `calendar.app.created` e o e-mail Google verificado com o e-mail confirmado atual da Agenda UnB. |
| `GET /api/v1/me/google-calendar/connection` | Bearer Supabase. | 200 com `connected` e `recovery_required`. |
| `DELETE /api/v1/me/google-calendar/connection` | Bearer Supabase. | 200 com `disconnected` e `revocation`. Revoga o acesso no Google, remove as credenciais locais e invalida autorizações em andamento. Se a revogação remota falhar, o retorno orienta removê-la na Conta Google. |
| `PUT /api/v1/me/google-calendar/destination` | Bearer Supabase e `calendar_id` (string ou `null`). | 204 após validar no Google o ID da agenda secundária Agenda UnB. Se o usuário confirmar que a agenda não existe ou foi excluída, envia `calendar_id: null` para limpar o destino e invalidar os mapeamentos do calendário anterior em `google_calendar_event_exports`, liberando nova criação. |
| `POST /api/v1/me/google-calendar/exports/preview` | Bearer Supabase e JSON com `events` (1 a 20 referências `{ id, kind }`, onde `kind` é `personal` ou `saved`), `include_description` (booleano opcional, padrão `false`), `start_date` e `end_date` opcionais (`YYYY-MM-DD`). | 200 com `requires_overwrite_confirmation` (booleano) e `items: [{ id, kind, action }]`. `action` é `create` (ainda não exportado para o destino atual ou com estado `pending`/`failed`), `update` (`exported_version` diverge do hash SHA-256 canônico atual dos campos geridos) ou `unchanged` (`exported_version` idêntico ao atual). |
| `POST /api/v1/me/google-calendar/exports` | Bearer Supabase, cabeçalho opcional `Idempotency-Key` (até 128 caracteres) e JSON com `events` (1 a 20 referências `{ id, kind }`), `allow_managed_field_updates` (booleano opcional, padrão `false`), `include_description` (booleano opcional, padrão `false`), `start_date` e `end_date` opcionais (`YYYY-MM-DD`). | 200 com lista `{ id, kind, status }` por item. Estados: `exported` (criado ou reconciliado após `409 Conflict`), `updated` (atualizado via `PUT` remoto quando `allow_managed_field_updates = true`), `already_exported` (inalterado ou já exportado quando `allow_managed_field_updates = false`) ou `failed`. |

O servidor consulta apenas eventos pessoais do dono (`eventos_pessoais`) e eventos públicos aprovados que ele salvou (`eventos_salvos`), opcionalmente filtrados pelo período civil `[start_date, end_date]` em `America/Sao_Paulo`. A exportação cria ou reutiliza a agenda secundária **Agenda UnB** e grava o mapeamento por item em `google_calendar_event_exports` (`user_id`, `event_kind`, `local_event_id`, `calendar_id`, `google_event_id`, `exported_version`, `status`, `last_idempotency_key`).

Cada evento recebe um identificador determinístico compatível com a regra `base32hex` (`a-v0-9`) do Google Calendar (`sha256("{user_id}:{kind}:{event_id}").hexdigest()`) e um hash de versão (`exported_version`) calculado sobre o JSON canônico dos campos geridos (`summary`, `description`, `location`, `start`, `end`):
- **Datas e intervalos ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)):** eventos de dia inteiro (`all_day = true`) enviam `start.date` e `end.date` exclusivo (`YYYY-MM-DD`); eventos com horário enviam `dateTime` e `timeZone: "America/Sao_Paulo"`, usando `ends_at` quando posterior a `starts_at` ou duração padrão de 1 hora.
- **Campos opcionais e privacidade (RNF02):** `location` só é incluído no payload quando houver texto não vazio; `description` só é incluído quando `include_description = true` e houver descrição não vazia (nunca inclui PDF, texto integral de planos, dados de terceiros ou tokens).
- **Idempotência, reexportação e falhas ([ADR-012](/arquitetura/adrs/adr-012-exportacao-google-idempotente)):** antes da chamada externa, o item é registrado como `pending`. Se o Google retornar `409 Conflict` (ex.: retry após timeout de criação), o servidor reconcilia o registro ou atualiza via `PUT` (com `status: "confirmed"`) se `allow_managed_field_updates = true`. Respostas `429` (ou `403` por limite de taxa) aguardam `Retry-After` limitado a 2 segundos com 1 nova tentativa; `404`/`410` na agenda secundária marcam `recovery_required = true` e retornam `409` orientando recriação do destino; `401`/`403` de permissão revogada ou `invalid_grant` limpam as credenciais locais e retornam `409` pedindo reconexão. Exclusões locais não apagam cópias já existentes no Google Agenda. Em **Meus Eventos**, o frontend oferece também exportação complementar em arquivo `.ics` (RFC 5545) para Apple Calendar e Outlook.

## Erros FastAPI

| HTTP | Situação | Formato |
| --- | --- | --- |
| 401 | Bearer ausente, sessão expirada/inválida ou identidade inválida retornada pelo Auth | `{"detail":"mensagem"}` |
| 403 | Perfil não encontrado, e-mail ainda não confirmado ou papel sem permissão | `{"detail":"mensagem"}` |
| 404 | Recurso não disponível conforme as regras da operação | `{"detail":"mensagem"}` |
| 409 | `IntegrityError` não recuperado pela operação | `{"detail":"A operação conflita com os dados existentes."}` |
| 422 | Validação automática de payload/path/query | `detail` textual e array `errors` de erros Pydantic |
| 422 | Regra explícita: campus/categoria desconhecido ou intervalo inválido | Somente `detail` textual |
| 413 | Corpo acima de 256 KiB fora do upload de planos (`MAX_JSON_BODY_BYTES`) | `{"detail":"mensagem"}` |
| 429 | Limite de requisições por cliente (cabeçalho `Retry-After`) ou mais de 10 sugestões pendentes da mesma conta | `{"detail":"mensagem"}` |
| 503 | Falha SQLAlchemy ou comunicação/configuração do Auth | `{"detail":"mensagem"}` |

Falhas de configuração OAuth também retornam 503. Falha temporária com Google pode retornar 502/503; autorização expirada/revogada pede reconexão (409). O callback sempre redireciona com estado genérico e não repassa `error_description`, código ou tokens.

Exemplo de validação de título curto:

```json
{
  "detail": "Título: deve ter pelo menos 3 caracteres",
  "errors": [{
    "type": "string_too_short",
    "loc": ["body", "title"],
    "msg": "String should have at least 3 characters"
  }]
}
```

O array `errors` inclui somente `type`, `loc` e `msg`. Falhas inesperadas recebem 500 com `detail` genérico. A validação evita devolver entrada bruta e contexto de exceções.

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
| `listar_revisoes_coleta` | Professor/admin | `p_status` (`pendente/aprovado/rejeitado`), `p_offset` inteiro ≥0 | `{items, total}` com itens coletados da Agenda UnB Notícias em revisão |
| `admin_listar_categorias` | Admin | — | Lista de categorias com `id`, `nome`, `cor` e `events_count` |
| `admin_criar_categoria` | Admin | `p_nome` texto (2–80), `p_cor` hex `#rrggbb` | Cria e retorna categoria (`42501` fora de admin; `22023` duplicada) |
| `admin_excluir_categoria` | Admin | `p_categoria_id` UUID | Retorno void; bloqueia exclusão se houver eventos vinculados |
| `registrar_redirecionamento_evento` | Público | `p_evento_id` UUID, `p_click_id` UUID | Incrementa `interessados_count` apenas no primeiro acionamento por `(event_id, click_id)` |

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

## Lembretes da agenda

| Rota | Resultado |
| --- | --- |
| `GET /api/v1/me/reminders?limit=20&offset=0` | **200** com um array de lembretes disparados da sessão, ordenado por disparo e ID decrescentes. `limit` aceita de 1 a 100. `offset` é um inteiro de 0 a 2147483647. |
| `PUT /api/v1/me/reminders/{id}/read` | **200** com `{id, read_at}`. A primeira leitura permanece em novas tentativas. O mesmo **404** é usado para IDs alheios, pendentes e inexistentes. |

Cada item traz `id`, `event_kind` (`personal` ou `saved_public`), `event_id`, `title`, `starts_at`, `scheduled_at` e `read_at`. `starts_at` é o início usado no agendamento. `title` pode ser nulo quando o título atual está indisponível para aquela conta. `read_at` nulo indica aviso não lido.

As duas rotas exigem uma sessão válida e um perfil com e-mail confirmado. Retornam **401** sem sessão, **403** para perfil indisponível ou com e-mail pendente de confirmação e **422** para parâmetros inválidos. Respostas de sucesso incluem `Cache-Control: no-store`. O scheduler opera no banco, conforme o [guia de implantação](/implantacao#publicacao-jobs-e-recuperacao).

## Verificação e manutenção

Conferir inventário com `app.openapi()` e revisar manualmente handlers, permissões e SQL. Os testes de eventos, sugestões e salvos usam SQLite e substituem dependências de autenticação: não comprovam integração real com Auth nem RLS. Os testes de moderação de banco exigem Supabase local descartável. Ver [Contribuição](/processo/contribuindo) e o registro de validação em [Arquitetura](/arquitetura/visao-geral#9-verificacao).

Qualquer alteração de rota, schema, autorização, erro ou RPC deve atualizar este documento no mesmo PR. A inscrição acontece na fonte oficial. Alterar eventos públicos exige perfil autorizado e a gestão de categorias exige `admin`.

## Planos particulares — atualização S6-B01 (09/11/2026)

### POST `/api/v1/syllabus/upload`

Autenticação obrigatória. Recebe `multipart/form-data` com `file` PDF e campos
`offering_id` obrigatório, com disciplina e turma derivadas do catálogo. Valida extensão, MIME, assinatura, integridade,
senha, tamanho (10 MB), quantidade (dez páginas) e presença de texto selecionável.
Lê no máximo limite + 1 byte antes de rejeitar excesso. O parser roda em processo
separado com prazo de 8s (`SYLLABUS_UPLOAD_VALIDATION_TIMEOUT_SECONDS`); a espera
e o acesso síncrono ao Storage/banco não bloqueiam o event loop da API.
Salva o arquivo no bucket privado e a linha do dono como `pendente`; retorna
**202**, sem esperar por IA. Se o banco falhar, compensa o arquivo no Storage.

Resposta: `id`, `userId`, `fileName`, `filePath`, `fileSize`, `fileType`, `status`,
`createdAt` e `message`. `filePath` é referência privada, não URL pública assinada.
401 sem sessão; 400 arquivo inválido/protegido/sem texto/excesso de páginas; 413
excesso de bytes; 422 prazo de pré-validação excedido; 502/503 indisponibilidade
de Storage, banco ou processo de validação. Timeout/falha da pré-validação não
persistem arquivo ou tarefa. A pré-validação é aguardada antes do 202; o prazo
inclui criação do processo e admite até 2,2s adicionais para encerrá-lo.

### GET `/api/v1/syllabus/{syllabus_id}`

Autenticado e restrito ao proprietário: UUID válido de outro dono ou inexistente
retorna **404**. Retorna metadados do upload e `status`, `extractedEventsCount`,
`errorMessage`, `errorCode`, `pageCount`, `attempts`, `processingStartedAt`,
`processedAt`, `processingDurationMs`, `totalDurationMs`, `disciplina` e `turma`. Campos ainda não
disponíveis são nulos; `attempts` começa em zero. Estados: `pendente`,
`processando`, `concluido` e `falha`. Erros são mensagens fixas e códigos da S6-D01.
Concluído com contagem zero significa documento sem cronograma identificado.
`processingDurationMs` mede a última tentativa; `totalDurationMs` mede da criação
do registro ao término, incluindo fila/retentativas, e é nulo antes de finalizar.

O [worker independente](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia) consome a fila. Ele fica
desativado até a configuração explícita e a validação das políticas S6-D02.
Upload e worker não criam compromissos. As rotas de listagem, detalhe e confirmação
S6-B02 já existentes, descritas acima, operam sobre `avaliacoes` legadas; os
candidatos privados do worker em `candidatos_avaliacao` ainda exigem conciliação
com esse contrato antes da integração no ambiente da equipe.
O contrato transacional de banco S6-D02 já está disponível em
[`revisar_candidatos_plano`](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos).


## Atualização S7-B01 — preparação e autorização do texto (10/11/2026)

Este contrato substitui o fluxo de upload/extração S6 descrito acima.

| Operação | Entrada | Resultado |
| --- | --- | --- |
| `POST /api/v1/syllabus/upload` | Multipart PDF validado, até 10 MiB/dez páginas; metadados existentes | 202, texto preparado privado, `filePath: null`, `authorizationRequired: true`, `preparedTextAvailable: true`. O PDF é descartado e não vai ao Storage. |
| `POST /api/v1/syllabus/text` | JSON `text` e `offering_id` obrigatórios; até 40.000 bytes UTF-8 | 202, preparação privada, `fileType: text`; página de origem nula. |
| `GET /api/v1/syllabus/{id}/text` | Sessão do dono | 200 com `pages: [{pagina, texto}]`, `textHash`, `authorizationRequired`, `provider`, `providerAvailable`, `maxTextBytes`, `warning`, `preparationDurationMs`, `textRevision` e `redactedCount`. Resposta `no-store`. |
| `POST /api/v1/syllabus/{id}/extractions` | JSON `pages`, `textHash`, `authorize: true`, `reprocess` opcional | 202, autorização registrada e elegibilidade para a fila persistente. Repetir o mesmo hash sem reprocessar não cria execução adicional. |

O hash usa SHA-256 do JSON UTF-8 compacto, com `pagina`/`texto` nessa ordem em
cada página; não é assinatura de autorização. O servidor valida sessão, propriedade, limites,
referências e integridade, recusa identificadores comuns ainda
presentes e não altera o texto aprovado antes de enviá-lo ao provedor.

Erros: 400 PDF inválido/protegido/sem texto; 401 sem sessão; 404 para plano alheio/inexistente; 413 excesso de bytes;
422 conteúdo, referências, autorização ausente ou hash malformado; 409 hash divergente,
execução em andamento, preparação antiga sem texto ou limite acumulado atingido;
503 indisponibilidade/bloqueio operacional do provedor. O corpo continua
`{"detail": "mensagem sanitizada"}`. Não há persistência do PDF após falha.

PDF e texto colado passam pelas mesmas regras locais antes da gravação do texto
preparado. `redactedCount` é um inteiro não negativo com o total de trechos
mascarados na preparação inicial, somado entre as páginas. As respostas de
preparação, autorização e detalhe do próprio plano incluem essa contagem para
exibir o aviso durante e após a análise. É `null` nos planos
preparados antes da contagem. O valor fica fora de `pages` e de `textHash`.
O cliente autoriza as páginas sanitizadas no fluxo iniciado pelo botão de envio.
A autorização devolve `422` quando encontra identificadores detectáveis. Um
snapshot legado com esses dados falha antes da chamada ao provedor, com
`errorCode: texto_com_dados_pessoais`. Reenviar o plano aplica a preparação atual.

Detalhe/listagem preservam estados anteriores. `authorizationRequired` distingue
texto preparado de uma extração já autorizada; `preparedTextAvailable` identifica o protocolo
S7. Detalhe inclui `preparationDurationMs`, `reviewDurationMs` e
`totalDurationMs` desde a autorização. `reviewDurationMs` mede o intervalo entre criação e autorização. Planos
históricos sem preparação mantêm a revisão legada e não recebem autorização
retroativa. A consulta e a confirmação usam `avaliacoes`, a mesma tabela do worker,
filtrando a versão aprovada e aplicando a permissão da versão. Cada candidato inclui `suggestedDate`,
`suggestedTime`, `ambiguousFields` e `versionId`; `startsAt` continua nulo quando
não existe instante/fuso confirmado. A rota envia as confirmações à função
transacional `confirmar_importacao`; `Idempotency-Key` é obrigatório, uma chave
repetida com conteúdo diferente é recusada, retries não recriam eventos apagados
e cada conta tem uma operação independente sobre a mesma versão compartilhada.
A revisão do tipo fica no item de importação da conta e não altera o candidato
compartilhado.

[Fluxo, flags e decisões](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia) · [Minimização (ADR-003)](/arquitetura/adrs/adr-003-minimizar-dados-de-planos) · [Versionamento e confirmação (ADR-010)](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos).

### Catálogo e seleção real de ofertas (#70/#71)

A integração autenticada, rotas de catálogo/filtros/vínculos e operação estão em
[Catálogo de turmas](/arquitetura/catalogo-de-turmas). PDF multipart e texto JSON
passam a exigir `offering_id` (UUID da oferta disponível). O servidor deriva
nome da disciplina, turma e período, ignorando metadados livres para associação.
A listagem particular aceita `offering_id` opcional; dados privados continuam
restritos ao proprietário. `GET /class-offerings/{id}/shared-plans` expõe apenas
versões compartilhadas a seguidores da oferta, sem o texto privado do autor.

### Envio vinculado à conta — S7-F03 (#73)

PDF e texto exigem também que a conta autenticada siga a oferta. Ausência de
vínculo, inclusive após deixar de seguir, retorna 403 com `detail` orientando
seguir a turma. A verificação ocorre antes da extração e novamente antes da
persistência. Em PostgreSQL, a segunda consulta bloqueia o vínculo até o commit,
serializando a gravação com a remoção concorrente do vínculo. Oferta retirada
continua retornando 409; catálogo sem publicação retorna 503.

A interface consulta a oferta e `GET /me/class-offerings` antes de habilitar
PDF/texto. Falhas ou respostas inválidas bloqueiam o envio e oferecem nova consulta.
Planos particulares continuam acessíveis ao dono após deixar de seguir.

### Compartilhamento, versões, procedência e votos — S8-B01 (#77)

| Operação | Entrada / Autorização | Resultado |
| --- | --- | --- |
| `GET /api/v1/class-offerings/{id}/shared-plans` | Seguidor autenticado da oferta (`limit`, `offset`) | Lista versões compartilhadas com `membership_type: "autodeclarado"`, `shared_content_notice`, autoria (`author_role`, `author_name`), `institutional_provenance`, contagens de votos, `divergent` e candidatos, sem expor PDF ou texto bruto privado |
| `GET /api/v1/syllabus/{id}/versions` e `.../versions/{vid}` | Autor da versão ou seguidor da oferta quando `compartilhada` | Lista ou detalha versões legíveis pelo ator (`ator_pode_ler_versao`); papel de professor/admin não abre rascunhos privados alheios |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/sharing` | Somente o autor da versão | Publica voluntariamente a versão para seguidores da oferta (`200`, idempotente; `409` se sem turma ou não concluído) |
| `DELETE /api/v1/syllabus/{id}/versions/{vid}/sharing` | Autor da versão ou `admin` | Retira o compartilhamento (`visibilidade: "privada"`, `withdrawnAt`), bloqueando novos acessos/votos/importações e preservando revisões derivadas e eventos pessoais já importados |
| `POST /api/v1/syllabus/{id}/versions` | Autor (em versão própria), seguidor autenticado da oferta, `professor` ou `admin` (em versão `compartilhada`) | Cria nova versão (`numero + 1`, `sourceVersionId`, `authorRole`) mantendo a versão anterior e agendas pessoais; publica quando `share=true` ou enviada com `candidates` em plano com oferta; herda `institutionalProvenance` apenas para `professor`/`admin` |
| `DELETE /api/v1/syllabus/{id}/versions/{vid}/candidates/{cid}` | Autor da versão ou `admin` | Retira logicamente o candidato da versão (`status: "descartado"`, 204), preservando cópias já importadas |
| `PUT /api/v1/syllabus/{id}/versions/{vid}` | Somente o autor da versão, enquanto `privada` | Atualiza os candidatos do rascunho privado antes do compartilhamento (`409` se já `compartilhada`) |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/provenance` | Somente `admin`, com `institutionalSourceUrl` pública `http(s)` | Registra evidência oficial de procedência institucional em versão compartilhada |
| `PUT /api/v1/syllabus/{id}/versions/{vid}/candidates/{cid}/vote` e `PUT .../versions/{vid}/vote` | Seguidor autenticado da oferta (`{"value": "confirm" \| "contest"}`) | Registra ou altera o voto único ativo por `(user_id, candidate_id)` e devolve `confirmCount`, `contestCount`, `divergent` e `myVote`, sem alterar datas automaticamente |
| `GET /api/v1/syllabus/{id}/versions/{vid}/votes` | Quem pode ler a versão | Retorna o resumo agregado de votos e divergências por candidato (`resumo_votos_versao`), mantendo votos individuais de terceiros privados |
| `POST /api/v1/syllabus/{id}/confirm` | `Idempotency-Key`, `versionId` opcional e `candidates` | Permite que seguidores importem candidatos de uma versão compartilhada para suas agendas privadas independentes, deduplicados por `(user_id, candidate_id)` |
