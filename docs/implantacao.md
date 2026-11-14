# Plano de hospedagem e CI/CD

## Operação da S7-B06

Em 14/11/2026, por decisão do PO de manter ambiente único nesta fase (sem
serviços ou projetos duplicados entre homologação e produção por prazo e
orçamento), [agendaunb.com.br](https://agendaunb.com.br) e
[2026-2-agendaunb-agenda-un-b.vercel.app](https://2026-2-agendaunb-agenda-un-b.vercel.app)
servem o frontend Vite na Vercel (o endereço legado `agendaunb.vercel.app`
retorna `DEPLOYMENT_NOT_FOUND`). O domínio `www` redireciona para o domínio
principal. O bundle aponta para a
[API no Render](https://agenda-unb-api-homolog.onrender.com/health)
(`agenda-unb-api-homolog`) e para o projeto Supabase `pzniltzdhyuzzdqbppjw`
(`agenda-unb-homolog`), com as 31 migrações versionadas aplicadas,
sincronização do catálogo `2026.2` executada e supressão de `uvicorn.access`
quando `APP_ENV != "local"`.

| Componente | Configuração ativa |
| --- | --- |
| SPA | Vercel, raiz `frontend` (e configuração equivalente na raiz em [`vercel.json`](../vercel.json)), Vite, `npm ci`, `npm run build`, saída `dist`. As rotas `/api/search`, `/sitemap.xml`, `/evento/:id` e `/auth/retorno` têm rewrites dedicados e ficam preservadas no fallback. |
| API | FastAPI em Python 3.11 no Render (`agenda-unb-api-homolog`). Usar HTTPS direto para `/api/v1`, inclusive no upload. O Blueprint em [`render.yaml`](../render.yaml) reflete o serviço único Free com publicação manual. |
| Auth, dados e Storage | Projeto Supabase único `pzniltzdhyuzzdqbppjw` (`agenda-unb-homolog`), compartilhado entre API, frontend e jobs, com 31 migrações aplicadas até `20261113212429` e conexão PostgreSQL via TLS (`sslmode=require`). |
| Worker, coletor e catálogo | GitHub Actions com segredos no environment `production-jobs` e disparo manual/agendado por job (`worker`, `collector` e `catalog` para `python -m src.modules.classes.sync --period 2026.2`), validando a operação de custo zero da [#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68). |

O PDF vai diretamente do navegador para o Render com Bearer do Supabase e
multipart. O limite é 10 MiB (10.485.760 bytes), com espaço adicional para o
envelope multipart. A API prepara o texto privado e descarta o PDF original.
A revisão e a autorização do texto continuam necessárias para iniciar
processamento por IA. A Vercel limita o payload de Functions a 4,5 MB.
[Limites da Vercel](https://vercel.com/docs/functions/limitations#request-body-size).

### Configurar o ambiente único

| Local | Variáveis e configuração |
| --- | --- |
| Vercel | `VITE_API_URL` com `https://agenda-unb-api-homolog.onrender.com/api/v1`, `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY` do projeto `pzniltzdhyuzzdqbppjw` (chave legada anon também aceita). |
| Previews Vercel | Como o projeto opera com ambiente único por decisão do PO, habilitar `VERCEL_ENV` apenas quando houver projeto/origem de produção distintos; caso contrário, `deploymentConfig.js` valida que `VITE_API_URL` seja HTTPS terminado em `/api/v1` e bloqueia variáveis `VITE_*` não listadas. |
| Render | `APP_ENV=production` (com `uvicorn.access` desativado fora de `local`), `DATABASE_URL` com TLS, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `GOOGLE_CALENDAR_REDIRECT_URI=https://agenda-unb-api-homolog.onrender.com/api/v1/me/google-calendar/callback`, `GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI=https://agendaunb.com.br/eventos?aba=meus` e `CORS_ORIGINS=https://agendaunb.com.br,https://2026-2-agendaunb-agenda-un-b.vercel.app`. |
| Supabase Auth | Definir `https://agendaunb.com.br` como Site URL e incluir `https://agendaunb.com.br/?auth=login`, `https://agendaunb.com.br/auth/retorno`, `https://agendaunb.com.br/eventos`, `https://2026-2-agendaunb-agenda-un-b.vercel.app/?auth=login` e `https://2026-2-agendaunb-agenda-un-b.vercel.app/auth/retorno` em Redirect URLs. |

Manter chaves de serviço, Gemini, SMTP, OAuth e criptografia nos serviços
servidores que as usam. O bundle público recebe apenas os valores acima.
Manter `SYLLABUS_PROVIDER_TERMS_READY` desativado até a validação da #68.

### Google OAuth

Para **login**, registrar `https://agendaunb.com.br` e
`https://2026-2-agendaunb-agenda-un-b.vercel.app` em Origens JavaScript
autorizadas do cliente Web Agenda UnB. O URI de retorno do cliente de login é
`https://pzniltzdhyuzzdqbppjw.supabase.co/auth/v1/callback` para o projeto atual.
Quando o projeto de produção for separado, registrar o callback dele no
respectivo cliente Web. Atualizar o branding com a home, a
[política de privacidade](https://agendaunb.com.br/privacidade.html) e os
[termos de uso](https://agendaunb.com.br/termos.html) do domínio principal após
verificar a propriedade. [Google Auth Platform](https://console.cloud.google.com/auth/clients?project=agendaunb).

Para **Calendar**, integrar [#110](https://github.com/unb-mds/2026-2-AgendaUnB/pull/110)
e aplicar a migration `20261111150000_s7_f04_auth_calendar_connection.sql`
antes do deploy da API que contém o callback. Em cada ambiente:

1. Habilitar a Google Calendar API e configurar o cliente e o consentimento
   para o escopo `https://www.googleapis.com/auth/calendar.app.created`.
2. Cadastrar `https://<host-da-api>/api/v1/me/google-calendar/callback` no Google
   e usar o mesmo valor em `GOOGLE_CALENDAR_REDIRECT_URI`. Usar os hosts
   definitivos de produção e teste, cada um vinculado ao ambiente correspondente.
3. No Render, cadastrar `GOOGLE_CALENDAR_CLIENT_ID`,
   `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_TOKEN_ENCRYPTION_KEY` e
   `GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI` para a rota de configurações da SPA
   publicada pela [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82).
4. Com conta sintética do ambiente, validar consentimento, retorno, persistência
   da conexão, renovação após expiração e desconexão. Conferir o estado da
   verificação Google, inclusive restrições a contas de teste.

### Publicação, jobs e recuperação

1. Revisar o PR e exigir os checks de frontend, backend e banco aplicáveis a
   `main`. Registrar o SHA em homologação. Conferir o histórico local/remoto
   com `supabase migration list` e revisar `supabase db push --dry-run` para
   cada projeto alvo. Aplicar migrations de forma controlada, primeiro em
   homologação, e repetir os testes antes de promover a mesma versão.
2. Depois da migração compatível, implantar o SHA revisado no Render, conferir
   `/health`, uma consulta ao banco via API e o preflight. Na Vercel, preparar
   um deploy de produção com as variáveis de produção, verificar as rotas e
   promover o deploy validado. Registrar os IDs e os SHAs dos dois serviços.
3. No GitHub, restringir `production-jobs` a `main` e configurar
   `DATABASE_URL` com TLS. Após integrar o coletor e sua migration da #75,
   habilitar `PRODUCTION_EVENT_COLLECTION_ENABLED` e executar `collector`
   manualmente antes de contar com a execução diária às 07h27 de Brasília.
   Acompanhar contagens, falhas e estado da coleta persistido no Supabase.
4. Após a prova da #68, configurar `GEMINI_API_KEY`,
   `SYLLABUS_PRIVACY_READY` e `SYLLABUS_PROVIDER_TERMS_READY` no environment de
   jobs. Habilitar `PRODUCTION_SYLLABUS_WORKER_ENABLED` somente depois de
   demonstrar retomada da fila e medir o tempo até o resultado. A agenda
   configurada processa até um item por execução, a cada 30 minutos, e pode
   atrasar. Serve para prova de execução e persistência, com capacidade e
   latência de produção ainda por validar. Lembretes dependem da #81.
5. Em incidente, desativar os jobs afetados e selecionar os deploys anteriores
   da API e da SPA compatíveis com o schema aplicado. Conferir os IDs,
   restaurar o deploy da API no Render e o da SPA na Vercel, repetir consultas,
   Auth e preflight, e só então retomar os jobs. Preferir correção incremental
   do schema se a aplicação anterior for incompatível com a migration.
   Ensaiar primeiro em homologação e registrar o tempo e o resultado.

O Render Free pode suspender a API após 15 minutos sem tráfego e compartilha
750 horas mensais por workspace. O sistema de arquivos é efêmero. Render Cron
Jobs têm mínimo de US$ 1 por serviço por mês e workers dedicados não têm
instância Free. Conferir o consumo do workspace e as cotas dos provedores
antes de habilitar os jobs. [Render Free](https://render.com/docs/free) ·
[Render Cron Jobs](https://render.com/docs/cronjobs#compute-plans-and-billing) ·
[Agendamento do GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Conferir logs de build e deploy na Vercel, eventos da API no Render, histórico
do GitHub Actions e estado dos jobs no Supabase. Correlacionar pelo horário,
SHA, status e código de erro. Os access logs do Uvicorn ficam desativados para
evitar o registro de URLs completas. Conferir com dados sintéticos que os
logs dos provedores também omitem tokens, credenciais e conteúdo acadêmico.

### Evidências de 12/11/2026

| Cenário | Resultado observado |
| --- | --- |
| HTTPS e acesso externo | `/eventos` respondeu 200 com a SPA pelo conector Vercel e por HTTP direto. As páginas legais responderam 200 no domínio principal. |
| API e CORS | O Render respondeu 200 JSON em `/health` e `/api/v1/events?limit=1`. As origens dos dois domínios oficiais foram aceitas; uma origem de preview não cadastrada recebeu 400 sem autorização CORS. Catálogo e planos retornaram 401 sem sessão. |
| Credenciais públicas | O bundle publicado tem uma chave publishable e nenhum valor no formato de chave `sb_secret_`. O build e os testes locais bloquearam os exemplos de configurações impróprias. |
| Login Google | O Supabase redirecionou ao Google com o callback esperado ao solicitar retorno para ambos os domínios. Falta completar a sessão no domínio novo e conferir a allowlist do Supabase e o branding no painel. |
| Calendar | O endpoint de conexão da versão publicada retorna 404. Conexão e renovação dependem da publicação da #110 e de configuração em cada ambiente. |
| Upload de 10 MiB | A API Render recebeu 10.486.132 bytes de multipart e respondeu 401 sem sessão. Com Auth e banco Supabase locais, o PDF sintético de 10 MiB foi aceito, a autorização gerou candidatos com provedor simulado e a revisão importou um evento. O PDF original não ficou no Storage. Falta repetir com sessão no Render. |
| Build, testes e migrations | Build Vite, 25 testes de frontend, 9 testes Playwright e 228 testes de backend passaram em ambiente local. Duas provas do backend ficaram ignoradas. A imagem Python 3.11 respondeu em `/health`; 28 migrations foram aplicadas do zero no Supabase descartável e o lint passou. |
| Rollback | No mesmo schema local, API candidata → `2a92144` → candidata respondeu 200 em `/health` e na consulta de eventos nas três etapas. Falta ensaiar rollback do frontend e da API na hospedagem. |
| Aceite integrado | Faltam SMTP com destinatário externo, jornadas com sessão no domínio publicado, execução dos jobs hospedados, revisão de logs dos provedores e revisão humana. |

## Plano original e histórico

O [ADR-002](arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes.md) registra a proposta de separação da hospedagem e dos ambientes. Este plano detalha a configuração, a publicação e a recuperação.

O plano abaixo registra a proposta de **24/10/2026**, com referência no commit `e0ecf46`. A seção de operação acima documenta a configuração da S7-B06 e as verificações mais recentes.

| Componente | Proposta | Configuração prevista |
| --- | --- | --- |
| Frontend | Vercel (multi-service ou projeto por ambiente) | Raiz `frontend`, framework `vite`, build `npm run build`, saída `dist`; fallback SPA via `rewrites` |
| Backend | Vercel Services (FastAPI Serverless) ou Render Web Service | Raiz `backend`, framework `fastapi` (`src/main.py`), rotas em `/api/(.*)` e `/health`; ou Render Python 3.11 com `uvicorn src.main:app` |
| Dados, Auth e Storage | Supabase gerenciado | Um projeto de homologação e outro de produção, com migrações SQL versionadas |
| Documentação | GitHub Pages | Manter o workflow MkDocs existente, independente da aplicação |

A versão 3.11 acima é uma proposta de implantação, não a versão observada no backend local: em 08/11/2026, `backend/venv/Scripts/python.exe --version` retornou 3.14.4. Validar a compatibilidade antes de fixar o runtime hospedado.

A proposta utiliza serviços gerenciados para reduzir manutenção operacional. O runtime Python dispensa o Dockerfile vazio; não executar servidor Vite de desenvolvimento nem Uvicorn com `--reload` em hospedagem. Não houve contratação, criação de contas ou deploy nesta entrega.

Fontes oficiais consultadas para a proposta: [Vite na Vercel](https://vercel.com/docs/frameworks/frontend/vite), [FastAPI no Render](https://render.com/docs/deploy-fastapi), [ambientes Supabase](https://supabase.com/docs/guides/deployment/managing-environments) e [limitações gratuitas do Render](https://render.com/docs/free). O Render gratuito suspende serviço após 15 minutos de inatividade e o retorno pode levar cerca de um minuto. Não pressupor disponibilidade contínua gratuita; confirmar limites e orçamento antes da implantação.

## Ambientes e configuração

### Login na Vercel e Supabase Auth

O frontend usa `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY`
(`sb_publishable_...`). `VITE_SUPABASE_ANON_KEY` continua aceito como alternativa
legada, somente com JWT de papel `anon`. O build rejeita chaves `sb_secret_...`
ou JWT `service_role` em qualquer variável `VITE_`, inclusive uma variável
legada que não seja mais utilizada. Nunca incluir credenciais privadas nesse prefixo.

Se aparecer `Forbidden use of secret API key in browser`, substituir a chave
na Vercel nos ambientes afetados e gerar um novo deploy: Vite incorpora os valores
durante o build. Revogar/rotacionar a chave secreta que foi publicada, atualizando
primeiro os serviços privados que dependem dela. A chave pública fica em
Supabase > Settings > API Keys.

No Supabase hospedado, configurar Auth > URL Configuration com a URL real do
site e permitir o retorno exato `https://<dominio>/?auth=login`. Configurar
separadamente os domínios de homologação e produção. `supabase/config.toml`
configura o ambiente local; alterá-lo não habilita provedores no projeto remoto.

Em Auth > Sign In / Providers, manter Email habilitado e habilitar Google com
o Client ID e Client Secret do cliente OAuth Web do Google Cloud. No Google,
cadastrar a origem HTTPS do site e o callback fornecido pelo Supabase:
`https://<project-ref>.supabase.co/auth/v1/callback`. Se o aplicativo Google
estiver em teste, cadastrar os usuários de teste autorizados.

Estudantes e professores entram pelo mesmo formulário de e-mail e senha.
O cadastro docente exige `@unb.br` no frontend e no trigger do banco;
`@aluno.unb.br` não concede papel docente. Google cria novos perfis como
`student` e preserva o papel de contas existentes. Atribuições administrativas
continuam no painel protegido. Com confirmação de e-mail habilitada, o cadastro
sem sessão mostra a orientação para confirmar antes de entrar, sem anunciar
que o usuário já está autenticado.

Verificação de 11/11/2026: o projeto `agenda-unb-homolog` permitia Email e
cadastro, exigia confirmação e tinha Google desativado. Os testes de interface
substituem o provedor externo; não comprovam entrega de e-mail nem consentimento
real do Google. Esses dois fluxos devem ser homologados após a configuração remota.

Referências: [chaves Supabase](https://supabase.com/docs/guides/api/api-keys) e
[Google OAuth](https://supabase.com/docs/guides/auth/social-login/auth-google).

### Processo de extração de planos (S6-B01)

Além da API, provisionar processo independente com comando, na pasta `backend`,
`python -m src.modules.syllabus.worker`. Deve usar o mesmo banco e Storage privado
da API e reiniciar após interrupções. O ciclo de requisição HTTP não executa IA.
Configurar `GEMINI_API_KEY` como segredo do servidor, nunca no frontend; demais
limites, preços e comandos estão em [Processamento de planos](processamento-planos.md).

Aplicar #40, S6-D01, `20261109110000_fila_processamento_planos.sql` e
`20261109113000_privacidade_e_revisao_planos.sql` (S6-D02).
Manter `SYLLABUS_WORKER_ENABLED=false` e `SYLLABUS_PRIVACY_READY=false` até
implantar/verificar as políticas de S6-D02 no PostgreSQL com os papéis reais.
Somente então habilitar os dois parâmetros no ambiente correspondente. A avaliação
sintética com Gemini não homologa privacidade, Storage remoto ou fila em produção.
Esta entrega não provisiona serviço nem aplica migrações remotas.
O worker também verifica pré-requisitos nos catálogos do banco e recusa configuração
incompleta, mesmo com as flags ativas. Consultar o [guia S6-D02](privacidade-planos.md)
para conferir o banco local antes de ativar o processo.

| Ambiente | Aplicação e dados | Uso e publicação |
| --- | --- | --- |
| Local | Vite/FastAPI + Supabase CLI/Docker | Desenvolvimento e testes; dados descartáveis |
| Homologação | Vercel + Render + projeto Supabase exclusivo | Dados fictícios e contas de teste; recebe `main` após validações |
| Produção | Projetos/serviços separados dos de homologação | Promoção manual do commit homologado, após aprovação do responsável pela release |

URLs, IDs dos projetos, região e responsáveis nominais serão preenchidos quando os recursos forem provisionados. Usar HTTPS público e regiões compatíveis entre API e banco. Não compartilhar banco, usuários, buckets ou segredos entre homologação e produção. Previews de PR não devem receber credenciais de produção.

### Variáveis

| Variável/configuração | Destino | Tratamento |
| --- | --- | --- |
| `VITE_API_URL` | Build Vercel | Pública; URL HTTPS da API **incluindo `/api/v1`**; ausente de `.env.example` atualmente |
| `VITE_SUPABASE_URL` | Build e função de busca Vercel | Pública; URL do projeto do ambiente |
| `VITE_SUPABASE_ANON_KEY` | Build e função de busca Vercel | Chave pública anon do ambiente; segurança depende de Auth/RLS |
| `DATABASE_URL` | Runtime Render | Segredo; conexão SQLAlchemy `postgresql+psycopg://...`, credenciais próprias do ambiente e TLS |
| `SUPABASE_URL` | Runtime Render | URL do mesmo projeto usado pelo frontend |
| `SUPABASE_ANON_KEY` | Runtime Render | Chave anon usada na validação do token pelo Auth |
| `CORS_ORIGINS` | Runtime Render | Origens exatas da SPA, separadas por vírgula, sem caminho; evitar curingas |
| `PORT` | Runtime Render | Fornecida pelo provedor; usada pelo comando de início |
| `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID` / `SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET` | Supabase Auth | Cliente de login. Em ambiente hospedado, configure o provedor diretamente no Supabase. |
| `GOOGLE_CALENDAR_CLIENT_ID` / `GOOGLE_CALENDAR_CLIENT_SECRET` | Runtime da API | Cliente web do projeto Google Cloud dedicado ao Calendar. |
| `GOOGLE_CALENDAR_REDIRECT_URI` | Runtime da API | Callback HTTPS exato da API com caminho `/api/v1/me/google-calendar/callback`. |
| `GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI` | Runtime da API | URL fixa da SPA, por exemplo `https://agendaunb.com.br/eventos?aba=meus`. |
| `GOOGLE_TOKEN_ENCRYPTION_KEY` | Runtime da API | Chave Fernet exclusiva e persistente do ambiente para criptografar as credenciais do Calendar. |
| `TEST_SUPABASE_DB_URL` | Job de teste | Somente conexão do Supabase local descartável; testes rejeitam host remoto |
| Tokens Vercel/Render/Supabase e senha de migração | GitHub Environments/Secrets | Segredos exclusivos da automação; provisionar somente na implementação do pipeline |

O Vite lê o ambiente na raiz do repositório (`envDir: '..'`) e incorpora `VITE_*` no build. Alterar esses valores exige novo build. Não incluir senha PostgreSQL, chave de serviço ou tokens de deploy em variáveis `VITE_*`, exemplos ou logs. O build precisa das dependências de desenvolvimento: o SDK Supabase está declarado nessa categoria no estado atual.

Configurar a conexão PostgreSQL usando a opção oferecida pelo projeto Supabase que seja alcançável pelo Render, preferindo pooler em modo de sessão quando necessário por conectividade. Confirmar TLS, driver psycopg e limites de conexões antes da homologação. Não afirmar que RLS protege conexões administrativas: o backend também deve aplicar suas verificações de usuário/papel.

### SPA, CORS e configuração Vercel

Tanto [`frontend/vercel.json`](../frontend/vercel.json) (usado quando o Root Directory é `frontend`) quanto [`vercel.json`](../vercel.json) na raiz configuram exclusivamente o frontend Vite (`framework: "vite"`, saída `dist` / `frontend/dist`), preservando `/api/search` (`kind=sitemap` e `kind=event`), `/auth/retorno` -> `/app.html`, `/eventos` -> `/eventos.html` e rotas profundas em `/app.html`.

O [roteamento do frontend](../frontend/vercel.json) gera títulos, descrições e URLs canônicas no HTML da home e da lista de eventos durante o build. As rotas da SPA, como `/admin` e `/plano-de-ensino`, continuam aceitando acesso direto e recarga.

A função [de busca](../frontend/api/search.js) responde a `/sitemap.xml` e `/evento/<id>`. Configure a URL e a chave pública do Supabase do mesmo ambiente no build e na função. As leituras passam pela RLS anônima e selecionam apenas eventos aprovados. A CDN pode guardar respostas públicas por cinco minutos. Teste o sitemap, um evento aprovado e um ID inexistente após a publicação. Após o deploy, envie o sitemap e solicite indexação no Search Console.

A SPA consome a API no Render diretamente por HTTPS através de `VITE_API_URL` (exigida no build em `frontend/src/lib/deploymentConfig.js`, terminada em `/api/v1`), inclusive no upload de 10 MiB, com `CORS_ORIGINS` restrito às origens explícitas da Vercel no Render.

> [!WARNING]
> **Atenção ao limite de upload (4,5 MB nas Vercel Functions):**
> O fluxo atual de upload de planos de ensino em `/api/v1/syllabus/upload` suporta arquivos de até 10 MB no FastAPI. Contudo, o limite de payload de requisições nas Vercel Serverless Functions é de 4,5 MB. Arquivos maiores que esse limite serão rejeitados com HTTP 413 pela camada de borda da Vercel antes de alcançar o FastAPI.
> Caso uploads entre 4,5 MB e 10 MB devam ser suportados sem falhas:
> 1. Adotar upload direto do frontend para o Supabase Storage via client SDK com RLS ou pre-signed URLs (enviando ao FastAPI apenas metadados/referência); ou
> 2. Manter a execução do backend como Web Service dedicado (ex: Render/container) para as rotas com transferências volumosas.

### Autenticação e Google Agenda (S7-F04)

1. No Supabase do ambiente, configure a Site URL da SPA e permita a URL exata `/auth/retorno` na origem correspondente. Habilite a confirmação de e-mail, mantenha pelo menos 8 caracteres para a senha e use intervalo mínimo de 60 segundos para novo envio.
2. Configure o SMTP de homologação e copie para **Confirm signup** e **Reset password** os templates [confirmation.html](../supabase/templates/confirmation.html) e [recovery.html](../supabase/templates/recovery.html). Os links carregam o hash no fragmento e exigem uma ação na página para consumi-lo. Desative o rastreamento de cliques nos e-mails de autenticação.
3. Para login com Google, habilite o provedor no Supabase e cadastre no Google Cloud a URL de callback fornecida pelo Supabase. O login retorna para `/auth/retorno` e troca o código via PKCE.
4. Use um projeto Google Cloud separado para o Calendar. O Google revoga permissões no nível do projeto, inclusive para outros clientes do mesmo projeto. Habilite a Calendar API, configure o consentimento para `https://www.googleapis.com/auth/calendar.app.created` e crie um cliente web com o callback de `GOOGLE_CALENDAR_REDIRECT_URI`. Configure as variáveis de Calendar e a chave Fernet na API do ambiente. [Revogação OAuth no Google](https://developers.google.com/identity/protocols/oauth2/web-server#tokenrevoke)
5. Aplique as migrações no ambiente de homologação e publique o mesmo commit da API e do frontend. No modo **Teste**, use uma conta autorizada na lista de testadores. A liberação pública segue as condições de consentimento e verificação da [#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68).
6. Valide login e logout por senha e Google. Em **Meus Eventos**, teste conexão por ambos os tipos de sessão, recusa, e-mail divergente, exportação de evento sintético, renovação, nova conexão e revogação. Após desconectar, confirme que o login segue disponível e que a agenda remota permanece. Confira os logs da API, do Supabase e da hospedagem em busca de senhas, códigos e tokens.
7. Quando o SMTP da #68 estiver homologado, registre cadastro e confirmação em caixa externa, reenvio após o intervalo, link expirado e reutilizado e recuperação real. Anexe à #74 o PR, o commit implantado, os resultados de cada cenário e a revisão humana dos contratos, permissões e dados.

| Cenário da S7-F04 | Evidência local | Evidência de homologação |
| --- | --- | --- |
| Cadastro e recuperação por senha | Supabase local com Mailpit confirmou cadastro sem sessão, bloqueio de login antes da confirmação, consumo único do link, troca de senha e login/logout. Playwright simulou reenvio, expiração e reuso. | Entrega e consumo de links em caixa externa via SMTP da #68. |
| Confirmação e papéis | Testes da API e do PostgreSQL verificaram o bloqueio sem confirmação e as restrições de papel. | Registrar o resultado na versão implantada. |
| Login Google e autorização do Calendar | Playwright e pytest cobriram retorno, recusa, divergência de e-mail, expiração, renovação, nova autorização, desconexão e recuperação do destino. | Testar no Google com o cliente Calendar da #68, em sessão Google e em sessão por senha, e conferir os logs publicados. |

A configuração local do Supabase inclui os templates e envia ao Mailpit. Mantenha separadas as origens de homologação e produção.

## Fluxo de CI/CD proposto

O workflow `.github/workflows/supabase-ci.yml` valida o banco em PRs e pushes
na `main` que alteram `supabase/**`, `backend/**` ou o próprio workflow, além de
permitir execução manual. Ele inicia o Supabase local com migrations e seed,
reprova erros de lint e executa `backend/tests/test_*database.py` com Python 3.11.
Os testes usam uma cópia do banco recém-inicializado (schema e seed) em `agenda_catalog_ci`, banco local
descartável necessário para o teste de publicação que faz commits. A porta vem
de `supabase/config.toml`; nenhuma credencial de produção é necessária. Testes
pgTAP só executam quando há arquivos SQL em `supabase/tests`. O stack é encerrado
mesmo em caso de falha. A execução no GitHub Actions ainda precisa ser confirmada.

O restante do fluxo abaixo continua proposto; este workflow não publica a aplicação.
O workflow de documentação continua independente.

1. **PR:** instalar dependências; executar pytest com SQLite, testes de calendário, build frontend e MkDocs. Subir Supabase local descartável, aplicar migrações/seed e executar os testes PostgreSQL com `TEST_SUPABASE_DB_URL` local. Falha bloqueia promoção; teste ignorado não equivale a aprovação de RLS.
2. **Merge em `main`:** repetir as verificações do commit final e publicar homologação, com exclusão mútua por ambiente para impedir migrações/deploys simultâneos. Somente jobs com sucesso liberam a sequência de publicação.
3. **Banco:** conferir projeto de destino e migrações pendentes; aplicar migrações versionadas antes do código dependente. Usar Supabase CLI autenticada com alvo explícito e `db push` após revisão. Não executar `db reset` nem seed demonstrativo em banco persistente.
4. **Backend:** publicar exatamente o SHA validado. Verificar `/health` e uma leitura real de eventos: `/health` sozinho não testa banco/Auth.
5. **Frontend:** gerar build do mesmo SHA com variáveis do ambiente e publicar. Executar os testes de fumaça abaixo.
6. **Produção:** acionamento manual informa o SHA homologado e exige aprovação do responsável pela release. Repetir banco → backend → frontend → fumaça com configuração de produção. Como `VITE_*` muda por ambiente, usar o mesmo código-fonte, não reutilizar cegamente o bundle de homologação.

Desabilitar deploy automático independente dos provedores quando o workflow assumir a publicação; do contrário, um push pode publicar código antes das migrações ou dos testes. Preservar o SHA e o resultado de cada etapa no registro de release. Congelar versões das ferramentas/dependências em tarefa futura: as dependências Python atuais não são fixadas, portanto o mesmo SHA ainda não garante build reproduzível.

### Recuperação e acompanhamento

- Exigir migrações compatíveis com a versão anterior durante a transição; alterações destrutivas precisam de plano próprio antes da promoção.
- Se migração falhar, interromper a publicação. Se API/SPA falhar, restaurar a versão anterior conhecida nos provedores, conferindo compatibilidade com o schema vigente.
- Rollback de código não desfaz migração. Para banco, priorizar migração corretiva; restauração só após avaliar perda de dados, janela e backup disponível. Verificar e ensaiar restauração em ambiente separado antes de depender dela.
- Acompanhar logs da API, erros HTTP, falhas de autenticação e execução de migrações; registrar horário, SHA, resultado e responsável. O monitoramento completo ainda é pendência de implementação.

## Homologação e aceite operacional

Usar duas contas estudantes, uma professora e uma administradora fictícias, criadas pelo fluxo Auth. Não incluir credenciais em documentação. Os testes automatizados de banco devem continuar no Supabase local descartável; verificar o ambiente hospedado por testes de fumaça controlados, sem contornar a restrição de host da suíte.

| Cenário | Resultado esperado |
| --- | --- |
| Login por senha/OAuth e retorno para SPA | Sessão válida no projeto correto, sem redirecionamento para ambiente errado |
| Catálogo anônimo | Apenas aprovados; filtros e paginação funcionam |
| CRUD privado com duas contas | Dono cria/consulta/atualiza/exclui; outra conta recebe 404 para o recurso |
| Papéis e publicação | Estudante não publica diretamente; professor/admin publicam e excluem |
| Salvar/remover público repetidamente | Sem duplicatas; remover vínculo não remove evento; usuários isolados |
| Sugestão aprovada/recusada | Pendência fora do catálogo; recusa exige justificativa; avisos ao autor; segunda decisão recusada |
| Administração | Só admin altera terceiros; cargo divergente detectado; sem autorrebaixamento |
| RLS de notificações e Storage | Usuário não lê/atualiza recursos alheios; bucket permanece privado; isso não implica fluxo de upload implementado |
| Rotas SPA e CORS | Acesso direto funciona; origem autorizada integra API; origem não permitida não recebe liberação CORS |
| Saúde e dependências | `/health` responde e leituras reais/autenticação também funcionam |

Aceitar a implantação apenas com evidências registradas de migrações, builds, testes de fumaça e recuperação preparada. Não marcar como homologado somente porque um deploy terminou.

## Pendências e responsabilidades propostas

| Pendência futura | Papel responsável |
| --- | --- |
| Aprovar arquitetura final (Vercel multi-service vs Render para backend) considerando o limite de 4,5 MB de upload | Time e responsável pela release |
| Validar comportamento de upload de planos de ensino em ambiente hospedado Vercel | Backend e Frontend |
| Provisionar projetos Supabase, Auth, migrações, dados de homologação e recuperação | Banco de dados, com Backend |
| Criar workflows, secrets por ambiente, gates e publicação pelo SHA | Time, com Backend |
| Atualizar este documento com evidências e URLs efetivas | Responsável pela release |

Nenhum desses papéis representa atribuição nominal já aprovada. Mudanças de hospedagem, variáveis, migrações ou pipeline devem atualizar este documento no mesmo PR. Ver [Arquitetura](arquitetura/visao-geral.md), [Contratos](api-specs.md) e [Contribuição](processo/contribuindo.md).

## Transição do desenvolvimento local para o projeto Supabase da equipe

O time informou que Felipe Couto Duque está preparando o projeto Supabase na
nuvem. O desenvolvimento de `feat/geminiapi` e os testes continuam locais enquanto
essa configuração é concluída. Nenhum outro projeto hospedado foi criado e nenhum
projeto remoto foi vinculado ou migrado por esta implementação.

Quando o ambiente estiver disponível, alinhar com Felipe o projeto/ambiente de
destino e o histórico de migrações já aplicado. Revisar e aplicar os SQLs pendentes
em ordem, preservando dados; não copiar/resetar o banco local inteiro na nuvem.
Para planos, o destino precisa incluir #40, S6-D01, a fila `20261109110000` e a
privacidade/revisão `20261109113000`.

Configurar URLs/chaves públicas no frontend e segredos somente no backend/worker
(`DATABASE_URL`, serviço Supabase e Gemini), separados dos de teste. Validar HTTPS,
CORS, Auth/retornos de login, bucket privado e revisão explícita com contas de
homologação antes de habilitar as flags. A aprovação local não equivale à aprovação
do ambiente hospedado. A suíte local foi feita para rejeitar hosts remotos; a
homologação na nuvem deve ter procedimento próprio, com dados sintéticos e o
projeto de destino identificado. Ver o [fluxo HTTP local](privacidade-planos.md#integracao-http-local-de-auth-storage-e-processamento)
e as [variáveis do worker](processamento-planos.md).


### Correção de configuração em produção (11/11/2026)

A variável VITE_SUPABASE_ANON_KEY na Vercel foi substituída por uma chave
publishable do projeto de homologação, nos ambientes production e preview.
O deploy de produção dpl_FMkQ3apCDBWxDG2RJAkSwZP7Je4U republicou o commit
5f2f18ae88b7baafd46b5a21ab385310967e75de de main com a configuração corrigida.
O bundle servido por https://agendaunb.vercel.app contém a chave pública e
não contém valores sb_secret_. Uma requisição com credenciais deliberadamente
inválidas retornou invalid_credentials (HTTP 400), sem o bloqueio de chave secreta.

O Site URL remoto passou de localhost:3000 para https://agendaunb.vercel.app.
Foram autorizados /eventos e /?auth=login nesse domínio e no domínio
2026-2-agendaunb.vercel.app. O provedor Email e a confirmação permanecem ativos.
Google ainda aguarda preenchimento das credenciais no painel e homologação real.
As melhorias de tratamento de erros e confirmação no código local ainda precisam
ser integradas e publicadas; o redeploy acima altera apenas a configuração.


### Novo cliente Google (11/11/2026)

Configurado o projeto Google Cloud agendaunb (722562228185), com cliente
Web Agenda UnB e origem https://agendaunb.vercel.app. O callback autorizado
é https://pzniltzdhyuzzdqbppjw.supabase.co/auth/v1/callback.
Uma nova chave foi gerada com autorização do responsável e cadastrada
exclusivamente no provedor Google do Supabase, sem persistência no código.
O painel confirmou Google Enabled e Successfully updated settings.
O provedor exige e-mail e mantém a verificação de nonce ativa.

O teste no site publicado chegou ao seletor de contas do Google com o novo
client_id e os parâmetros de callback corretos. O consentimento e a troca
do código por sessão ainda precisam de validação com uma conta real.
O app Google permanece Externo / Testando: a publicação está bloqueada pela
configuração de branding. Não há URLs públicas de política de privacidade
e termos no cadastro. Não foram inventados links para esses documentos.


### Validação real do Google OAuth (11/11/2026)

O fluxo foi concluído no site publicado com a conta do projeto: seleção da conta
Google, consentimento limitado a nome/foto/e-mail e retorno à página de eventos
autenticada, com Notificações e Sair da conta disponíveis. Isso valida o callback,
a chave secreta configurada e a criação da sessão pelo Supabase.
O branding e a publicação geral no Google permanecem pendentes por decisão
do responsável; o ambiente Google continua em modo de teste.


### Publicação legal e verificação da marca (11/11/2026)

Deploy de produção dpl_FvAa8JYvqr2Vaj2PjHkKY83K9npT, commit
1a54cc701ced396c3a6c73013df4ba0039ed747b da branch codex/oauth-privacy-publication.
Política e termos acessíveis sem login em https://agendaunb.vercel.app/privacidade.html
e https://agendaunb.vercel.app/termos.html, com links no rodapé e metatag de propriedade.
Os textos vieram da branch feat/s8-d01-privacidade (961f6d1), com responsáveis,
canal e retenção definidos pelo responsável e identificação do autoatendimento
ainda previsto para a Release 2.

Search Console confirmou Propriedade verificada via Tag HTML para
unbagenda@gmail.com. Não remover a metatag google-site-verification.
O Google OAuth foi publicado em produção e a verificação da marca foi iniciada.
A checagem automática ainda não reconheceu a propriedade recém-confirmada e
solicitou expressamente aguardar 24 horas antes de tentar novamente.
Não foi apresentada contestação: a atualização entre os sistemas é pendente real.
Retomar Branding > Informações e resumo > Ver problemas > Corrigi os problemas
após esse intervalo e concluir a nova solicitação. A marca ainda não está aprovada.
