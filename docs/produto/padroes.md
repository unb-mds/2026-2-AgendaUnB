---
title: "Padrões de projeto"
description: "Convenções de código, nomenclatura e contratos do Agenda UnB."
---

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
| **Candidato a Avaliação** | `AssessmentCandidate` | Sugestão privada ou compartilhada de avaliação com evidência de página/trecho; só entra na agenda pessoal após revisão e confirmação explícita do usuário. |
| **Calendário / Agenda** | `Calendar` | Coleção/agrupamento de eventos de um usuário ou do campus. |
| **Categoria / Etiqueta** | `Category` | Classificação de evento público ou pessoal (ex: *Acadêmico*, *Cultura*, *Esporte*, *Extensão*, *Lazer*, *Comunicado*), distinta dos tipos de avaliação (*Prova*, *Trabalho*, *Seminário*). |
| **Notificação** | `Notification` | Aviso persistido de submissão, aprovação ou recusa de sugestão. |
| **Lembrete** | `Reminder` | Alerta futuro programado antes do início de um evento. |
| **Evento público salvo** | `SavedPublicEvent` | Vínculo do usuário com um evento público na agenda pessoal. |
| **Moderação / Submissão** | `Review` / `Submission` | Fluxo de validação de eventos propostos por usuários antes de entrarem na agenda pública. |

---

## 2. Convenções de Escrita (*Naming Conventions*)

No worker de extração, os nomes em português do contrato de persistência em candidatos e metadados de IA são preservados; respostas de rastreamento HTTP usam aliases `camelCase`.
Os estados do plano são `pendente`, `processando`, `concluido` e `falha`; os estados do candidato são `pendente`, `descartado` e `confirmado`. O extrator grava apenas `pendente`, sem confirmar ou converter em evento. Consulte [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos) e [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia).

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
* `autor_id` / `author_id`: ID do criador do evento (nulo em eventos coletados de fontes institucionais)
* `titulo` / `title`: Título do evento
* `descricao` / `description`: Detalhes, ementa ou notas sobre a atividade
* `localizacao` / `location`: Local físico ou link
* `data_evento` / `starts_at` e `data_fim` / `ends_at`: Início e fim exclusivo (`ISO 8601`), acompanhados de `dia_inteiro` / `all_day`, `data_inicio_civil` / `start_date` e `data_fim_civil` / `end_date`
* `link_externo` / `external_url`: URL externa oficial
* `campus_id`: ID do campus associado
* `category_id`: ID da categoria associada
* `status`: Status de moderação (`"pendente"`, `"aprovado"`, `"rejeitado"`)
* `justificativa_recusa`, `interessados_count` e `sugestao_estudante`: Metadados de moderação e contagem agregada de redirecionamentos em "Conferir evento"
* `criado_em`: Data de registro no sistema

### 📅 `PersonalEvent` / `eventos_pessoais` (Evento Pessoal / Agenda Privada)
* `id`: Identificador único do evento (`UUID`)
* `user_id`: ID do proprietário (`UUID`, restrito via RLS)
* `titulo` / `title`: Título do compromisso ou prazo
* `descricao` / `description`: Detalhes sobre o prazo
* `localizacao` / `location`: Local opcional do compromisso
* `data_hora` / `starts_at` e `data_fim` / `ends_at`: Início e fim exclusivo (`ISO 8601`), com suporte a `dia_inteiro`, `data_inicio_civil` e `data_fim_civil`
* `campus_id` e `category_id`: Associações opcionais
* `origem_versao_id` e `origem_avaliacao_id`: Rastreio opcional da avaliação importada de um plano (com unicidade para importação idempotente)
* `criado_em`: Data de criação

### 📄 `Syllabus`, `SyllabusVersion`, `Subject`, `ClassOffering` e `ClassFollow`
* `Syllabus` / `planos_ensino`: Guarda metadados do envio, vínculo à oferta, texto sanitizado e estados `pendente`, `processando`, `concluido` e `falha`. O PDF é descartado após a extração local, e a autorização sobre o texto exato é registrada antes do envio à IA. Consulte [Dados de planos](/arquitetura/dados-de-planos), [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos) e [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia).
* `SyllabusVersion` / `versoes_plano`: Versões de um plano, `privada` por padrão ou `compartilhada` na oferta; leitura pelo dono ou por seguidores da turma quando compartilhada. `avaliacoes` referencia `versao_id` e `ordem`.
* `Subject` / `disciplinas` e `ClassOffering` / `ofertas_turma`: Disciplina e sua oferta em um período (`turma`, `ano`, `semestre` 1 ou 2), com leitura pública e escrita restrita ao back-end.
* `ClassFollow` / `vinculos_turma`: Chave `(user_id, oferta_id)`, representando vínculo autodeclarado com leitura restrita ao próprio usuário.

### 🔔 `SavedPublicEvent`, `Notification` e `Reminder`
* `SavedPublicEvent` / `eventos_salvos`: Chave composta `(user_id, event_id)`, `criado_em`, referências com exclusão em cascata e RLS por proprietário.
* `Notification` / `notificacoes`: `id`, `usuario_id`, `evento_id`, `tipo` (`submissao`, `aprovacao`, `recusa`), `titulo_evento`, `justificativa`, `criado_em`, `lida_em`. Leitura e atualização restritas ao destinatário.
* `Reminder` / `lembretes`: Alertas agendados 24 horas antes do início dos eventos da agenda do próprio usuário.

### 🏷️ `Category` / `categories` (Categoria)
* `id`: Identificador da categoria (`UUID`)
* `nome`: Nome da categoria (*"Acadêmico"*, *"Cultura"*, *"Esporte"*, *"Extensão"*, *"Lazer"*, *"Comunicado"*)
* `cor`: Código hexadecimal de cor (ex: `"#008bff"`)

---

## 4. Contratos, exceções preservadas e manutenção

O [inventário do backend](/api-specs) e o [modelo de dados](/arquitetura/modelo-de-dados) documentam todas as rotas, payloads e tabelas da plataforma. As rotas de negócio usam o prefixo `/api/v1`, com `/health` como exceção; autenticação usa Supabase Auth e fluxos de moderação/administração usam RPCs do PostgreSQL e rotas dedicadas da API.

A API utiliza campos JSON em inglês (`snake_case` na maior parte das rotas, como `starts_at` e `external_url`, e `camelCase` nos fluxos de rastreamento/confirmação de planos e filtros `startDate`/`endDate`). No banco de dados, preservam-se nomes legados como `profiles`, `categories`, `user_id`, `professor_id`, `category_id`, `event_id`, os mapeamentos distintos de início em `eventos.data_evento` e `eventos_pessoais.data_hora`, bem como os valores de papel (`student`, `professor`, `admin`) e de status em português (`pendente`, `aprovado`, `rejeitado`, `processando`, `concluido`, `falha`, `descartado`, `confirmado`).

Usar os códigos e envelopes documentados por operação em [API](/api-specs#erros-fastapi). RPCs retornam erros pelo caminho do Supabase/PostgreSQL.

Mudanças de contratos e convenções devem atualizar esta documentação juntamente com o código, mantendo alinhamento com [Arquitetura](/arquitetura/visao-geral) e [Implantação](/implantacao).
