---
title: "Conferir evento e eventos salvos"
description: "Contrato do link oficial, deduplicação anônima de cliques e vínculos da agenda pessoal."
---

**Adicionar aos meus eventos** cria um vínculo com o evento público aprovado em **Meus Eventos**. **Conferir evento** abre a página oficial externa e registra um acionamento agregado sem identificar o usuário. A inscrição em atividades acontece exclusivamente no canal do organizador.

| Operação | Comportamento |
| --- | --- |
| `PUT /api/v1/me/saved-events/{event_id}` | Cria ou mantém o vínculo da própria conta. Retorna `200 {"saved": true}` ou `404` se o evento estiver indisponível. |
| `DELETE /api/v1/me/saved-events/{event_id}` | Retorna `204`, inclusive em repetição. Remover o vínculo cancela seus lembretes futuros pendentes. |
| `POST /api/v1/events/{event_id}/outbound-clicks` | Aceita `click_id` ou `clickId` (UUID) de visitantes e contas autenticadas. Retorna `external_url`, `outbound_clicks_count` e `incremented`, ou `404` para evento indisponível e `422` para link ausente ou inválido. |

A interface abre o link `http(s)` do evento e registra o acionamento pela API de forma independente do vínculo na agenda pessoal. A página `/evento/:id` reutiliza o mesmo `click_id` por visualização para evitar contagem dupla em cliques repetidos; cada par `(evento_id, click_id)` é contabilizado uma única vez. A métrica mede acionamentos únicos por visualização ao link oficial e não representa inscrições efetivas nem presença.

O servidor invoca `public.registrar_redirecionamento_evento(p_evento_id, p_click_id)`, grava em `cliques_evento` (contendo apenas `evento_id`, `click_id` e `criado_em`, sem usuário, IP ou `User-Agent`) e incrementa `eventos.interessados_count` na mesma transação. Tanto a função quanto a tabela são restritas ao servidor (`service_role`).

Em **Meus Eventos**, filtros por período se aplicam de forma unificada a compromissos privados e eventos públicos salvos na visualização em lista e no calendário.

A cobertura automatizada inclui `backend/tests/test_event_clicks_database.py`, `backend/tests/test_events_api.py`, `backend/tests/test_saved_events_api.py` e `backend/tests/test_reminders_database.py`. Consulte os [contratos da API](/api-specs) e a [operação dos lembretes](/arquitetura/dados-de-eventos#agendador-pg_cron).
