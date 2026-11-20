---
title: "Conferir evento e eventos salvos"
description: "Contrato do link oficial, deduplicação de cliques e vínculos da agenda pessoal."
---

**Adicionar aos meus eventos** cria um vínculo com o evento público aprovado. **Conferir evento** abre a página oficial e registra um acionamento agregado. A inscrição acontece no canal do organizador.

| Operação | Comportamento |
| --- | --- |
| `PUT /api/v1/me/saved-events/{event_id}` | Cria ou mantém o vínculo da própria conta. Retorna `200 {"saved": true}` ou 404 se o evento estiver indisponível. |
| `DELETE /api/v1/me/saved-events/{event_id}` | Retorna 204, inclusive em repetição. Remover o vínculo cancela seus lembretes futuros pendentes. |
| `POST /api/v1/events/{event_id}/outbound-clicks` | Aceita `click_id` ou `clickId` (UUID) de visitantes e contas autenticadas. Retorna `external_url`, `outbound_clicks_count` e `incremented`. Retorna 404 para evento indisponível e 422 para link ausente ou inválido. |

A interface abre o link HTTP(S) do evento e registra o acionamento pela API. A gravação independe do vínculo da agenda. Cada par `(evento_id, click_id)` conta uma única vez. Essa métrica mede acionamentos, independentemente de visita efetiva, inscrição ou presença.

O servidor chama `registrar_redirecionamento_evento`, grava em `cliques_evento` e atualiza `eventos.interessados_count` na mesma transação. A tabela contém somente evento, identificador aleatório do clique e horário. A função e a tabela ficam restritas ao servidor. A migração `20261120120000_consolida_cliques_e_fila_planos.sql` combina as chaves do registro duplicado e preserva o contador já publicado.

Em **Meus Eventos**, filtros por período se aplicam a compromissos privados e eventos públicos salvos na lista e no calendário.

Os testes `test_event_clicks_database.py`, `test_events_api.py`, `test_saved_events_api.py` e `test_reminders_database.py` cobrem deduplicação, acesso ao contador, isolamento de vínculos e cancelamento de lembretes. Consulte os [contratos da API](/api-specs) e a [operação dos lembretes](/arquitetura/dados-de-eventos#agendador).
