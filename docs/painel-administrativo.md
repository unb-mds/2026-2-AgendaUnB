# Painel administrativo e sugestões

## Navegação e permissões

- `/eventos`: eventos públicos e agenda pessoal. `/segunda-pagina` redireciona para esta rota, preservando parâmetros.
- `/plano-de-ensino`: página independente; informa que a importação de planos ainda está em preparação e oferece acesso à criação manual de eventos pessoais.
- `/sugestoes`: professores e administradores; fila de pendentes, histórico de aprovadas/recusadas, busca e paginação.
- `/admin`: somente administradores; busca por nome/e-mail, filtros de perfil e confirmação de e-mail, último acesso e alteração de cargo com confirmação.

A navbar usa o mesmo indicador sublinhado para todas as páginas. Admin aparece depois de Sugestões com destaque azul. O sino aparece apenas para estudantes.

## Envio e moderação

O estudante abre **Criar Evento** em Eventos e escolhe **Sugerir evento** no campo Visibilidade. **Apenas para mim** continua disponível. Professores e administradores podem publicar diretamente com **Público**. Não há botão nem formulário separado de sugestão.

O endpoint autenticado `POST /api/v1/suggestions` aceita apenas estudantes. A autoria vem da sessão e o banco força o status `pendente`. O frontend não adiciona a proposta à lista pública antes da aprovação.

A RPC `moderar_sugestao` verifica o perfil no banco e permite decidir apenas sugestões pendentes. A recusa exige justificativa de até 2.000 caracteres. Decisões concorrentes retornam erro legível, sem sobrescrever a decisão anterior. O histórico preserva o texto enviado ao estudante.

Notificações de envio, aprovação e recusa são persistidas por trigger na mesma transação do evento. O sino atualiza ao enviar, ao retornar à janela e a cada 30 segundos. O estudante pode marcar notificações como lidas; a RLS restringe leitura e atualização ao próprio destinatário.

## Administração

As RPCs administrativas verificam o perfil real no banco. A troca de cargo detecta alterações concorrentes e impede o administrador de remover o próprio acesso. O cadastro e a autopromoção para professor exigem e-mail `@unb.br`; um administrador pode atribuir esse perfil mesmo a outro endereço. Nenhuma chave de serviço é exposta ao navegador.

## Migração

Aplicar `supabase/migrations/20261018000000_moderacao_e_notificacoes.sql` e `supabase/migrations/20261018000100_admin_professor_email_livre.sql` após as migrações existentes:

```sh
supabase migration up --local
```

A migração acrescenta permissões de moderação para professores, RPCs e notificações. Marca eventos de estudantes já existentes como sugestões, mas não gera notificações retroativas. Para outro ambiente, aplicar pelo fluxo habitual de migrações do projeto. A conta administrativa de teste foi criada apenas no Supabase local; credenciais não fazem parte do repositório.

## Validação

```sh
cd frontend
npm run build
node --test src/lib/calendar.test.js
cd ../backend
python -m pytest tests -q
```

Para incluir os testes reais de RLS/RPC/triggers, configure `TEST_SUPABASE_DB_URL` com a conexão PostgreSQL do Supabase local antes de executar pytest. Esses testes aceitam somente localhost/127.0.0.1 e desfazem seus dados ao terminar. Sem a variável, são ignorados.


## API REST administrativa

Todas as rotas abaixo exigem `Authorization: Bearer <token>` validado pelo Supabase e cargo atual `admin` no banco. Ausencia de credenciais ou token invalido retorna 401; outro cargo retorna 403.

- `GET /api/v1/admin/events/pending?offset=0&limit=20`: lista somente pendentes, ordenados por criacao e ID. Limite maximo: 100.
- `PATCH /api/v1/admin/events/{id}/review`: recebe `{"status":"rejeitado","justificativa_recusa":"Motivo"}` ou `{"status":"aprovado"}`. Recusa exige texto de ate 2.000 caracteres. Aprovacao limpa justificativa. Evento inexistente retorna 404; revisao anterior retorna 409. Atualizacao condicional impede sobrescrever decisoes concorrentes e preserva os triggers de notificacao.
- `GET /api/v1/admin/users?busca=&papel=&confirmado=&offset=0`: reutiliza `admin_buscar_usuarios`, com pagina de 20 e resposta `items`, `total`, `all`, `unconfirmed`. Filtros de confirmacao: vazio, `sim`, `nao`. Retorna identificador, nome, email, papel, criacao, ultimo login e confirmacao; nunca retorna segredos de autenticacao.
- `PATCH /api/v1/admin/users/{id}/role`: recebe `{"role":"student"}`, `professor` ou `admin`. Campos extras sao rejeitados. Revalida o administrador dentro da transacao; 404 para alvo inexistente e 409 ao rebaixar o ultimo administrador. Permite rebaixar a propria conta quando existe outro administrador. O modelo atual nao possui indicador de administrador ativo; a protecao conta os perfis com papel admin.

A troca de cargo usa bloqueio transacional da tabela profiles no PostgreSQL, serializando inclusive escritores das RPCs existentes. Isso privilegia integridade, podendo aumentar a espera em alteracoes simultaneas de perfis. O usuario de banco do backend precisa das permissoes para esse bloqueio e para atualizar profiles/eventos. A listagem depende das migracoes administrativas existentes e usa identidade definida apenas durante a transacao. As alteracoes emitem logs com autor, alvo e resultado, sem justificativas ou dados pessoais. Nenhuma migracao nova e necessaria.

Os testes de API usam SQLite; a listagem de usuarios simula a RPC. Os testes PostgreSQL de RPC/RLS/triggers e bloqueio exigem `TEST_SUPABASE_DB_URL` local. Sem essa configuracao, sao ignorados e nao comprovam o comportamento concorrente no ambiente de implantacao.
