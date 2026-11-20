# Plano de hospedagem e CI/CD

## Operação da Release 2

A R2 usa um ambiente hospedado compartilhado. A aprovação das mudanças da release usa Supabase local descartável e contas sintéticas. Confira o SHA e o estado dos serviços antes de publicar.

| Camada | Configuração da R2 |
| --- | --- |
| Vercel | [agendaunb.com.br](https://agendaunb.com.br) e [domínio Vercel](https://2026-2-agendaunb-agenda-un-b.vercel.app). Root Directory `frontend`, Vite, `npm ci`, `npm run build`, saída `dist`. `frontend/vercel.json` serve a SPA e a função de busca de eventos públicos. |
| Render | [agenda-unb-api-homolog](https://agenda-unb-api-homolog.onrender.com/health), plano Free, FastAPI. O serviço ativo foi observado com runtime Python nativo e deploy automático de `main`. O Blueprint versionado define Docker com Python 3.11, `/health` e publicação manual. Coordene a configuração do serviço ativo com a ordem abaixo. |
| Supabase | Projeto `agenda-unb-homolog` (`pzniltzdhyuzzdqbppjw`) para PostgreSQL, Auth e Storage. Use conexão Session Pooler com TLS. |
| Jobs | GitHub Actions em `main` para retomada da fila de planos e coleta de notícias. Sincronização do Followw sob demanda no mesmo workflow. Supabase Cron para lembretes. |

A SPA envia o PDF diretamente ao Render com a sessão Supabase via `Authorization`. O backend aceita até 10 MiB em multipart, extrai e sanitiza o texto e descarta o PDF. O envio autoriza o processamento do texto sanitizado. [Limites de payload da Vercel](https://vercel.com/docs/functions/limitations#request-body-size).

### Configurar o ambiente único

| Local | Variáveis e configuração |
| --- | --- |
| Vercel | `VITE_API_URL=https://agenda-unb-api-homolog.onrender.com/api/v1`, `VITE_SUPABASE_URL` e `VITE_SUPABASE_PUBLISHABLE_KEY` da mesma instância Supabase. A função de busca também usa a URL e a chave pública em runtime. |
| Render | `APP_ENV=production`, `DATABASE_URL` com TLS, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` e `CORS_ORIGINS=https://agendaunb.com.br,https://2026-2-agendaunb-agenda-un-b.vercel.app`. |
| Supabase Auth | Site URL `https://agendaunb.com.br`. Cadastre as URLs exatas de retorno para `/auth/retorno`, `/?auth=login` e `/eventos` nas origens oficiais em uso. Configure SMTP customizado e os templates de confirmação/recuperação no próprio Supabase. |

Previews Vercel precisam de Auth, banco e API separados quando `VERCEL_ENV=preview` estiver disponível para o build. A verificação usa `VITE_DEPLOYMENT_ENV=preview`, `PRODUCTION_SUPABASE_URL` e `PRODUCTION_API_ORIGIN`. Reserve segredos de banco, Storage, Gemini e OAuth aos serviços servidores que os consomem.

### Google OAuth

Para **login**, configure o provedor Google no Supabase Auth, com o callback `https://pzniltzdhyuzzdqbppjw.supabase.co/auth/v1/callback` no Google. Inclua as origens oficiais do frontend no cliente OAuth Web e vincule a tela de consentimento às páginas legais do domínio. [Google OAuth no Supabase](https://supabase.com/docs/guides/auth/social-login/auth-google).

Para **Google Agenda**:

1. Habilite a Google Calendar API no projeto OAuth do Calendar. O fluxo usa `openid`, `email` e `https://www.googleapis.com/auth/calendar.app.created`.
2. Registre `https://agenda-unb-api-homolog.onrender.com/api/v1/me/google-calendar/callback` no Google e em `GOOGLE_CALENDAR_REDIRECT_URI`. O callback recebe `state` e `code` ou `error` e redireciona, sem credenciais na URL final, para `GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI=https://agendaunb.com.br/eventos?aba=meus`. [OAuth para aplicações web](https://developers.google.com/identity/protocols/oauth2/web-server#handlingresponse).
3. Cadastre `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET` e `GOOGLE_TOKEN_ENCRYPTION_KEY` no Render. A chave Fernet deve ser estável para renovar conexões existentes. Use uma conta sintética com o mesmo e-mail verificado nos dois lados e incluída na lista de teste do Google, quando aplicável.

### Publicação, jobs e recuperação

1. Confirme o SHA revisado e o destino com `supabase migration list`. No estado observado em 20/11/2026, o Supabase remoto tinha 35 migrações, incluindo `20261117150000_planos_compartilhamento_e_votos.sql`, e ainda precisava receber `20261117130000_endurecimento_seguranca.sql`. Revise `supabase db push --dry-run --include-all` e aplique `supabase db push --include-all`. O `--include-all` inclui essa migração anterior ainda ausente. Faça backup antes da janela de mudança conforme o [roteiro de entrega](/processo/roteiro-entrega).
2. Publique a API do SHA validado no Render. Confira `/health`, `/api/v1/events?limit=1`, o preflight da origem oficial e `/api/v1/me/legal-documents` com sessão. Na Vercel, publique o mesmo SHA e confira recarga de `/configuracoes`, `/plano-de-ensino`, `/eventos` e `/auth/retorno`, além de `/sitemap.xml` e de um detalhe público.
3. Para liberar a análise no Render, confira `GEMINI_API_KEY`, `SYLLABUS_WORKER_ENABLED`, `SYLLABUS_PRIVACY_READY` e `SYLLABUS_PROVIDER_TERMS_READY`. O Render pode iniciar o subprocesso após a autorização. O job `worker` de `production-jobs` retoma a fila persistente aos minutos 13 e 43 de cada hora, sujeito a atrasos do GitHub. Ele drena até 25 planos por execução, com lease e orçamento. Defina `PRODUCTION_SYLLABUS_WORKER_ENABLED` e as flags de prontidão como variáveis do repositório. Mantenha `DATABASE_URL` e `GEMINI_API_KEY` como segredos do ambiente `production-jobs`. [Variáveis do GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/variables#configuration-variable-precedence).
4. Configure `PRODUCTION_EVENT_COLLECTION_ENABLED` e execute `collector` sob demanda em `main` antes de depender do agendamento diário às 07h27 de Brasília. Execute `catalog` sob demanda para `2026.2`. Ambos usam `DATABASE_URL` com TLS. Registre a contagem e o estado da coleta/publicação, incluindo exceções encaminhadas à moderação.
5. Após aplicar as migrações de lembretes, execute `supabase/snippets/habilitar_lembretes.sql` como `postgres`. Confira o job `agenda-unb-lembretes` no Supabase Cron e valide a entrega e a leitura de uma notificação. [Operação dos lembretes](/arquitetura/dados-de-eventos#agendador).
6. Em incidente, pause os jobs afetados e restaure o deploy da API e da SPA compatível com o schema aplicado. Confira saúde, CORS e Auth antes de retomar. Para o banco, prefira uma migração corretiva. Registre SHAs e IDs de deploy.

A instância Free do Render pode suspender a API após 15 minutos sem tráfego. O SMTP de autenticação sai do Supabase Auth. O Render Free bloqueia portas SMTP comuns. Acompanhe build e erros na Vercel, logs da API no Render, execuções no GitHub Actions e jobs no Supabase. [Limites do Render Free](https://render.com/docs/free).

### Estado verificado em 20/11/2026

| Ambiente | Evidência |
| --- | --- |
| Vercel publicada | `main` em `0239a06`. Home, eventos, retorno de autenticação, sitemap, documentos legais e `/docs` responderam. `/configuracoes` retornou 404 nessa versão. |
| Render publicado | Mesmo SHA. `/health` e `/api/v1/events?limit=1` retornaram 200. A operação de documentos legais retornou 404, pois a API publicada antecede a entrega de privacidade. |
| Supabase hospedado | 35 migrações aplicadas. O projeto redirecionou o login ao Google, sem completar uma sessão nesta verificação. O inventário retornou zero objetos no bucket legado e zero caminhos de PDF persistidos. O Supabase Cron ainda não estava ativado. |
| Branch integrada em ambiente isolado | A migração foi testada a partir do zero e na ordem real do ambiente hospedado. O lint SQL e a conferência do schema passaram. O lembrete agendado executou com sucesso no Supabase local. Build Vercel com Node 26 e container Render Python 3.11 foram verificados. |
| Envio e importação de plano | Com Auth, Storage e PostgreSQL locais, um PDF sintético de 838 bytes gerou dois candidatos em 7,91 s com Gemini real. A primeira importação criou um compromisso e o PDF foi descartado. Um PDF sintético de 10 MiB também passou com provedor simulado. |

`npm audit` e `pip-audit` passaram após a atualização das dependências sinalizadas.

O aceite hospedado depende da publicação do SHA integrado após as migrações. Inclui entrega de e-mail por SMTP, login via Google, conexão e exportação no Google Agenda, importação de plano, execução dos jobs e entrega de lembretes.

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

O protocolo de migrações seguras e as decisões de infraestrutura estão consolidados nas [ADR-002](/arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes) e [ADR-007](/arquitetura/adrs/adr-007-migracoes-sql). Este plano detalha a configuração, a publicação e a recuperação.

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

### Processo de extração de planos

A API registra a autorização e a fila no PostgreSQL. O worker executa em processo independente, verifica o snapshot sanitizado e limita tentativas, tempo e custo. Os requisitos de execução estão nas [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos) e [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia). Faça o teste da jornada completa com PDF sintético e confirme prazo, candidatos, exclusão do original e ausência de texto nos logs.

### Coleta da Agenda UnB Notícias (S7-B05)

O coletor é um processo desacoplado da API, que utiliza `DATABASE_URL` do ambiente e advisory locks (`pg_advisory_xact_lock`) no PostgreSQL para garantir idempotência e impedir concorrência.

#### Formas de Execução e Ativação em Background
1. **GitHub Actions (Ambiente Hospedado):**
   - Configurado no workflow `.github/workflows/production-jobs.yml` através do job `collector`.
   - Execução programada diariamente às 07h27 BRT (`cron: '27 10 * * *'`) e manual via `workflow_dispatch` com input `job: collector`.
   - **Ativação:** defina a variável de repositório `PRODUCTION_EVENT_COLLECTION_ENABLED=true` e configure o segredo `DATABASE_URL` com TLS no ambiente `production-jobs`.
2. **Automação Local via Makefile:**
   - `make events-collect`: executa uma única passagem de coleta localmente.
   - `make events-collect-daemon`: executa o coletor em modo daemon com intervalo padrão.
3. **CLI Direto no Backend:**
   - `python -m src.modules.events.collector`: execução única.
   - `python -m src.modules.events.collector --daemon`: execução contínua em background.
   - `python -m src.modules.events.collector --interval-hours <h>`: execução recorrente com intervalo mínimo de 1 hora.

#### Status de Validação e Evidências
Consulte [Dados de eventos: datas e coleta](/arquitetura/dados-de-eventos) e a [ADR-011](/arquitetura/adrs/adr-011-datas-civis-e-instantes) para a rastreabilidade completa dos critérios de aceite.

| Cenário / Requisito | Validação Realizada (Local / CI) | Acompanhamento na Hospedagem |
| --- | --- | --- |
| Deduplicação por similaridade de título e data | 34 testes em `test_event_collector.py` e 18 em `test_event_collection_database.py` cobrindo limiares ($\ge 0{,}80$ / $0{,}85$ / $0{,}92$), janela $\le 2$ dias, acentos/pontuação e prevenção de falsos positivos com números/edições. | Homologação com dados reais de produção e integração visual da fila de revisão em S8-F02 ([#80](https://github.com/unb-mds/2026-2-AgendaUnB/issues/80)). |
| Marcação de dia inteiro vs `00:00` | Termos explícitos reconhecidos gerando datas civis (`dia_inteiro: True`); horários `00:00` sem indicativo mantidos em revisão (`ambiguo: True`). | Verificação amostral nos eventos extraídos diretamente de `noticias.unb.br`. |
| Procedência visível (RF16) | Contratos públicos em `EventRead` (`source`, `source_url`), API (`test_events_api.py`), cache frontend (`publicEventsCache.test.js`) e UI (`PaginaDeEvento.jsx`, `SecondPage.jsx`). | Inspeção visual no deploy da Vercel após publicação em `main`. |
| Cobertura multicampus | Mapeamento e normalização dos 5 campi da UnB (Darcy Ribeiro, FCTE, FCTS, FUP, FAL). | Conferência dos nomes de campus gravados no banco remoto. |
| Execuções concorrentes e falha da fonte | Advisory lock (`pg_try_advisory_lock(708073)` e lock por item) validado. Falhas de HTTP/timeout preservam dados existentes e registram `status = 'falha'`. | Ativação da variável de repositório `PRODUCTION_EVENT_COLLECTION_ENABLED=true` após merge em `main`. |

### Variáveis

| Variável/configuração | Destino | Tratamento |
| --- | --- | --- |
| `VITE_API_URL` | Build Vercel | Pública; URL HTTPS da API **incluindo `/api/v1`** (exigida em builds Vercel por `frontend/src/lib/deploymentConfig.js`) |
| `VITE_SUPABASE_URL` | Build e função de busca Vercel | Pública; URL do projeto do ambiente |
| `VITE_SUPABASE_ANON_KEY` | Build e função de busca Vercel | Chave pública anon do ambiente; segurança depende de Auth/RLS |
| `DATABASE_URL` | Runtime Render | Segredo; conexão SQLAlchemy `postgresql+psycopg://...`, credenciais próprias do ambiente e TLS |
| `SUPABASE_URL` | Runtime Render | URL do mesmo projeto usado pelo frontend |
| `SUPABASE_ANON_KEY` | Runtime Render | Chave anon usada na validação do token pelo Auth |
| `CORS_ORIGINS` | Runtime Render | Origens exatas da SPA, separadas por vírgula, sem caminho; evitar curingas |
| `PORT` | Runtime Render | Fornecida pelo provedor; usada pelo comando de início |
| `API_DOCS_ENABLED` | Runtime Render | `false` em homologação e produção: desliga `/docs`, `/redoc` e `/openapi.json` |
| `TRUSTED_PROXY_HOPS` | Runtime Render | Configuração para hospedagem própria. No Render, o limite usa o IP inserido pela borda em `CF-Connecting-IP`. |
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_WRITE_PER_MINUTE` | Runtime Render | Limite de requisições por cliente; padrões `240` e `60` |
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

Use [`frontend/vercel.json`](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/frontend/vercel.json) com Root Directory `frontend`. A configuração Vite (saída `dist`) preserva `/api/search` (`kind=sitemap` e `kind=event`), `/auth/retorno` -> `/app.html`, `/eventos` -> `/eventos.html` e rotas profundas em `/app.html`.

O [roteamento do frontend](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/frontend/vercel.json) gera títulos, descrições e URLs canônicas no HTML da home e da lista de eventos durante o build. As rotas da SPA, como `/admin`, `/configuracoes` e `/plano-de-ensino`, continuam aceitando acesso direto e recarga.

A função [de busca](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/frontend/api/search.js) responde a `/sitemap.xml` e `/evento/<id>`. Configure a URL e a chave pública do Supabase do mesmo ambiente no build e na função. As leituras passam pela RLS anônima e selecionam apenas eventos aprovados. A CDN pode guardar respostas públicas por cinco minutos. Teste o sitemap, um evento aprovado e um ID inexistente após a publicação. Após o deploy, envie o sitemap e solicite indexação no Search Console.

A SPA consome a API no Render diretamente por HTTPS através de `VITE_API_URL` (exigida no build em `frontend/src/lib/deploymentConfig.js`, terminada em `/api/v1`), inclusive no upload de 10 MiB, com `CORS_ORIGINS` restrito às origens explícitas da Vercel no Render.

> [!WARNING]
> **Atenção ao limite de upload (4,5 MB nas Vercel Functions):**
> O fluxo atual de upload de planos de ensino em `/api/v1/syllabus/upload` suporta arquivos de até 10 MB no FastAPI. Contudo, o limite de payload de requisições nas Vercel Serverless Functions é de 4,5 MB. Arquivos maiores que esse limite serão rejeitados com HTTP 413 pela camada de borda da Vercel antes de alcançar o FastAPI.
> Caso uploads entre 4,5 MB e 10 MB devam ser suportados sem falhas:
> 1. Adotar upload direto do frontend para o Supabase Storage via client SDK com RLS ou pre-signed URLs (enviando ao FastAPI apenas metadados/referência); ou
> 2. Manter a execução do backend como Web Service dedicado (ex: Render/container) para as rotas com transferências volumosas.

### Autenticação e Google Agenda (S7-F04)

1. No Supabase do ambiente, configure a Site URL da SPA e permita a URL exata `/auth/retorno` na origem correspondente. Habilite a confirmação de e-mail, mantenha pelo menos 8 caracteres para a senha e use intervalo mínimo de 60 segundos para novo envio.
2. Configure o SMTP de homologação e copie para **Confirm signup** e **Reset password** os templates [confirmation.html](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/supabase/templates/confirmation.html) e [recovery.html](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/supabase/templates/recovery.html). Os links carregam o hash no fragmento e exigem uma ação na página para consumi-lo. Desative o rastreamento de cliques nos e-mails de autenticação.
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
| RLS de notificações e Storage | Usuário não lê/atualiza recursos alheios; bucket legado permanece privado e novos PDFs são descartados após a preparação |
| Rotas SPA e CORS | Acesso direto funciona; origem autorizada integra API; origem não permitida não recebe liberação CORS |
| Saúde e dependências | `/health` responde e leituras reais/autenticação também funcionam |

Aceitar a implantação apenas com evidências registradas de migrações, builds, testes de fumaça e recuperação preparada. Não marcar como homologado somente porque um deploy terminou.

## Pendências do plano original, registro de 24/10

| Pendência futura | Papel responsável |
| --- | --- |
| Aprovar arquitetura final (Vercel multi-service vs Render para backend) considerando o limite de 4,5 MB de upload | Time e responsável pela release |
| Validar comportamento de upload de planos de ensino em ambiente hospedado Vercel | Backend e Frontend |
| Provisionar projetos Supabase, Auth, migrações, dados de homologação e recuperação | Banco de dados, com Backend |
| Criar workflows, secrets por ambiente, gates e publicação pelo SHA | Time, com Backend |
| Atualizar este documento com evidências e URLs efetivas | Responsável pela release |

Nenhum desses papéis representa atribuição nominal já aprovada. Mudanças de hospedagem, variáveis, migrações ou pipeline devem atualizar este documento no mesmo PR. Ver [Arquitetura](/arquitetura/visao-geral), [Contratos](/api-specs) e [Contribuição](/processo/contribuindo).

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
projeto de destino identificado. Ver as [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos)
e [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia).


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
