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
