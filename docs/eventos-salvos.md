# Eventos públicos na agenda pessoal

O botão **Adicionar aos meus eventos** salva um vínculo com o evento público aprovado.
Os dados não são copiados: título, data, local e organizador são lidos do original.
Em **Meus Eventos**, o frontend combina os eventos privados com os públicos salvos,
mantendo busca, filtros, lista e calendário. Um público salvo pode ser removido da
agenda, mas não editado ou excluído como se fosse um evento privado.

## Banco e implantação

Aplicar `supabase/migrations/20261016000000_adiciona_eventos_salvos.sql` no ambiente
de destino **antes** de disponibilizar a nova API/frontend. A migração cria
`public.eventos_salvos`, com chave primária `(user_id, event_id)`, FKs com exclusão
em cascata e políticas RLS que restringem cada vínculo ao seu usuário. Não há
política de UPDATE; para mudar um vínculo, removê-lo e criar outro.

O backend também limita todas as operações ao usuário da sessão validada, pois
conexões administrativas ao banco podem ignorar RLS. A migração não altera eventos
existentes. A exclusão de um evento público remove seus vínculos; eventos que
deixarem de estar aprovados não aparecem nas consultas da agenda.

## API autenticada

| Método | Rota | Resultado |
| --- | --- | --- |
| GET | `/api/v1/me/saved-events` | Eventos públicos aprovados salvos pelo usuário |
| GET | `/api/v1/me/saved-events/{id}` | `{ "saved": true/false }` |
| PUT | `/api/v1/me/saved-events/{id}` | Salva sem duplicar, retorna `{ "saved": true }` |
| DELETE | `/api/v1/me/saved-events/{id}` | Remove somente o vínculo, retorna 204 |

PUT e DELETE são idempotentes. PUT retorna 404 para evento inexistente ou não
aprovado. Todas as rotas exigem autenticação; o cliente nunca escolhe `user_id`.
O CRUD privado em `/me/events` continua independente.

## Verificação

Executar `python -m pytest` em `backend` e `npm run build` em `frontend`.
Os testes de eventos salvos verificam autenticação, isolamento entre usuários,
idempotência, leitura dos dados atualizados, eventos não aprovados e cascata.
Os testes usam SQLite com FKs ativas; as políticas RLS da migração precisam ser
verificadas em PostgreSQL/Supabase após aplicar a migração no ambiente de teste.
