# Plano de hospedagem e CI/CD

## Arquitetura de implantação

A plataforma opera com separação entre SPA estática, API Web em container Docker, banco/autenticação gerenciados e jobs assíncronos em GitHub Actions ([ADR-002](/arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes) e [ADR-007](/arquitetura/adrs/adr-007-migracoes-sql)).

| Camada | Configuração de implantação |
| --- | --- |
| Vercel (Frontend SPA) | Root Directory `frontend`, framework Vite, `npm ci && npm run build`, saída `dist`. `frontend/vercel.json` serve a SPA e a função serverless `/api/search` (`/sitemap.xml` e metadados de `/evento/:id`). |
| Render (API FastAPI) | Blueprint em `render.yaml`: Web Service com `runtime: docker`, raiz `backend`, `backend/Dockerfile` (`python:3.11-slim`, Uvicorn com `--no-access-log --no-server-header`), health check em `/health` e `autoDeployTrigger: "off"`. |
| Supabase Cloud | PostgreSQL, Auth, Storage privado e Cron (`pg_cron`). Utilizar conexão Session Pooler com TLS (`sslmode=require`). |
| GitHub Actions | Workflows `.github/workflows/app-ci.yml`, `supabase-ci.yml`, `docs.yml` e `production-jobs.yml` (worker de planos, coletor da Agenda UnB Notícias e sincronização sob demanda do catálogo de turmas). |

A SPA envia requisições e uploads de planos (PDF até 10 MiB em multipart) diretamente para a API no Render utilizando `Authorization: Bearer <token>`, evitando o limite de payload de 4,5 MB das Vercel Serverless Functions. O backend extrai e sanitiza o texto em memória e descarta o PDF imediatamente ([ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos)).

A instância Free do Render suspende o serviço após 15 minutos sem tráfego, podendo gerar latência de despertar na primeira chamada. E-mails transacionais de autenticação utilizam o SMTP configurado no Supabase Auth (o Render Free bloqueia portas SMTP comuns).

## Configuração de ambiente e autenticação

### Supabase Auth e login Google

1. Em **Auth > URL Configuration**, configure a Site URL de produção e cadastre as URLs de retorno exatas permitidas (`/auth/retorno`, `/?auth=login`, `/eventos`).
2. Em **Auth > Sign In / Providers**, mantenha **Email** ativo com confirmação obrigatória, senha mínima de 8 caracteres (com letras e dígitos, alinhada a `supabase/config.toml`) e intervalo mínimo de 60 segundos para reenvio.
3. Configure o SMTP customizado no Supabase Auth e utilize os templates versionados `supabase/templates/confirmation.html` (**Confirm signup**) e `recovery.html` (**Reset password**), desativando rastreamento de cliques nos e-mails.
4. Para **login com Google**, habilite o provedor no Supabase Auth com Client ID e Client Secret de um cliente OAuth Web no Google Cloud, cadastrando o callback `https://<project-ref>.supabase.co/auth/v1/callback` no Google e as origens oficiais da SPA.
5. Cadastro e autopromoção para `professor` exigem e-mail `@unb.br` confirmado; login via Google cria novas contas como `student` e preserva papéis existentes.

### Google Calendar OAuth e operação

1. **Projeto OAuth dedicado:** utilize um projeto Google Cloud separado do login principal (a revogação de permissões no Google afeta todo o projeto). Habilite a **Google Calendar API** e configure a tela de consentimento com os escopos `openid`, `email` e `https://www.googleapis.com/auth/calendar.app.created` (acesso restrito à agenda secundária **"Agenda UnB"**).
2. **Callbacks:** cadastre `https://<host-da-api>/api/v1/me/google-calendar/callback` no Google Cloud e em `GOOGLE_CALENDAR_REDIRECT_URI`; configure `GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI` apontando para `https://<host-da-spa>/eventos?aba=meus`.
3. **Modo *Testing* vs. publicação:** enquanto o aplicativo OAuth estiver em *Testing*, apenas contas cadastradas na lista de testadores conseguem autorizar o Calendar (limite de 100 usuários de teste). Para liberação ao público geral, conclua a verificação de domínio (preservando a metatag `google-site-verification` usada pelo Search Console), os links públicos para `/privacidade.html` e `/termos.html` e a revisão de marca e escopos no Google Auth Platform.
4. **Regras operacionais de exportação e falhas:**
   - Tokens ficam cifrados com Fernet (`GOOGLE_TOKEN_ENCRYPTION_KEY`, chave estável entre deploys) no servidor; desafios OAuth expiram em 10 minutos. Quando o `access_token` expira, a API renova via `refresh_token`.
   - Ao desconectar em **Meus Eventos** ou revogar em **Configurações**, as credenciais locais são apagadas e a revogação é enviada ao Google.
   - A exportação e reexportação são idempotentes (lotes de até 20 eventos, fuso `America/Sao_Paulo`, duração padrão de 1 hora). Não há sincronização bidirecional: alterações ou exclusões no Agenda UnB após a exportação não modificam nem apagam cópias na agenda **"Agenda UnB"** do Google, e alterações no Google não retornam ao Agenda UnB.
   - Em `429`, timeout após criação, falha parcial do lote ou token revogado (`401`/`403`/`invalid_grant`), a interface preserva os eventos locais, reporta o estado por item e oferece nova tentativa ou exportação complementar em `.ics`.

## Variáveis de ambiente

Nunca inclua credenciais privadas (`DATABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, segredos OAuth ou `GOOGLE_TOKEN_ENCRYPTION_KEY`) em variáveis prefixadas por `VITE_*`, no código-fonte ou em logs. O build do frontend valida em `frontend/src/lib/supabaseConfig.js` e `deploymentConfig.js` a ausência de chaves secretas e o isolamento entre ambientes de preview e produção.

| Variável | Destino | Finalidade e tratamento |
| --- | --- | --- |
| `VITE_API_URL` | Build Vercel | Pública; URL HTTPS da API **incluindo `/api/v1`** |
| `VITE_SUPABASE_URL` | Build e função `/api/search` Vercel | Pública; URL do projeto Supabase do ambiente |
| `VITE_SUPABASE_PUBLISHABLE_KEY` | Build e função `/api/search` Vercel | Chave pública publishable (`sb_publishable_...`; `VITE_SUPABASE_ANON_KEY` aceito como alternativa legada anon) |
| `APP_ENV` | Runtime Render / Jobs | `production` em ambientes hospedados; `local` em desenvolvimento |
| `DATABASE_URL` | Runtime Render / Jobs | Segredo; conexão PostgreSQL `postgresql+psycopg://...` com TLS (`sslmode=require`) |
| `SUPABASE_URL` | Runtime Render | URL do mesmo projeto Supabase usado pelo frontend |
| `SUPABASE_ANON_KEY` | Runtime Render | Chave pública anon usada na validação de sessão |
| `SUPABASE_SERVICE_ROLE_KEY` | Runtime Render | Segredo exclusivo do servidor (operações administrativas de Storage e exclusão de conta) |
| `CORS_ORIGINS` | Runtime Render | Origens HTTPS exatas da SPA separadas por vírgula, sem barra final |
| `PORT` | Runtime Render | Fornecida pelo provedor para o comando `uvicorn` |
| `API_DOCS_ENABLED` | Runtime Render | `false` em homologação e produção (desativa `/docs`, `/redoc` e `/openapi.json`) |
| `TRUSTED_PROXY_HOPS` | Runtime Render | Número de proxies confiáveis quando fora de borda Cloudflare (`CF-Connecting-IP`) |
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_WRITE_PER_MINUTE` | Runtime Render | Limites de requisição por cliente (padrões `240` e `60`) |
| `GEMINI_API_KEY` | Runtime Render / `production-jobs` | Segredo da API Google Gemini |
| `GEMINI_MODEL` | Runtime Render / `production-jobs` | Modelo configurado (padrão `gemini-3.5-flash-lite`) |
| `SYLLABUS_WORKER_ENABLED` | Runtime Render / `production-jobs` | `"true"` para habilitar disparo e execução do worker de planos |
| `SYLLABUS_PRIVACY_READY` | Runtime Render / `production-jobs` | `"true"` após confirmar pré-requisitos de minimização e políticas RLS no banco |
| `SYLLABUS_PROVIDER_TERMS_READY` | Runtime Render / `production-jobs` | `"true"` após validação dos termos do provedor externo de IA |
| `PRODUCTION_SYLLABUS_WORKER_ENABLED` | GitHub Repo/Env Variables (`production-jobs`) | `"true"` para ativar o job agendado `worker` (`13,43 * * * *`) |
| `PRODUCTION_EVENT_COLLECTION_ENABLED` | GitHub Repo/Env Variables (`production-jobs`) | `"true"` para ativar o coletor diário `collector` (`27 10 * * *`) |
| `GOOGLE_CALENDAR_CLIENT_ID` / `GOOGLE_CALENDAR_CLIENT_SECRET` | Runtime Render | Segredos do cliente OAuth Web dedicado ao Google Calendar |
| `GOOGLE_CALENDAR_REDIRECT_URI` | Runtime Render | Callback HTTPS exato `/api/v1/me/google-calendar/callback` |
| `GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI` | Runtime Render | URL da SPA após OAuth (ex.: `https://<dominio>/eventos?aba=meus`) |
| `GOOGLE_TOKEN_ENCRYPTION_KEY` | Runtime Render | Chave Fernet exclusiva e persistente para cifrar tokens OAuth |
| `TEST_SUPABASE_DB_URL` | CI / Local | Conexão exclusiva para Supabase local descartável (`localhost`/`127.0.0.1`) |

## Publicação, jobs e recuperação {#publicacao-jobs-e-recuperacao}

### 1. Pré-implantação, backup e migrations

Como o plano Free do Supabase não disponibiliza *Point-in-Time Recovery* (PITR) automático, realize backup lógico antes de aplicar migrações com alteração de esquema:

```bash
# Backup lógico antes da janela de mudança
pg_dump "$DATABASE_URL" --format=custom --no-owner --no-acl -f "backup-agendaunb-$(date +%Y%m%d-%H%M).dump"

# Conferência do histórico e ensaio antes de aplicar migrações
npx supabase migration list
npx supabase db push --dry-run --include-all
npx supabase db push --include-all
```

Nunca execute `supabase db reset` nem seed demonstrativo contra banco persistente.

### 2. Deploy da API, SPA e configuração dos jobs

1. **Backend (Render):** publique o SHA validado após as migrações. Valide `GET /health` (`200`), `GET /api/v1/events?limit=1` (`200` JSON), cabeçalhos `CORS` para a origem oficial e `GET /api/v1/me/legal-documents` autenticado.
2. **Frontend (Vercel):** publique o mesmo SHA com variáveis de produção/homologação (alterar `VITE_*` exige novo build). Valide recarga direta em `/eventos`, `/plano-de-ensino`, `/configuracoes`, `/auth/retorno`, `/sitemap.xml`, `/evento/<id>`, `/privacidade.html` e `/termos.html`.
3. **Jobs em GitHub Actions (`.github/workflows/production-jobs.yml`):**
   - `worker`: drena até 25 planos por execução (`python -m src.modules.syllabus.worker --drain --max-items 25`) aos minutos 13 e 43 de cada hora.
   - `collector`: coleta eventos da Agenda UnB Notícias diariamente às 07h27 BRT (`27 10 * * *`) ou sob demanda via `workflow_dispatch`.
   - `catalog`: sincroniza o catálogo Followw sob demanda via `workflow_dispatch` (`python -m src.modules.classes.sync --period <AAAA.S>`).
4. **Lembretes (`pg_cron`):** execute `supabase/snippets/habilitar_lembretes.sql` como `postgres` no banco migrado para registrar de forma idempotente o job `agenda-unb-lembretes` (execução a cada 5 minutos). Consulte a verificação manual em [Dados de eventos](/arquitetura/dados-de-eventos#agendador-pg_cron).

### 3. Procedimento de rollback e recuperação

1. **Jobs (`production-jobs`):** desative `PRODUCTION_EVENT_COLLECTION_ENABLED` e `PRODUCTION_SYLLABUS_WORKER_ENABLED` imediatamente se houver falha em lote. Para pausar lembretes em incidente, execute `select cron.unschedule('agenda-unb-lembretes')`.
2. **Aplicação (API e SPA):** no Render e na Vercel, reverta para o deploy anterior validado compatível com o schema vigente do banco.
3. **Banco de dados:** rollback de código não desfaz migrações; priorize migração corretiva incremental. Caso seja indispensável restaurar um snapshot pré-janela após alteração destrutiva:
   ```bash
   pg_restore --clean --if-exists --no-owner --no-acl -d "$DATABASE_URL" backup-agendaunb-YYYYMMDD-HHMM.dump
   ```
   Após a restauração, confira a integridade das tabelas `eventos`, `eventos_pessoais`, `planos_ensino` e `google_calendar_connections` e valide `/health` e consultas reais antes de reativar os jobs.

## Pipelines de CI e checklist de aceite

### Workflows automatizados

- **`.github/workflows/app-ci.yml`:** executa em PRs e pushes (`main`) `npm test`, `npm run build` e `npx playwright test` (Chromium) no frontend, além de `python -m pytest tests -q -ra` (Python 3.11 com SQLite) no backend.
- **`.github/workflows/supabase-ci.yml`:** inicia Supabase local via CLI, executa `supabase db lint --level error --fail-on error`, testes `pgTAP` (quando presentes), `tests/*_database.py`, `tests/test_syllabus_http_integration.py` e `tests/test_catalog_publication_database.py` em cópia isolada.
- **`.github/workflows/docs.yml`:** valida a documentação Mintlify em `docs/` com `npx -y mint validate`, `npx -y mint broken-links --check-redirects` e `npx -y mint a11y`.

### Checklist de verificação de ambiente

- [ ] SHA implantado na Vercel e no Render corresponde ao commit validado nos workflows de CI.
- [ ] `supabase migration list` sem divergências no projeto alvo e variáveis de ambiente conferidas sem segredos em `VITE_*`.
- [ ] `GET /health` e `GET /api/v1/events?limit=1` respondem `200` com TLS válido e cabeçalhos CORS corretos.
- [ ] Login por e-mail/senha (com confirmação via SMTP) e login Google concluídos, incluindo rotas protegidas e páginas `/privacidade.html` e `/termos.html`.
- [ ] Fluxos de eventos salvos, sugestões, moderação, seleção de turmas, envio e confirmação de plano de ensino, conexão/exportação Google Agenda e exclusão de conta verificados com contas sintéticas de teste.
- [ ] Jobs `collector`, `worker` e `agenda-unb-lembretes` ativos e executando sem falhas nos logs.
- [ ] Documentação aprovada com `mint validate`, `mint broken-links --check-redirects` e `mint a11y`.
