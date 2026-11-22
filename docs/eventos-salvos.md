# Eventos públicos na agenda pessoal

A ação **Adicionar aos meus eventos** cria um vínculo em `eventos_salvos` com um evento público aprovado, sem duplicar seus dados. Título, descrição, data, local e organizador são sempre lidos do registro original em `eventos`.

Em **Meus Eventos**, o frontend unifica compromissos privados (`eventos_pessoais`) e eventos públicos salvos, mantendo busca, filtros por período, lista e calendário. Um evento público salvo pode ser removido da agenda pessoal a qualquer momento, mas alterações de conteúdo permanecem restritas ao autor ou à administração na origem. A ação **Conferir evento** opera de forma independente, abrindo o link externo oficial e contabilizando acionamentos agregados; inscrições ocorrem exclusivamente no canal do organizador.

## Banco de dados e isolamento

A tabela `public.eventos_salvos` possui chave primária composta `(user_id, event_id)`, chaves estrangeiras com exclusão em cascata (`ON DELETE CASCADE`) para `profiles` e `eventos` e políticas RLS que restringem leitura, inserção e exclusão ao proprietário com e-mail confirmado (não há política de `UPDATE`).

O backend também filtra todas as operações pelo usuário autenticado da sessão, pois conexões administrativas ao PostgreSQL podem ignorar RLS. A exclusão de um evento público remove seus vínculos em cascata; eventos retirados do catálogo (`status <> 'aprovado'`) deixam de aparecer nas consultas da agenda e têm seus lembretes pendentes cancelados.

## API autenticada

Consulte os [contratos de eventos salvos](/api-specs#eventos-salvos) para métodos, parâmetros e códigos de resposta.

`PUT /api/v1/me/saved-events/{event_id}` e `DELETE /api/v1/me/saved-events/{event_id}` são idempotentes: `PUT` retorna `404` para evento inexistente ou não aprovado e recupera colisões concorrentes quando o vínculo já existe; `DELETE` retorna `204` e cancela lembretes futuros pendentes do vínculo. O CRUD privado em `/api/v1/me/events` permanece independente.

## Verificação

Os testes automatizados em `backend/tests/test_saved_events_api.py` verificam autenticação, isolamento entre contas, idempotência, leitura de dados atualizados na origem, ocultação de eventos não aprovados e remoção em cascata. A validação de políticas RLS e triggers de lembretes no PostgreSQL é coberta em `backend/tests/test_reminders_database.py` e `backend/tests/test_moderation_database.py` com Supabase local.
