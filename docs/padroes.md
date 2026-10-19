# 📖 Glossário e Padronização de Nomenclaturas — Projeto Agenda UnB

Este documento estabelece as convenções de código, terminologia oficial e padrões de rotas da API para garantir consistência entre o **Frontend** e o **Backend** da aplicação **Agenda UnB**.

---

## 1. Glossário de Domínio (Entidades Principais)

Utilizamos **Inglês** para os nomes de domínio da API e rotas. O banco existente mantém nomes em português com `snake_case`, mapeados pela API. Os textos da interface com o usuário (UI) permanecem em Português.

| Termo (PT-BR) | Termo Oficial (Código) | Descrição / Uso |
| :--- | :--- | :--- |
| **Usuário** | `User` | Conta de acesso da pessoa na aplicação (Estudante, Professor ou Administrador). |
| **Papel / Tipo de Usuário** | `Role` | Nível de acesso do usuário (`student`, `professor`, `admin`). |
| **Evento / Compromisso** | `Event` | Registro de uma atividade na agenda (acadêmica pessoal ou geral do campus). |
| **Plano de Ensino** | `Syllabus` | Arquivo (PDF ou texto) enviado para extração automática de datas acadêmicas. |
| **Calendário / Agenda** | `Calendar` | Coleção/agrupamento de eventos de um usuário ou do campus. |
| **Categoria / Etiqueta** | `Category` | Classificação do evento (ex: *Prova*, *Trabalho*, *Seminário*, *Cultural*, *Palestra*). |
| **Notificação** | `Notification` | Aviso persistido de submissão, aprovação ou recusa de sugestão. |
| **Lembrete** | `Reminder` | Alerta futuro programado antes do início de um evento. |
| **Inscrição / Participante** | `Attendee` | Registro de presença/inscrição direta de um usuário em um evento público. |
| **Moderação / Submissão** | `Review` / `Submission` | Fluxo de validação de eventos propostos por usuários antes de entrarem na agenda pública. |

---

## 2. Convenções de Escrita (*Naming Conventions*)

| Elemento | Padrão | Exemplo |
| :--- | :--- | :--- |
| **Variáveis e Funções** | `camelCase` | `eventId`, `getEventsByDate()`, `isAvailable`, `extractedEvents` |
| **Classes, Componentes e Schemas** | `PascalCase` | `EventController`, `CalendarGrid.jsx`, `RegisterModal.jsx`, `UserModel` |
| **Arquivos de Código** | `kebab-case` ou `PascalCase` | `event-service.js` ou `EventCard.jsx` |
| **Rotas da API (URLs)** | `kebab-case` | `/api/v1/user-settings`, `/api/v1/syllabus/upload` |
| **Campos do Banco de Dados** | `snake_case` (PT-BR) no PostgreSQL | `criado_em`, `data_evento`, `data_hora`, `autor_id`, `user_id` |
| **Constantes Globais e Enums** | `UPPER_SNAKE_CASE` | `MAX_EVENTS_PER_DAY`, `DEFAULT_PORT`, `ROLE_STUDENT` |
| **Classes CSS** | `kebab-case` | `.modal-btn-primary`, `.role-selector`, `.nav-items` |

---

## 3. Estrutura de Atributos dos Modelos (Campos de Dados)

> **Nota de Mapeamento:** No banco de dados PostgreSQL (`supabase/migrations/`), as colunas seguem `snake_case` em português (ex: `data_evento`, `autor_id`, `criado_em`). A API FastAPI (`backend/src/database/models.py`) mapeia essas colunas para entidades de domínio e expõe schemas JSON com tipagem clara via Pydantic.

### 👤 `User` / `profiles` (Perfil de Usuário)
* `id`: Identificador único (`UUID`, vinculado a `auth.users.id`)
* `nome_completo` / `name`: Nome completo
* `email`: Endereço de e-mail institucional ou pessoal (imutável via trigger)
* `papel` / `role`: Papel no sistema (`"student"`, `"professor"`, `"admin"`)
* `avatar_url`: URL da foto de perfil
* `criado_em` / `createdAt`: Data de criação da conta
* `atualizado_em` / `updatedAt`: Data da última alteração de perfil

### 📅 `Event` / `eventos` (Evento Público / Campus)
* `id`: Identificador único do evento (`UUID`)
* `autor_id` / `author_id`: ID do criador do evento (Chave Estrangeira em `profiles.id`)
* `titulo` / `title`: Título do evento
* `descricao` / `description`: Detalhes, ementa ou notas sobre a atividade
* `localizacao` / `location`: Local físico ou link
* `data_evento` / `starts_at`: Data e hora de início (`ISO 8601`)
* `link_externo` / `external_url`: URL externa oficial
* `campus_id`: ID do campus associado
* `category_id`: ID da categoria associada
* `status`: Status de moderação (`"pendente"`, `"aprovado"`, `"rejeitado"`)
* `criado_em`: Data de registro no sistema

### 📅 `PersonalEvent` / `eventos_pessoais` (Evento Pessoal / Agenda Privada)
* `id`: Identificador único do evento (`UUID`)
* `user_id`: ID do proprietário (`UUID`, restrito via RLS)
* `titulo` / `title`: Título do compromisso ou prazo
* `descricao` / `description`: Detalhes sobre o prazo
* `data_hora` / `starts_at`: Data e hora do compromisso (`ISO 8601`)
* `campus_id`: ID do campus (opcional)
* `category_id`: ID da categoria associada (opcional)
* `criado_em`: Data de criação

### 📄 `Syllabus` / `planos_ensino` (Modelo Dual planejado)

Os campos abaixo são uma proposta para o processamento futuro; não descrevem integralmente a tabela já criada nas migrações. O parser e as rotas de upload não estão implementados.
* `id`: Identificador único do arquivo/processamento (`UUID`)
* `usuario_id` / `professor_id`: ID do usuário que enviou o arquivo
* `disciplina`: Nome ou código da disciplina
* `turma`: Identificação da turma (para planos oficiais)
* `arquivo_url`: URL do arquivo armazenado no Supabase Storage
* `tipo_plano`: `"oficial"` (enviado por docente) ou `"particular"` (enviado por discente)
* `status`: Status do processamento (`"pendente"`, `"processando"`, `"concluido"`, `"falha"`)
* `criado_em`: Data e hora do envio

### 📋 `EnrollmentCertificate` / `atestados_matricula` (Atestado de Matrícula — modelo planejado)
* `id`: Identificador único (`UUID`)
* `usuario_id`: ID do estudante (`UUID`)
* `arquivo_url`: URL do PDF do atestado no Supabase Storage
* `semestre`: Semestre letivo correspondente (ex: `"2026/2"`)
* `status`: Status da extração (`"pendente"`, `"processando"`, `"concluido"`, `"falha"`)
* `criado_em`: Data do upload

### ✅ `AssessmentConfirmation` / `confirmacoes_avaliacao` (Validação Colaborativa — modelo planejado)
* `id`: Identificador do voto/confirmação (`UUID`)
* `avaliacao_id`: ID da avaliação extraída (`UUID`)
* `usuario_id`: ID do aluno matriculado que votou (`UUID`)
* `confirmado`: Booleano indicando se a data foi confirmada (`true`) ou contestada (`false`)
* `criado_em`: Data do registro

### 🏷️ `Category` / `categories` (Categoria)
* `id`: Identificador da categoria (`UUID`)
* `nome`: Nome da categoria (*"Acadêmico"*, *"Cultura"*, *"Esporte"*, *"Extensão"*, *"Lazer"*, *"Comunicado"*)
* `cor`: Código hexadecimal de cor (ex: `"#008bff"`)

---

## 4. Padronização de Rotas da API REST (`Endpoints`)

Todas as rotas da API backend iniciam com o prefixo `/api/v1`.

### 🔑 Autenticação e Sessão
A autenticação de usuários é realizada pelo **Supabase Auth SDK** diretamente no frontend (`@supabase/supabase-js`), provendo cadastro, login por senha e Google OAuth com emissão de tokens JWT. O backend FastAPI atua como validador de recursos, recebendo o cabeçalho `Authorization: Bearer <token>` através do middleware `get_current_user`.

### 📅 Eventos Públicos (`/api/v1/events`) — Implementado
* `GET /api/v1/events` — Listar eventos públicos aprovados (filtros: `campus`, `category`, `startDate`, `endDate`, `q`, `limit`, `offset`)
* `GET /api/v1/events/:id` — Obter detalhes de um evento público aprovado
* `POST /api/v1/events` — Criar novo evento público (restrito a `professor` e `admin`, status inicial `"aprovado"`)
* `DELETE /api/v1/events/:id` — Excluir evento público (restrito a `professor` e `admin`)

### 📅 Agenda Pessoal do Usuário (`/api/v1/me/events`) — *Implementado (R1)*
* `GET /api/v1/me/events` — Listar compromissos privados do usuário autenticado
* `GET /api/v1/me/events/:id` — Obter detalhes de um compromisso pessoal (restrito ao dono)
* `POST /api/v1/me/events` — Criar compromisso particular na agenda pessoal
* `PUT /api/v1/me/events/:id` — Atualizar compromisso pessoal (restrito ao dono)
* `DELETE /api/v1/me/events/:id` — Excluir compromisso pessoal (restrito ao dono)

### Eventos públicos salvos — Implementado

* `GET /api/v1/me/saved-events` — Lista públicos aprovados vinculados ao usuário.
* `GET /api/v1/me/saved-events/:id` — Retorna `{ "saved": true/false }`.
* `PUT /api/v1/me/saved-events/:id` — Salva sem duplicar; retorna `{ "saved": true }` ou 404 para evento ausente/não aprovado.
* `DELETE /api/v1/me/saved-events/:id` — Remove apenas o vínculo; retorna 204 mesmo que ele já não exista.

Todas exigem sessão; `user_id` vem da identidade validada. PUT/DELETE são idempotentes. Os dados são lidos do evento original. Salvar não é inscrição e não usa a futura rota `/attend`.

### 🏥 Verificação do Servidor — *Implementado (R1)*
* `GET /health` — Health check do servidor API

### 📋 Atestado de Matrícula (`/api/v1/enrollment`) — *Planejado, sem endpoint implementado*
* `POST /api/v1/enrollment/upload` — Enviar PDF do atestado de matrícula do SIGAA para alocação automática de turmas

### 📄 Processamento de Planos de Ensino (`/api/v1/syllabus`) — *Planejado, sem endpoint implementado*
* `POST /api/v1/syllabus/upload` — Enviar arquivo PDF ou texto bruto de plano de ensino (Modelo Dual)
* `GET /api/v1/syllabus` — Listar planos de ensino enviados pelo usuário
* `GET /api/v1/syllabus/:id` — Obter status do processamento e eventos/prazos extraídos

### ✅ Validação Colaborativa (`/api/v1/assessments`) — *Planejado, sem endpoint implementado*
* `POST /api/v1/assessments/:id/confirm` — Votar para confirmar ou contestar data de avaliação extraída de plano compartilhado

### Sugestões, moderação e administração — Implementado

* `POST /api/v1/suggestions` — Estudante envia proposta pendente; autoria obtida da sessão. Usa os campos de `EventCreate`, sem permitir escolha de autor ou status.
* RPC Supabase `listar_sugestoes(p_status, p_busca, p_offset)` — Professor/admin; pendências e histórico com páginas de 20.
* RPC `moderar_sugestao(p_evento_id, p_status, p_justificativa)` — Professor/admin; aprova ou rejeita apenas pendentes. Recusa exige justificativa de até 2.000 caracteres.
* RPC `admin_buscar_usuarios(p_busca, p_papel, p_confirmado, p_offset)` — Admin; usuários, confirmação de e-mail, último acesso e paginação de 20.
* RPC `admin_definir_papel(p_usuario_id, p_novo_papel, p_papel_atual)` — Admin; detecta mudança concorrente e chama `admin_alterar_papel`. Impede remoção do próprio cargo administrativo. Permite atribuir professor a e-mail não institucional; cadastro/autopromoção continuam exigindo `@unb.br`.

Essas RPCs são chamadas pelo SDK Supabase autenticado. As rotas FastAPI `/admin/events/pending`, `/admin/events/{id}/review` e `/admin/users/{id}/role` sugeridas anteriormente não estão implementadas. As notificações usam leitura da tabela `notificacoes` e atualização somente de `lida_em`, restritas ao destinatário.

### 🎟️ Inscrição Direta em Eventos (`/api/v1/events/:id/attend`) — *Planejado, sem endpoint implementado*
* `POST /api/v1/events/:id/attend` — Inscrever o usuário autenticado no evento
* `DELETE /api/v1/events/:id/attend` — Cancelar inscrição no evento
* `GET /api/v1/events/:id/attendees` — Listar participantes do evento (para organizadores/admin)

### 🏷️ Categorias (`/api/v1/categories`) — *Planejado, sem endpoint implementado*
* `GET /api/v1/categories` — Listar todas as categorias de eventos
* `POST /api/v1/categories` — Criar uma nova categoria (apenas administradores)
* `DELETE /api/v1/categories/:id` — Remover uma categoria

---

## 5. Códigos de Resposta HTTP Padronizados

* `200 OK`: Requisição processada com sucesso.
* `204 No Content`: Exclusão de evento ou remoção de vínculo concluída, sem corpo de resposta.
* `422 Unprocessable Entity`: Falha de validação de campos, campus/categoria desconhecidos ou intervalo de datas inválido.
* `503 Service Unavailable`: Falha de acesso ao banco ou à validação da sessão no Supabase.
* `201 Created`: Recurso (evento/usuário/inscrição) criado com sucesso.
* `202 Accepted`: Arquivo de plano de ensino recebido e em processamento assíncrono.
* `400 Bad Request`: Dados inválidos enviados pelo frontend (ex: formato de arquivo não suportado, datas inconsistentes).
* `401 Unauthorized`: Usuário não autenticado ou token inválido/expirado.
* `403 Forbidden`: Usuário não possui permissão para esta ação (ex: não administrador tentando moderar eventos).
* `404 Not Found`: Recurso não encontrado (ex: evento ou plano de ensino inexistente).
* `409 Conflict`: Conflito de regras de negócio (ex: usuário já inscrito no evento).
* `500 Internal Server Error`: Erro inesperado no servidor.


## 6. Entidades adicionadas após a R1

- `SavedPublicEvent` / `eventos_salvos`: chave composta `(user_id, event_id)`, `criado_em`, referências com exclusão em cascata e RLS por proprietário; sem política de UPDATE.
- `notificacoes`: `id`, `usuario_id`, `evento_id`, `tipo` (`submissao`, `aprovacao`, `recusa`), `titulo_evento`, `justificativa`, `criado_em`, `lida_em`. Somente o destinatário lê e marca como lida.
- `eventos`: acrescenta `justificativa_recusa`, `interessados_count` e `sugestao_estudante`. Status persistidos continuam em português: `pendente`, `aprovado`, `rejeitado`.

A existência de colunas de contagem ou entidades de planejamento não implica endpoints ou fluxos de inscrição implementados. O estado atual está em [Atualizações pós-R1](atualizacoes.md).
