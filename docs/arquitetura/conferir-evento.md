---
title: "Dados de Conferir evento: redirecionamento por clique e histórico"
description: "Como a API, o banco e a interface tratam os vínculos salvos, os redirecionamentos de Conferir evento e os históricos separados (S8-B02)."
---

# Dados de Conferir evento: redirecionamento por clique e histórico

Guia de integração da migração `20261117151000_eventos_conferir_evento.sql` (conciliada com `20261117200000_s8_f02_eventos_moderacao_categorias.sql` e `20261117152000_eventos_lembretes.sql`), entregando a [S8-B02 (#79)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/79).

**Regra geral:** o que precisa valer em qualquer caminho de escrita está em chaves únicas, triggers e funções no PostgreSQL. A aplicação chama as funções e projeta os contratos HTTP; não reimplementa as regras no navegador.

## 1. Vínculos de eventos salvos e cancelamento de lembretes (RF12, RF13)

- `PUT /api/v1/me/saved-events/{event_id}` → `200 {"saved": true}`: cria vínculo único `(user_id, event_id)` em `public.eventos_salvos`. Adicionar repetidas vezes é idempotente e mantém um único registro. Eventos inexistentes, pendentes ou rejeitados retornam `404`.
- `DELETE /api/v1/me/saved-events/{event_id}` → `204`: remove o próprio vínculo de forma idempotente e cancela lembretes futuros pendentes associados ao par `(user_id, event_id)` (via trigger `eventos_salvos_agenda_lembrete` no PostgreSQL e sincronização no ORM em SQLite). Uma conta nunca altera nem remove vínculos de outra conta.

## 2. Conferir evento: redirecionamento deduplicado por clique (RF12)

```python
@router.post("/events/{event_id}/outbound-clicks", response_model=OutboundClickRead)
def register_outbound_click(
    event_id: UUID,
    payload: OutboundClickCreate,
    db: Session = Depends(get_db),
) -> OutboundClickRead:
```

- `POST /api/v1/events/{event_id}/outbound-clicks` aceita `{"click_id": UUID}` (ou `{"clickId": UUID}`) e devolve `200 {"external_url": "https://...", "outbound_clicks_count": int, "incremented": bool}`.
- Disponível para visitantes e usuários autenticados.
- Só devolve o link de evento **aprovado** (`404` se inexistente ou não aprovado) e com URL `http(s)` válida (`422` quando não há link oficial disponível; `P0002` na função SQL direta `registrar_clique_evento`).
- O mesmo `click_id` para o mesmo evento conta uma única vez (`cliques_evento` e `eventos_cliques_redirecionamento`). Outro `click_id` incrementa `eventos.interessados_count` (`outbound_clicks_count` / `redirect_count` no ORM).
- O registro guarda apenas `evento_id`, `click_id` e `criado_em`. Não há usuário, IP ou `User-Agent`: o contador não identifica pessoas e não mede visitantes únicos, inscrição externa ou presença.
- Acionar **Conferir evento** nunca adiciona o evento à agenda pessoal (`eventos_salvos`) nem cria entrada no histórico do usuário.
- A função legada `registrar_interesse(uuid)` foi removida.

## 3. Históricos separados para públicos salvos passados e compromissos privados passados (RF18)

- `GET /api/v1/me/events/history` (autenticado, `Cache-Control: no-store`) retorna listas separadas de eventos já encerrados da conta:
  - `saved_public_events`: eventos públicos aprovados vinculados em `eventos_salvos` cujo término (`ends_at`, ou `starts_at` quando sem término) é anterior ao instante de referência, ordenados do mais recente ao mais antigo.
  - `personal_events`: compromissos privados em `eventos_pessoais` cujo término (`ends_at` ou `starts_at`) já passou, ordenados do mais recente ao mais antigo.
- Na interface (**Meus Eventos** em `SecondPage.jsx`, com utilitário `splitMyEventsByHistory` em `frontend/src/lib/calendar.js`), os itens passados são exibidos em duas seções distintas:
  1. **Histórico — Eventos públicos salvos passados**
  2. **Histórico — Compromissos privados passados**
- Eventos públicos apenas abertos pelo botão **Conferir evento** não aparecem em nenhum dos dois históricos.

## 4. Quem pode o quê

| Recurso | Visitante | Conta logada (navegador) | Professor / admin | Servidor |
| --- | --- | --- | --- | --- |
| `registrar_clique_evento` | Não | Não | Não | Sim |
| `POST /api/v1/events/{id}/outbound-clicks` | Sim (eventos aprovados com URL) | Sim | Sim | Sim |
| `cliques_evento` / `eventos_cliques_redirecionamento` | Sem acesso | Sem acesso | Sem acesso | Sim |
| `eventos.interessados_count` | Lê (catálogo) | Lê; não altera diretamente | Lê; não altera diretamente | Sim |
| `PUT/DELETE /api/v1/me/saved-events/{id}` | Não (`401`) | Apenas o próprio vínculo | Apenas o próprio vínculo | Sim |
| `GET /api/v1/me/events/history` | Não (`401`) | Apenas o próprio histórico separado | Apenas o próprio histórico separado | Sim |

## 5. Testes e Validação Técnica — S8-B02 (#79)

```bash
# Testes de banco PostgreSQL/Supabase local
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  python -m pytest tests/test_event_clicks_database.py tests/test_reminders_database.py -q

# Testes de contrato HTTP FastAPI (vínculos salvos, cliques deduplicados, lembretes e históricos separados)
cd backend && PYTHONPATH=. venv/bin/pytest tests/test_saved_events_api.py tests/test_events_api.py tests/test_reminders_api.py -q

# Testes unitários do frontend (separação de históricos em Meus Eventos e cache)
cd frontend && node --test src/lib/*.test.js
```

| Critério de Aceite (#79) | Evidência Técnica e Testes | Resultado |
| --- | --- | --- |
| **1. Repetir adição e remoção sem duplicar vínculo. Verificar histórico, agenda e cancelamento de lembrete futuro** | `test_save_is_idempotent_and_preserves_public_data`, `test_database_rejects_duplicate_links` e `test_removing_saved_event_cancels_future_reminder_and_history_separates_past_lists` em `backend/tests/test_saved_events_api.py`; `test_saved_public_event_reminder_follows_the_event` em `backend/tests/test_reminders_database.py`; `splitMyEventsByHistory` em `frontend/src/lib/calendar.test.js` | Aprovado |
| **2. Abrir o link oficial, verificar incremento do redirecionamento e ausência de mudança na agenda. Repetir a mesma requisição sem duplicar o contador** | `test_redirect_is_counted_once_per_click` e `test_click_log_holds_no_person_and_is_closed_to_the_browser` em `backend/tests/test_event_clicks_database.py`; `test_outbound_clicks_are_deduplicated_and_independent_of_saved_events` em `backend/tests/test_events_api.py` | Aprovado |
| **3. Recusar adição de evento indisponível e alteração de vínculo de outra conta** | `test_users_only_remove_their_own_links` e `test_unapproved_missing_and_deleted_events` em `backend/tests/test_saved_events_api.py`; `test_saved_events_are_private_and_only_for_approved_events` em `backend/tests/test_security_database.py` | Aprovado |

### Revisão de Contratos, Permissões e Dados Afetados

- **Responsável principal:** `@marrathomaz` | **Corresponsável:** `@felipecduque7` | **Apoio na interface e histórico:** `@Bielziin07`.
- **Contratos revisados:** `PUT /api/v1/me/saved-events/{event_id}`, `DELETE /api/v1/me/saved-events/{event_id}`, `POST /api/v1/events/{event_id}/outbound-clicks` e `GET /api/v1/me/events/history`.
- **Permissões e dados afetados:** `public.eventos_salvos` (PK `(user_id, event_id)`, RLS por `auth.uid()`), `public.cliques_evento` e `public.eventos_cliques_redirecionamento` (RLS ativo, sem PII, fechadas a escrita direta de clientes), `public.eventos.interessados_count` (atualizado apenas por função atômica com deduplicação por `click_id`) e `public.lembretes` (cancelamento automático de avisos `pendente` ao remover o vínculo).
