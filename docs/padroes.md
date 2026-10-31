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
| **Python: variáveis e funções** | `snake_case` | `event_id`, `get_current_user`, `list_public_events` |
| **JavaScript: variáveis e funções** | `camelCase` | `eventId`, `toUiEvent`, `listPublic` |
| **Classes, Componentes e Schemas** | `PascalCase` | `EventController`, `CalendarGrid.jsx`, `RegisterModal.jsx`, `UserModel` |
| **Arquivos Python/JS utilitários** | Nomes existentes, Python em `snake_case` | `router.py`, `test_events_api.py`, `api.js`, `moderation.js` |
| **Componentes React** | `PascalCase` | `SaveEventButton.jsx`, `NotificationBell.jsx` |
| **Rotas da API (URLs)** | `kebab-case` | `/api/v1/events`, `/api/v1/me/saved-events` |
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

## 4. Contratos e rotas disponíveis

A referência única é [Contratos do backend](api-specs.md), com inventário, payloads, filtros, acesso, respostas, exemplos e RPCs. As rotas de negócio usam `/api/v1`; `/health` é exceção. Autenticação/cadastro usam Supabase Auth diretamente; moderação/administração usam RPCs, não endpoints FastAPI `/admin`.

A API usa campos em inglês, geralmente `snake_case` (`starts_at`, `external_url`); os filtros de data usam os aliases existentes `startDate` e `endDate`. Papéis são `student`, `professor`, `admin`; status de eventos são `pendente`, `aprovado`, `rejeitado`. Preservar esses valores na integração.

As propostas de upload de planos/atestados, inscrições, validação colaborativa e categorias REST não têm rotas disponíveis. Modelos planejados da seção 3 não são contratos executáveis.

## 5. Respostas e manutenção

Usar os códigos e envelopes documentados por operação em [API](api-specs.md#erros-fastapi). Não presumir que exemplos futuros com 202, inscrições ou parsing já existem. A API possui erros globais próprios; RPCs retornam erros Supabase/PostgreSQL por outro caminho.

Mudanças de contratos e convenções devem atualizar esta documentação no mesmo PR. Registrar limitações observadas em vez de alterar o comportamento descrito para o comportamento desejado. Decisões e evidências ficam em [Arquitetura](Architecture.md); hospedagem proposta fica em [Implantação](implantacao.md).

## 6. Entidades adicionadas após a R1

- `SavedPublicEvent` / `eventos_salvos`: chave composta `(user_id, event_id)`, `criado_em`, referências com exclusão em cascata e RLS por proprietário; sem política de UPDATE.
- `notificacoes`: `id`, `usuario_id`, `evento_id`, `tipo` (`submissao`, `aprovacao`, `recusa`), `titulo_evento`, `justificativa`, `criado_em`, `lida_em`. Somente o destinatário lê e marca como lida.
- `eventos`: acrescenta `justificativa_recusa`, `interessados_count` e `sugestao_estudante`. Status persistidos continuam em português: `pendente`, `aprovado`, `rejeitado`.

A existência de colunas de contagem ou entidades de planejamento não implica endpoints ou fluxos de inscrição implementados. O estado atual está em [Atualizações pós-R1](atualizacoes.md).
