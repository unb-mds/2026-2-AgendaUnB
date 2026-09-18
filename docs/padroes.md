# 📖 Glossário e Padronização de Nomenclaturas — Projeto Agenda UnB

Este documento estabelece as convenções de código, terminologia oficial e padrões de rotas da API para garantir consistência entre o **Frontend** e o **Backend** da aplicação **Agenda UnB**.

---

## 1. Glossário de Domínio (Entidades Principais)

Utilizaremos o **Inglês** como idioma padrão para código, variáveis, entidades, rotas e banco de dados. Os textos da interface com o usuário (UI) permanecem em Português.

| Termo (PT-BR) | Termo Oficial (Código) | Descrição / Uso |
| :--- | :--- | :--- |
| **Usuário** | `User` | Conta de acesso da pessoa na aplicação (Estudante, Professor ou Administrador). |
| **Papel / Tipo de Usuário** | `Role` | Nível de acesso do usuário (`student`, `professor`, `admin`). |
| **Evento / Compromisso** | `Event` | Registro de uma atividade na agenda (acadêmica pessoal ou geral do campus). |
| **Plano de Ensino** | `Syllabus` | Arquivo (PDF ou texto) enviado para extração automática de datas acadêmicas. |
| **Calendário / Agenda** | `Calendar` | Coleção/agrupamento de eventos de um usuário ou do campus. |
| **Categoria / Etiqueta** | `Category` | Classificação do evento (ex: *Prova*, *Trabalho*, *Seminário*, *Cultural*, *Palestra*). |
| **Notificação / Lembrete** | `Reminder` | Alerta programado antes do início de um evento. |
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
| **Campos do Banco de Dados** | `camelCase` *(ou `snake_case`)* | `createdAt`, `startTime`, `userId`, `approvalStatus` |
| **Constantes Globais e Enums** | `UPPER_SNAKE_CASE` | `MAX_EVENTS_PER_DAY`, `DEFAULT_PORT`, `ROLE_STUDENT` |
| **Classes CSS** | `kebab-case` | `.modal-btn-primary`, `.role-selector`, `.nav-items` |

---

## 3. Estrutura de Atributos dos Modelos (Campos de Dados)

### 👤 `User` (Usuário)
* `id`: Identificador único (`UUID` ou `ObjectId`)
* `name`: Nome completo
* `email`: Endereço de e-mail institucional ou pessoal
* `passwordHash`: Senha criptografada (opcional se autenticado via OAuth)
* `role`: Papel no sistema (`"student"`, `"professor"`, `"admin"`)
* `provider`: Método de login (`"local"`, `"google"`)
* `googleId`: ID exclusivo fornecido pelo Google (quando autenticado via Google)
* `avatarUrl`: URL da foto de perfil
* `createdAt`: Data de criação da conta
* `updatedAt`: Data da última alteração de perfil

### 📅 `Event` (Evento / Prazo Acadêmico)
* `id`: Identificador único do evento
* `userId`: ID do criador/proprietário do evento (Chave Estrangeira)
* `title`: Título do evento ou prazo (ex: *"Prova 1 - Cálculo 1"*, *"Semana Universitária"*)
* `description`: Detalhes, ementa ou notas sobre a atividade
* `location`: Local físico (ex: *"ICC Sul - Sala AT 03/12"*) ou link de videochamada
* `startDate`: Data e hora de início (`ISO 8601`: `YYYY-MM-DDTHH:mm:ssZ`)
* `endDate`: Data e hora de término (`ISO 8601`)
* `isAllDay`: Booleano (`true`/`false`) indicando se dura o dia todo
* `visibility`: Visibilidade do evento:
  * `"private"`: Evento pessoal / prazo acadêmico individual
  * `"public"`: Evento divulgado no calendário geral do campus
* `status`: Andamento do evento (`"scheduled"`, `"cancelled"`, `"completed"`)
* `approvalStatus`: Status de moderação para eventos públicos:
  * `"pending"`: Aguardando avaliação de um moderador/administrador
  * `"approved"`: Aprovado e visível na agenda pública
  * `"rejected"`: Recusado pela moderação
* `source`: Origem do evento (`"manual"`, `"syllabus_extraction"`, `"instagram_sync"`, `"unb_feed"`)
* `syllabusId`: ID do plano de ensino que originou a data (se aplicável)
* `categoryId`: ID da categoria associada
* `createdAt`: Data de registro no sistema
* `updatedAt`: Data da última alteração

### 📄 `Syllabus` (Plano de Ensino)
* `id`: Identificador único do arquivo/processamento
* `userId`: ID do usuário que realizou o upload
* `fileName`: Nome original do arquivo enviado (ex: *"Plano_MDS_2026_2.pdf"*)
* `fileUrl`: URL do arquivo armazenado (ex: bucket S3 ou Supabase Storage)
* `fileType`: Tipo do arquivo (`"pdf"`, `"text"`)
* `status`: Status do processamento por IA/parser (`"pending"`, `"processing"`, `"completed"`, `"failed"`)
* `extractedEventsCount`: Quantidade de prazos/provas identificados
* `errorMessage`: Descrição do erro, caso o processamento falhe
* `createdAt`: Data e hora do envio

### 🏷️ `Category` (Categoria)
* `id`: Identificador da categoria
* `name`: Nome da categoria (*"Prova"*, *"Trabalho"*, *"Seminário"*, *"Palestra"*, *"Cultural"*, *"Esporte"*)
* `colorHex`: Código hexadecimal de cor (ex: `"#008BFF"`)

### 🎟️ `Attendee` (Inscrição em Evento)
* `id`: Identificador único do registro
* `eventId`: ID do evento associado
* `userId`: ID do usuário inscrito
* `registeredAt`: Data e hora da inscrição

---

## 4. Padronização de Rotas da API REST (`Endpoints`)

Todas as rotas iniciam com o prefixo `/api/v1`.

### 🔑 Autenticação (`/api/v1/auth`)
* `POST /api/v1/auth/register` — Criar nova conta local (Nome, Email, Senha, Role)
* `POST /api/v1/auth/login` — Autenticar usuário com email e senha
* `POST /api/v1/auth/google` — Autenticar ou cadastrar com token OAuth do Google
* `POST /api/v1/auth/logout` — Encerrar sessão ativa
* `GET /api/v1/auth/me` — Obter dados do usuário autenticado no momento

### 📅 Eventos e Agenda (`/api/v1/events`)
* `GET /api/v1/events` — Listar eventos visíveis ao usuário (suporta filtros: `?visibility=...&startDate=...&endDate=...&categoryId=...`)
* `GET /api/v1/events/:id` — Obter detalhes de um evento específico
* `POST /api/v1/events` — Criar um novo evento (se público por usuário comum, nasce como `"pending"`)
* `PUT /api/v1/events/:id` — Atualizar dados de um evento existente
* `PATCH /api/v1/events/:id/status` — Atualizar andamento (`scheduled`, `cancelled`, `completed`)
* `DELETE /api/v1/events/:id` — Excluir um evento

### 🎟️ Inscrição Direta em Eventos (`/api/v1/events/:id/attend`)
* `POST /api/v1/events/:id/attend` — Inscrever o usuário autenticado no evento
* `DELETE /api/v1/events/:id/attend` — Cancelar a inscrição do usuário no evento
* `GET /api/v1/events/:id/attendees` — Listar participantes do evento (para organizadores/admin)

### 📄 Processamento de Planos de Ensino (`/api/v1/syllabus`)
* `POST /api/v1/syllabus/upload` — Enviar arquivo PDF ou texto bruto de plano de ensino
* `GET /api/v1/syllabus` — Listar planos de ensino enviados pelo usuário
* `GET /api/v1/syllabus/:id` — Obter status do processamento e eventos extraídos

### 🛡️ Moderação e Administração (`/api/v1/admin`)
* `GET /api/v1/admin/events/pending` — Listar eventos submetidos pela comunidade aguardando aprovação
* `PATCH /api/v1/admin/events/:id/review` — Aprovar (`"approved"`) ou rejeitar (`"rejected"`) a publicação de um evento público

### 🏷️ Categorias (`/api/v1/categories`)
* `GET /api/v1/categories` — Listar todas as categorias de eventos
* `POST /api/v1/categories` — Criar uma nova categoria (apenas administradores)
* `DELETE /api/v1/categories/:id` — Remover uma categoria

---

## 5. Códigos de Resposta HTTP Padronizados

* `200 OK`: Requisição processada com sucesso.
* `201 Created`: Recurso (evento/usuário/inscrição) criado com sucesso.
* `202 Accepted`: Arquivo de plano de ensino recebido e em processamento assíncrono.
* `400 Bad Request`: Dados inválidos enviados pelo frontend (ex: formato de arquivo não suportado, datas inconsistentes).
* `401 Unauthorized`: Usuário não autenticado ou token inválido/expirado.
* `403 Forbidden`: Usuário não possui permissão para esta ação (ex: não administrador tentando moderar eventos).
* `404 Not Found`: Recurso não encontrado (ex: evento ou plano de ensino inexistente).
* `409 Conflict`: Conflito de regras de negócio (ex: usuário já inscrito no evento).
* `500 Internal Server Error`: Erro inesperado no servidor.
