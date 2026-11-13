# Supabase Cloud: migrações e preparação da publicação

Operação autorizada por Heitor Gomes Monteiro em **10/11/2026** no projeto
`pzniltzdhyuzzdqbppjw`. A transação do banco foi confirmada às **12h52 (America/Sao_Paulo)**;
a conclusão do banco foi confirmada depois em uma nova conexão.

## Resultado

Foram aplicadas as cinco migrações pendentes da `dev`, preservando os arquivos SQL
versionados. O histórico remoto passou de **21 para 26 versões** e coincidiu
com o inventário usado na operação. A contagem registra o estado de 10/11/2026.
A `main` recebeu depois as migrações do catálogo `20261110142000` e
`20261111120000`. O histórico remoto delas precisa ser conferido antes do deploy.

| Versão | Alteração |
| --- | --- |
| `20261109110000` | Lease, orçamento e duração do processamento de planos |
| `20261109113000` | Autoria privada, revisão transacional e Storage |
| `20261109120000` | Disciplinas, ofertas, vínculos e versões de planos |
| `20261109185725` | Tabela paralela de fila de processamento IA |
| `20261110120000` | Preparação de texto e autorização explícita antes do provedor |

Antes da operação, existiam **cinco campi e sete categorias**. Não havia usuários,
planos, candidatos, avaliações, eventos ou objetos de Storage. Os doze registros
do catálogo foram preservados. A remoção prevista de `candidatos_avaliacao` foi
permitida somente após confirmar que a tabela estava vazia, sob bloqueio contra
escritas concorrentes.

## Backup e preservação

Foi produzido um backup lógico consistente com `pg_dump 17.11`, no formato
custom, dos esquemas `public`, `auth`, `storage` e `supabase_migrations`,
incluindo estrutura, dados, proprietários e privilégios. A conexão do cliente ao
Session Pooler usou TLS (`sslmode=require`).

O backup fica localmente em
`.supabase/cloud-integration-20261110/before.dump`, fora do versionamento.
O manifesto privado registra contagens e hashes do conteúdo das 48 tabelas do
snapshot. A cópia tem **356.880 bytes** e SHA-256:

```text
effcdb3cf4be4614c2f1349a35574fe113a70c41eea4f917fddea6542c2ae041
```

O arquivo foi inspecionado com `pg_restore --list` e restaurado com sucesso em
um banco local separado, `agendaunb_cloud_rehearsal_20261110`. Os testes rodaram
somente nessa cópia, sem criar contas ou conteúdo sintético na nuvem.
O backup cobre metadados do Storage; não baixa arquivos binários. Não havia
objetos no Storage remoto no momento do snapshot.

Depois do ensaio local, as cinco migrações foram executadas no destino remoto
em uma transação com rollback. Somente após essa aprovação foram aplicadas
juntas em uma segunda transação, incluindo os cinco registros no histórico.
O wrapper `BEGIN/COMMIT` de `20261109185725` foi retirado apenas do comando
executado para evitar um commit intermediário; o arquivo SQL e o texto original
registrado no histórico não foram alterados.

Antes do commit, foram comparados os hashes de todos os campos preexistentes
das tabelas preservadas com o snapshot, inclusive Auth e Storage. A verificação
de histórico conferiu as 26 versões esperadas. Foi emitido `NOTIFY pgrst,
'reload schema'` na mesma transação. Nenhum reset, seed demonstrativo ou reparo
automático de histórico foi executado.

Para recuperação, primeiro restaurar esse backup em **outro banco isolado** e
validar os registros. A restauração sobre um ambiente compartilhado exige um
procedimento de recuperação separado, considerando gravações posteriores;
não executar `pg_restore --clean` diretamente no projeto em uso.

## Revisão e validação

Foram revisados os cinco SQLs, suas dependências, constraints, triggers,
privilégios e políticas. Não foi identificado impedimento para aplicá-los ao
estado observado do banco remoto. A condição de remoção da tabela legada foi
verificada explicitamente. O mecanismo de execução rejeitou histórico divergente,
mudanças nos dados desde o backup e alterações nos SQLs após o ensaio.

A suíte PostgreSQL sobre a cópia restaurada teve **49 testes aprovados**:

- Turmas, versões e leitura de compartilhamentos.
- Moderação e controle de papéis.
- Matriz de acesso entre usuários e permissões de clientes.
- Revisão particular, confirmação e concorrência.
- Preparação e proteção do texto autorizado.

Os dez pré-requisitos do worker passaram tanto no ensaio quanto no banco remoto,
inclusive em nova conexão após o commit: migração, RLS, privilégios do cliente,
políticas do dono, privilégios da revisão, trigger de autoria, versões canônicas,
bucket privado, políticas de Storage e proteção do snapshot autorizado.

Achado de revisão **MEDIUM**, sem bloqueio para o consumidor atual:
`supabase/migrations/20261109185725_cria_fila_processamento_ia.sql:36`.
A tabela `fila_processamento_ia`, adicionada pela S7-B02,
não é o mecanismo consumido pelo worker atual, que usa lease em `planos_ensino`.
Sua política de consulta usa `professor_id`; precisa ser alinhada com o contrato
de propriedade por `user_id` antes de expor o acompanhamento dos planos
particulares por esse caminho. Isso não bloqueou o fluxo atual, que não usa
essa tabela como consumidor ou endpoint de status.

Recomendação da revisão: **Changes are acceptable with the noted follow-ups.**
As verificações apoiam RNF02/RNF04 e o contrato S7; não comprovam a homologação
integral da Release 2. O acompanhamento da fila paralela é a pendência técnica
identificada, além das etapas operacionais de publicação descritas abaixo.

## Configuração Render e Vercel

O [roteiro de homologação da S7-B02](s7-b02-homologacao.md) reúne as evidências
posteriores e os passos para testar Google Calendar, SMTP e retomada dos jobs.

Os modelos sem segredos estão em `deploy/render.env.example` e
`deploy/vercel.env.example`; comandos e procedimentos em `deploy/README.md`.
Foram preparados também arquivos privados em
`.supabase/cloud-integration-20261110/render.env` e `vercel.env`. O arquivo do
Render contém a conexão PostgreSQL funcional com TLS e a chave Gemini obtida do
ambiente do Windows. Campos que dependem dos painéis dos provedores permanecem
vazios e identificados no guia; não importar os arquivos incompletos sem preenchê-los.

Na opção com API externa, as variáveis de servidor pertencem ao Render. O build
do frontend usa `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` e `VITE_API_URL`.
A função de busca da Vercel também usa as duas variáveis públicas do Supabase.
Na configuração com múltiplos serviços, `VITE_API_URL` pode ficar vazia para
usar a API no mesmo domínio. O [plano de implantação](implantacao.md) detalha
essa configuração.

Pendências identificadas durante a operação de 10/11/2026:

1. Obter a chave pública do projeto e configurar Render/Vercel. As chaves públicas
   locais testadas foram recusadas com HTTP 401 pelo endpoint Auth remoto.
2. Configurar a chave `service_role` legada para o cliente Storage atual no Render.
   Nenhuma chave de serviço foi encontrada nos acessos disponíveis.
3. Informar os domínios reais da API Render e da SPA Vercel, preenchendo
   `VITE_API_URL`, `CORS_ORIGINS` e os retornos de Auth/Google OAuth.
4. Publicar API e frontend e validar a jornada HTTP com contas sintéticas.
5. Resolver hospedagem/custo do worker e a aprovação S7-B02 de termos e
   elegibilidade. As três flags de ativação permanecem em `false`.

Não havia token do Render ou da Vercel, nem sessão disponível do painel Supabase
para configurar esses serviços naquela operação. A implantação integrada é
acompanhada no [PR #113](https://github.com/unb-mds/2026-2-AgendaUnB/pull/113).
Instâncias Render Background
Worker não têm plano Free, conforme a
[documentação oficial](https://render.com/docs/free). Nenhum serviço pago foi
criado e nenhuma chamada Gemini foi feita nesta atividade.
