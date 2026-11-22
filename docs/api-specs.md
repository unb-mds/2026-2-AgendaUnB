# Contratos do backend

## Referência e arquitetura

A API HTTP do Agenda UnB é implementada em FastAPI com prefixo `/api/v1` (além de `/health` e `/api/health`). Quando `API_DOCS_ENABLED=true` (padrão local), `/docs`, `/redoc` e `/openapi.json` ficam disponíveis para inspeção. Consulte também [Arquitetura](/arquitetura/visao-geral), [Padrões](/produto/padroes) e [Implantação](/implantacao).

Módulos de aplicação sob `backend/src/`: `main.py`, `middlewares/auth.py`, `database/models.py` e `modules/{account, classes, events, google_calendar, reminders, syllabus}/`.

## Convenções comuns

- Base local padrão: `http://127.0.0.1:8000/api/v1`.
- Corpos JSON utilizam `Content-Type: application/json`. Rotas autenticadas exigem `Authorization: Bearer <token>` do Supabase Auth.
- Papéis persistidos: `student`, `professor`, `admin`. O servidor extrai o ID da sessão no Auth e consulta `profiles.papel` no banco; o cliente não escolhe a identidade.
- Toda rota autenticada exige e-mail confirmado no Supabase Auth. Metadados nunca concedem `admin`; o papel `professor` só é aceito no cadastro ou autopromoção após confirmação do endereço `@unb.br` da conta. Papéis de terceiros são alterados exclusivamente por administrador via RPC.
- `{event_id}`, `{syllabus_id}`, `{offering_id}` e demais identificadores de recursos são UUIDs válidos.
- Toda resposta inclui cabeçalhos de proteção (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Content-Security-Policy`); respostas com dados privados da conta incluem `Cache-Control: no-store`. O CORS aceita apenas origens configuradas em `CORS_ORIGINS` e os cabeçalhos `Authorization`, `Content-Type`, `Accept` e `Idempotency-Key`. Detalhes em [Verificação de segurança](/processo/seguranca).
- A busca `q` trata `%` e `_` como caracteres literais.
- Respostas `204` não contêm corpo. Listagens de eventos e lembretes retornam arrays (`[]` quando vazias); listagens de planos, versões e ofertas utilizam envelope com `items` e `total`.

## Payloads e respostas de eventos

### Entrada de evento

`EventCreate` é usado na criação pública e na sugestão estudantil. `EventUpdate` usa os mesmos campos na edição pública. `PersonalEventCreate` e `PersonalEventUpdate` usam os campos comuns, sem `external_url`.

| Campo | Tipo | Obrigatório | Regra |
| --- | --- | --- | --- |
| `title` | string | Sim | 3–200 caracteres após remoção de espaços nas extremidades; não aceita `null` |
| `all_day` | boolean | Não | Padrão `false`. Quando `true`, exige `start_date` (e `end_date` exclusivo opcional) e recusa `starts_at`/`ends_at` |
| `starts_at` | datetime ou null | Condicional | Obrigatório quando `all_day = false`; ISO 8601 com fuso explícito (ex.: `2026-11-10T14:00:00-03:00`) |
| `ends_at` | datetime ou null | Não | Somente quando `all_day = false`; ISO 8601 com fuso e posterior a `starts_at` |
| `start_date` | date (`YYYY-MM-DD`) ou null | Condicional | Obrigatório quando `all_day = true`; início civil em `America/Sao_Paulo` |
| `end_date` | date (`YYYY-MM-DD`) ou null | Não | Somente quando `all_day = true`; fim civil exclusivo posterior a `start_date` (padrão `start_date + 1 dia`) |
| `description` | string ou null | Não | Até 10.000 caracteres; padrão `null` |
| `campus` | string ou null | Não | Nome oficial existente (`Darcy Ribeiro (Plano Piloto)`, `FCTE (Gama)`, `FCTS (Ceilândia)`, `FUP (Planaltina)`, `FAL`), 2–120 caracteres |
| `category` | string ou null | Não | Nome de categoria existente (`Acadêmico`, `Cultura`, `Esporte`, `Extensão`, `Lazer`, `Comunicado`, ou criada pelo admin), 2–80 caracteres |
| `location` | string ou null | Não | Até 250 caracteres; persistido em eventos públicos e pessoais |
| `external_url` | URL HTTP/HTTPS ou null | Não | Somente evento público/sugestão; validado por `HttpUrl`; padrão `null` |

Strings são aparadas nas extremidades; strings vazias em `description`, `campus`, `category` e `location` tornam-se `null`. Campus e categoria são resolvidos por nome sem diferenciar maiúsculas/minúsculas; nome desconhecido na escrita retorna `422`. Operações `PUT` substituem os campos editáveis.

Exemplo `EventCreate` com horário:

```json
{
  "title": "Encontro de extensão",
  "all_day": false,
  "starts_at": "2026-11-18T14:00:00-03:00",
  "ends_at": "2026-11-18T16:00:00-03:00",
  "description": "Apresentação de projetos da comunidade acadêmica.",
  "campus": null,
  "category": null,
  "location": "Auditório",
  "external_url": "https://example.org/encontro"
}
```

Exemplo de evento de dia inteiro (cobrindo 18, 19 e 20/11 inclusive, com `end_date` exclusivo):

```json
{
  "title": "Mostra de extensão",
  "all_day": true,
  "start_date": "2026-11-18",
  "end_date": "2026-11-21"
}
```

### Objetos retornados

`EventRead` retorna `id`, `title`, `description`, `starts_at`, `ends_at`, `all_day`, `start_date`, `end_date`, `campus`, `category`, `location`, `external_url`, `organizer_name`, `organizer_avatar`, `source`, `source_url` e `outbound_clicks_count`.

`PersonalEventRead` retorna `id`, `title`, `description`, `starts_at`, `ends_at`, `all_day`, `start_date`, `end_date`, `campus`, `category`, `location` e `origin` (`{ syllabusId, candidateId, page, excerpt }` quando importado de plano de ensino, ou `null`). Eventos de dia inteiro preenchem `all_day = true`, `start_date` e `end_date` exclusivo em `America/Sao_Paulo`, mantendo `starts_at`/`ends_at` normalizados na meia-noite de Brasília para ordenação e filtros ([ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes)).

`SavedEventStatus` retorna `{ "saved": true }` ou `{ "saved": false }`.

## Inventário HTTP

Operações que acessam dados podem retornar **503** em falha SQLAlchemy. Rotas autenticadas também podem retornar **401** (sessão ausente/inválida), **403** (perfil ausente ou e-mail não confirmado) e **503** (falha de comunicação com Auth). Escritas podem retornar **409** em conflitos de integridade.

### Eventos públicos e categorias

| Método e rota | Acesso | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- | --- |
| `GET /api/v1/events` | Público | Filtros abaixo | `200`, `EventRead[]`, somente aprovados, ordenados por `starts_at ASC, id ASC` | `422`, filtros inválidos |
| `GET /api/v1/events/{event_id}` | Público | UUID no caminho | `200`, `EventRead` aprovado | `422`, UUID; `404`, ausente ou não aprovado |
| `POST /api/v1/events/{event_id}/outbound-clicks` | Público | UUID + `{"click_id": UUID}` (aceita `clickId`) | `200`, `{external_url, outbound_clicks_count, incremented}` (deduplicado por `click_id`) | `422`, sem link oficial; `404`, ausente/não aprovado |
| `POST /api/v1/events` | Professor/admin | `EventCreate` | `201`, `EventRead`; autoria da sessão e status `aprovado` | `403`, papel; `422`, payload/referências; `409` |
| `GET /api/v1/me/published-event-ids` | Professor/admin | — | `200`, UUIDs dos próprios eventos aprovados, sem cache | `403`, papel |
| `PUT /api/v1/events/{event_id}` | Professor autor ou admin | UUID + `EventUpdate` | `200`, `EventRead` atualizado para evento aprovado | `403`, papel ou autoria; `422`; `404`; `409` |
| `DELETE /api/v1/events/{event_id}` | Professor autor ou admin | UUID no caminho | `204`, exclui o evento e vínculos em cascata | `403`, papel ou autoria; `422`; `404`; `409` |
| `GET /api/v1/categories` | Público | — | `200`, `CategoryRead[]` | — |
| `POST /api/v1/categories` | Admin | `CategoryCreate` (`name`, `color`) | `201`, `CategoryRead` | `403`, papel; `409`, nome duplicado; `422` |
| `DELETE /api/v1/categories/{category_id}` | Admin | UUID no caminho | `204` | `403`, papel; `404`, ausente; `409`, categoria em uso |

Administradores podem editar qualquer evento aprovado, inclusive eventos coletados. A exclusão autorizada aceita eventos em qualquer status. O painel administrativo no frontend utiliza as RPCs `admin_listar_categorias`, `admin_criar_categoria` e `admin_excluir_categoria` (que incluem contagem de eventos vinculados), enquanto as rotas REST de categorias em `/api/v1/categories` permanecem ativas na API com a mesma exigência de papel `admin`.

| Query de listagem pública | Tipo e padrão | Semântica |
| --- | --- | --- |
| `campus` | string opcional, 2–120 caracteres | Nome exato sem diferenciar caixa; desconhecido retorna lista vazia |
| `category` | string opcional, 2–80 caracteres | Mesma regra de `campus` |
| `startDate` | datetime opcional | Exige fuso. Inclui intervalos com `ends_at > startDate` (ou `starts_at >= startDate` quando sem término) |
| `endDate` | datetime opcional | Limite superior inclusivo; exige fuso e não pode preceder `startDate` |
| `q` | string opcional, 1–120 caracteres | Busca parcial no título sem diferenciar caixa (`%` e `_` literais) |
| `limit` | inteiro, padrão 50 | De 1 a 100 |
| `offset` | inteiro, padrão 0 | Maior ou igual a zero |

O filtro de turno é aplicado na interface.

### Agenda pessoal

Todas as operações exigem sessão e restringem os dados ao usuário autenticado.

| Método e rota | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- |
| `GET /api/v1/me/events` | — | `200`, `PersonalEventRead[]`, início crescente | Erros comuns |
| `GET /api/v1/me/events/{event_id}` | UUID | `200`, `PersonalEventRead` | `422`, UUID; `404`, ausente ou alheio |
| `POST /api/v1/me/events` | `PersonalEventCreate` | `201`, `PersonalEventRead` | `422`, payload/referências; `409` |
| `PUT /api/v1/me/events/{event_id}` | UUID + `PersonalEventUpdate` | `200`, `PersonalEventRead` | `422`; `404`, ausente ou alheio; `409` |
| `DELETE /api/v1/me/events/{event_id}` | UUID | `204` | `422`; `404`, ausente ou alheio; `409` |

### Sugestões

| Método e rota | Acesso e entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- |
| `POST /api/v1/suggestions` | Somente `student`; `EventCreate` | `201`, `EventRead`; autoria da sessão, status `pendente`, notificação via trigger | `403`, papel; `422`; `409`; `429` (limite de 10 sugestões pendentes por conta) |

### Eventos salvos {#eventos-salvos}

Todas as operações exigem sessão. O vínculo não copia o evento e não constitui inscrição.

| Método e rota | Entrada | Sucesso | Erros específicos |
| --- | --- | --- | --- |
| `GET /api/v1/me/saved-events` | — | `200`, `EventRead[]`, somente aprovados vinculados; ordem por início e ID | Erros comuns |
| `GET /api/v1/me/saved-events/{event_id}` | UUID | `200`, `SavedEventStatus`; `false` se ausente ou não aprovado | `422`, UUID |
| `PUT /api/v1/me/saved-events/{event_id}` | UUID, sem corpo | `200`, `{ "saved": true }`, idempotente | `422`, UUID; `404`, evento ausente ou não aprovado; `409` |
| `DELETE /api/v1/me/saved-events/{event_id}` | UUID | `204`, idempotente; cancela lembretes futuros pendentes do vínculo | `422`, UUID; `409` |

### Catálogo de turmas e vínculos autodeclarados {#catalogo-e-vinculos}

Todas as rotas do módulo `classes` exigem autenticação com e-mail confirmado e retornam `Cache-Control: no-store`.

| Método e rota | Entrada | Resposta |
| --- | --- | --- |
| `GET /api/v1/class-offerings/filters` | — | `200`, `{ units, periods, source_updated_at, stale }` (`503` sem publicação válida) |
| `GET /api/v1/class-offerings` | `year`, `semester` (`1\|2`), `unit`, `subject_code`, `q`, `limit` (`1–100`, padrão `20`), `offset` (`>=0`) | `200`, `{ items, total, limit, offset, source_updated_at, stale }` (`503` sem publicação válida) |
| `GET /api/v1/class-offerings/{offering_id}` | UUID da oferta | `200`, `OfferingRead` com `available` (`404` se inexistente) |
| `GET /api/v1/me/class-offerings` | — | `200`, `{ items }` com ofertas seguidas pela conta |
| `PUT /api/v1/me/class-offerings/{offering_id}` | UUID da oferta disponível | `204`, idempotente (`409` se oferta indisponível/retirada) |
| `DELETE /api/v1/me/class-offerings/{offering_id}` | UUID da oferta | `204`, remove vínculo da sessão de forma idempotente (preserva eventos importados) |
| `GET /api/v1/class-offerings/{offering_id}/shared-plans` | `limit` (`1–100`, padrão `20`), `offset` (`>=0`) | `200`, `SharedPlanList` com `membership_type: "autodeclarado"`, `shared_content_notice`, versões compartilhadas ordenadas por votos positivos e data mais recente, indicador `is_default`, alterações pós-importação e candidatos (`403` sem vínculo) |

Consulte os detalhes de sincronização e identidade em [Catálogo de turmas](/arquitetura/catalogo-de-turmas).

### Planos de ensino: preparação, extração, versões e votos {#preparacao-e-autorizacao-de-planos}

Todas as operações exigem sessão com e-mail confirmado. Envios de novos planos (`POST /upload` e `POST /text`) exigem `offering_id` de uma oferta disponível seguida pela conta (`403` sem vínculo, `409` se oferta retirada, `503` sem catálogo publicado) e aplicam cota acumulada de 10 envios em 5 dias (`429`).

| Operação | Entrada / Autorização | Resposta |
| --- | --- | --- |
| `POST /api/v1/syllabus/upload` | Multipart com `file` (PDF digital ≤ 10 MiB e ≤ 10 páginas) e `offering_id` | `202`, texto preparado privado, `filePath: null`, `authorizationRequired: true`, `preparedTextAvailable: true`, `redactedCount`. O PDF é descartado após extração local em memória |
| `POST /api/v1/syllabus/text` | JSON `text` (≤ 40.000 bytes UTF-8) e `offering_id` | `202`, preparação privada, `fileType: "text"`, página de origem `null`, `redactedCount` |
| `GET /api/v1/syllabus/{syllabus_id}/text` | Sessão do dono (`no-store`) | `200`, `pages: [{pagina, texto}]`, `textHash` (SHA-256 compacto), `authorizationRequired`, `provider`, `providerAvailable`, `maxTextBytes`, `warning`, `preparationDurationMs`, `textRevision`, `redactedCount` |
| `POST /api/v1/syllabus/{syllabus_id}/extractions` | JSON `pages`, `textHash`, `authorize: true`, `reprocess` opcional | `202`, registra autorização e enfileira para processamento. Repetir o mesmo hash sem `reprocess` não cria execução adicional (`422` se contiver PII detectável; `409` se hash divergir ou limite atingido) |
| `GET /api/v1/syllabus` | `offering_id` opcional, `limit` (`1–100`, padrão `20`), `offset` (`>=0`) | `200`, `{ items, total, limit, offset }`, ordenado por criação e ID decrescentes |
| `GET /api/v1/syllabus/{syllabus_id}` | Autor ou seguidor se versão `compartilhada` | `200`, detalhes, `preparationDurationMs`, `reviewDurationMs`, `totalDurationMs`, `redactedCount` e candidatos com `suggestedDate`, `suggestedTime`, `ambiguousFields`, `versionId` e contagens de votos. Compartilha `v1` automaticamente ao concluir com candidatos e turma vinculada quando consultada pelo autor (salvo se retirada) |
| `POST /api/v1/syllabus/{syllabus_id}/confirm` | Cabeçalho `Idempotency-Key` (8–200 chars), `versionId` opcional e `candidates[]` (`candidateId`, `title`, `description`, `type`, `startsAt`, `allDay`, `start_date`, `end_date`, `category`) | `200`, `{ syllabusId, operationId, repeated, items, events }`. Execução transacional via `confirmar_importacao`; `409` (`AG409`) se chave reutilizada com conteúdo divergente; `422` para data ambígua sem correção |
| `DELETE /api/v1/syllabus/{syllabus_id}` | Dono do plano | `204`, remove plano, versões próprias e candidatos preservando eventos pessoais importados (`409` se `processando`, com versão `compartilhada` ou revisões de terceiros) |
| `DELETE /api/v1/syllabus/{syllabus_id}/candidates/{candidate_id}` | Dono do plano privado | `204`, marca candidato como `descartado` na versão privada |
| `GET /api/v1/syllabus/{syllabus_id}/versions` e `.../versions/{version_id}` | Autor da versão ou seguidor da oferta se `compartilhada` | `200`, `SyllabusVersionListResponse` ou `VersionStatusResponse` com `membershipType: "autodeclarado"` e `sharedContentNotice` |
| `PUT /api/v1/syllabus/{syllabus_id}/versions/{version_id}` | Somente autor enquanto `privada` | `200`, atualiza candidatos do rascunho privado (`409` se já `compartilhada`) |
| `POST /api/v1/syllabus/{syllabus_id}/versions` | Autor da origem; ou seguidor da oferta, `professor` ou `admin` se origem `compartilhada` | `201`, cria revisão (`numero + 1`, `sourceVersionId`, `authorRole`), preservando versão anterior e agendas pessoais; publica quando `share=true` ou enviada com `candidates` em plano com oferta; herda `institutionalProvenance` apenas para `professor`/`admin` |
| `PUT /api/v1/syllabus/{syllabus_id}/versions/{version_id}/sharing` | Somente autor da versão | `200`, publica voluntariamente a versão para seguidores (`409` se sem oferta ou não `concluido`) |
| `DELETE /api/v1/syllabus/{syllabus_id}/versions/{version_id}/sharing` | Autor da versão ou `admin` | `200`, retira compartilhamento (`visibility: "privada"`, `withdrawnAt`), preservando revisões derivadas e cópias importadas |
| `DELETE /api/v1/syllabus/{syllabus_id}/versions/{version_id}/candidates/{candidate_id}` | Autor da versão ou `admin` | `204`, retira logicamente o candidato (`status: "descartado"`), preservando cópias já importadas |
| `PUT /api/v1/syllabus/{syllabus_id}/versions/{version_id}/provenance` | Somente `admin`, em versão `compartilhada` | `200`, registra `institutionalSourceUrl` pública `http(s)` validando procedência institucional |
| `PUT /api/v1/syllabus/{syllabus_id}/versions/{version_id}/candidates/{candidate_id}/vote` e `PUT .../versions/{version_id}/vote` | Seguidor autenticado ou autor em versão `compartilhada` (`{"value": "confirm" \| "contest"}`) | `200`, registra/altera voto único por `(user_id, avaliacao_id)` e retorna `confirmCount`, `contestCount`, `divergent` e `myVote` |
| `GET /api/v1/syllabus/{syllabus_id}/versions/{version_id}/votes` | Quem pode ler a versão | `200`, resumo agregado `VersionVotesResponse` sem expor votos individuais de terceiros |

Consulte a integração SQL e exemplos de confirmação em [Dados de planos](/arquitetura/dados-de-planos) e as decisões [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos), [ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos) e [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia).

### Conta e privacidade

| Método | Rota | Acesso | Resposta |
| --- | --- | --- | --- |
| `GET` | `/api/v1/me/legal-documents` | Autenticado (`no-store`) | `200` com versão vigente (`terms` e `privacy`) e versão aceita pela conta |
| `PUT` | `/api/v1/me/legal-acceptances/{terms\|privacy}` | Autenticado (`no-store`) | `204`; `409` se a versão enviada divergir da vigente |
| `GET` | `/api/v1/me/consents` | Autenticado (`no-store`) | `200` com os consentimentos opcionais registrados |
| `DELETE` | `/api/v1/me/consents/{purpose}` | Autenticado (`no-store`) | `204`; revoga consentimento opcional (ex.: `google_agenda`) |
| `GET` | `/api/v1/me/data-export` | Autenticado (`no-store`) | `200` com `agenda-unb-dados.json` contendo os dados da conta (inclusive `reminders` e `googleCalendarExports`) |
| `DELETE` | `/api/v1/me` | Autenticado (`no-store`) | `204`; exige frase `"EXCLUIR MINHA CONTA"` (`422` se divergente); `409` para o último administrador |

Detalhes do ciclo de vida em [Privacidade e ciclo de vida dos dados](/processo/privacidade).

### Saúde

`GET /health` e `GET /api/health`: públicos, sem parâmetros ou corpo, retornam `200` com `{ "status": "ok" }`. Não consultam banco nem Auth.

### Exportação para o Google Calendar {#exportacao-para-o-google-calendar}

O login Google do Supabase solicita apenas identidade. A permissão de calendário é opcional e acionada sob demanda em **Meus Eventos** (inclusive para sessões por e-mail e senha com e-mail confirmado), utilizando um cliente OAuth Google Cloud dedicado ao Calendar. Todas as respostas deste grupo aplicam `Cache-Control: no-store`.

| Operação | Entrada | Resposta |
| --- | --- | --- |
| `POST /api/v1/me/google-calendar/authorization` | Bearer Supabase | `200` com `authorization_url` e `expires_in_seconds` (`600`). Desafio de uso único com `state` e PKCE S256 |
| `GET /api/v1/me/google-calendar/callback` | Query string com `state` e `code` ou `error` (`POST` também aceito) | `303` para `GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI` com parâmetro `google_calendar`. Valida escopo `calendar.app.created` e correspondência com o e-mail confirmado atual |
| `GET /api/v1/me/google-calendar/connection` | Bearer Supabase | `200` com `connected` e `recovery_required` |
| `DELETE /api/v1/me/google-calendar/connection` | Bearer Supabase | `200` com `disconnected` e `revocation`. Revoga o acesso no Google, remove credenciais locais e preserva eventos já exportados |
| `PUT /api/v1/me/google-calendar/destination` | Bearer Supabase e `calendar_id` (string ou `null`) | `204` após validar no Google ou limpar o destino (`calendar_id: null`), invalidando mapeamentos anteriores para permitir nova criação |
| `POST /api/v1/me/google-calendar/exports/preview` | Bearer Supabase e JSON com `events` (1 a 20 `{ id, kind }`, sendo `kind` `personal` ou `saved`), `include_description` (padrão `false`), `start_date` e `end_date` opcionais (`YYYY-MM-DD`) | `200` com `requires_overwrite_confirmation` e `items: [{ id, kind, action }]`, onde `action` é `create`, `update` ou `unchanged` |
| `POST /api/v1/me/google-calendar/exports` | Bearer Supabase, cabeçalho opcional `Idempotency-Key` (≤ 128 chars), `events` (1 a 20 `{ id, kind }`), `allow_managed_field_updates` (padrão `false`), `include_description` (padrão `false`), `start_date` e `end_date` opcionais | `200` com lista `{ id, kind, status }` por item (`exported`, `updated`, `already_exported` ou `failed`) |

Exemplo de prévia (`POST /api/v1/me/google-calendar/exports/preview`):

```json
{
  "requires_overwrite_confirmation": true,
  "items": [
    {"id": "77777777-7777-4777-8777-777777777777", "kind": "saved", "action": "create"},
    {"id": "99999999-9999-4999-8999-999999999999", "kind": "personal", "action": "update"}
  ]
}
```

Exemplo de envio (`POST /api/v1/me/google-calendar/exports`) e resposta (`200 OK`):

```json
{
  "events": [
    {"id": "77777777-7777-4777-8777-777777777777", "kind": "saved"},
    {"id": "99999999-9999-4999-8999-999999999999", "kind": "personal"}
  ],
  "allow_managed_field_updates": true,
  "include_description": true,
  "start_date": "2026-11-18",
  "end_date": "2026-11-22"
}
```

```json
[
  {"id": "77777777-7777-4777-8777-777777777777", "kind": "saved", "status": "exported"},
  {"id": "99999999-9999-4999-8999-999999999999", "kind": "personal", "status": "updated"}
]
```

Cada evento recebe um ID determinístico `base32hex` (`sha256("{user_id}:{kind}:{event_id}").hexdigest()`) e um hash de versão (`exported_version`) sobre os campos geridos (`summary`, `description`, `location`, `start`, `end`), utilizando a agenda secundária **"Agenda UnB"**. Não há sincronização bidirecional: exclusões ou edições locais não removem nem sincronizam automaticamente alterações após a exportação. Consulte a [ADR-012](/arquitetura/adrs/adr-012-exportacao-google-idempotente) para detalhes de tratamento de erros (`409`, `429`, `404`/`410`, `invalid_grant`) e geração complementar de `.ics` (RFC 5545).

### Lembretes da agenda {#lembretes-da-agenda}

| Rota | Resultado |
| --- | --- |
| `GET /api/v1/me/reminders?limit=20&offset=0` | `200` com array de lembretes disparados da sessão, ordenado por disparo e ID decrescentes (`limit` 1–100, `offset` 0–2147483647) |
| `PUT /api/v1/me/reminders/{id}/read` | `200` com `{id, read_at}`, preservando o primeiro `read_at`. Retorna `404` para IDs alheios, pendentes ou inexistentes |

Cada item inclui `id`, `event_kind` (`personal` ou `saved_public`), `event_id`, `title`, `starts_at`, `scheduled_at` e `read_at`. O agendamento opera no PostgreSQL via triggers e `pg_cron`, conforme [Dados de eventos](/arquitetura/dados-de-eventos#3-lembretes) e [Implantação](/implantacao#publicacao-jobs-e-recuperacao).

## Erros FastAPI {#erros-fastapi}

| HTTP | Situação | Formato |
| --- | --- | --- |
| `401` | Bearer ausente, sessão expirada/inválida ou identidade inválida no Auth | `{"detail":"mensagem"}` |
| `403` | Perfil não encontrado, e-mail não confirmado ou papel/vínculo sem permissão | `{"detail":"mensagem"}` |
| `404` | Recurso inexistente ou indisponível para a conta | `{"detail":"mensagem"}` |
| `409` | `IntegrityError`, estado incompatível ou `Idempotency-Key` divergente (`AG409`) | `{"detail":"mensagem"}` |
| `413` | Corpo acima de 256 KiB fora de upload de planos (`MAX_JSON_BODY_BYTES`) | `{"detail":"mensagem"}` |
| `422` | Validação automática Pydantic ou regra explícita (campus/categoria desconhecidos, data ambígua/inválida) | `detail` textual e, na validação Pydantic, `errors: [{type, loc, msg}]` |
| `429` | Limite de requisições (`Retry-After`), mais de 10 sugestões pendentes ou cota de envios de planos | `{"detail":"mensagem"}` |
| `503` | Falha SQLAlchemy, indisponibilidade do Auth, catálogo sem publicação ou provedor externo indisponível | `{"detail":"mensagem"}` |

Falhas inesperadas retornam `500` com mensagem genérica, sem vazar entradas brutas, tokens ou stack traces.

## Contratos Supabase separados da API FastAPI

O frontend utiliza o SDK autenticado para as RPCs de moderação e administração listadas abaixo (`frontend/src/lib/moderation.js`). A função `registrar_redirecionamento_evento` é restrita ao servidor (`service_role`).

| RPC | Acesso | Parâmetros | Resultado |
| --- | --- | --- | --- |
| `listar_sugestoes` | Professor/admin | `p_status` (`pendente/aprovado/rejeitado`), `p_busca`, `p_offset` (≥0) | `{items, total, pending}`; páginas de 20, ordem crescente de criação |
| `listar_revisoes_coleta` | Professor/admin | `p_status` (`pendente/aprovado/rejeitado`), `p_offset` (≥0) | `{items, total}` com itens coletados em revisão |
| `moderar_sugestao` | Professor/admin | `p_evento_id`, `p_status` (`aprovado/rejeitado`), `p_justificativa` (obrigatória 1–2.000 chars na recusa) | Void; decide somente itens `pendente` |
| `admin_buscar_usuarios` | Admin | `p_busca`, `p_papel` (`student/professor/admin`), `p_confirmado` (`sim/nao`), `p_offset` (≥0) | `{items, total, all, unconfirmed}`; 20 por página |
| `admin_definir_papel` | Admin | `p_usuario_id`, `p_novo_papel`, `p_papel_atual` | Void; verifica cargo anterior, audita mudança e bloqueia autorrebaixamento |
| `admin_listar_categorias` | Admin | — | Lista de categorias com `id`, `nome`, `cor`, `created_at` e `events_count` |
| `admin_criar_categoria` | Admin | `p_nome` (2–80 chars), `p_cor` (`#rrggbb`) | Cria e retorna categoria (`42501` fora de admin; `22023` duplicada) |
| `admin_excluir_categoria` | Admin | `p_categoria_id` | Void; bloqueia exclusão se houver eventos vinculados |

**RPCs legadas de compatibilidade:** `revisar_candidatos_plano(p_plano_id, p_itens)` (restrita ao dono confirmado), `admin_listar_usuarios()` e `admin_alterar_papel(p_usuario_id, p_novo_papel)` (chamada internamente por `admin_definir_papel`) permanecem no banco para compatibilidade e verificações de segurança.

### Notificações de moderação

O SDK consulta `notificacoes` filtrando por `usuario_id`, ordenando por `criado_em desc, id asc` em páginas de 20 itens e contando não lidas (`lida_em IS NULL`). Cada registro contém `id`, `usuario_id`, `evento_id`, `tipo` (`submissao/aprovacao/recusa`), `titulo_evento`, `justificativa`, `criado_em` e `lida_em`. O banco restringe ao destinatário apenas leitura e atualização da coluna `lida_em`.

## Verificação

Conferir inventário de rotas com `app.openapi()` e validar contratos com `pytest` (`backend/tests/`). Testes unitários da API usam SQLite e substituem dependências do Auth; testes de RLS, triggers e RPCs (`tests/*_database.py` e `tests/test_syllabus_http_integration.py`) exigem Supabase local descartável. Consulte [Contribuição](/processo/contribuindo).
