# Plano de hospedagem e CI/CD

## Estado e proposta

O [ADR-002](arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes.md) registra a proposta de separação da hospedagem e dos ambientes. Este plano detalha a configuração, a publicação e a recuperação.

Documento criado em **24/10/2026**, com referência no commit `e0ecf46`. **Este é um plano, não um registro de infraestrutura implantada.** O repositório comprova somente o workflow `Deploy Docs`, que publica MkDocs no GitHub Pages quando há mudanças pertinentes em `main` ou acionamento manual. Não existe pipeline da aplicação; `backend/Dockerfile` está vazio. A existência de `main` não comprova produção ativa.

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

### SPA, CORS e arquitetura multi-serviços (Vercel)

A raiz do repositório contém a configuração [`vercel.json`](../vercel.json) operando em modo de múltiplos serviços (Vercel Services):

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "services": {
    "backend": {
      "root": "backend",
      "framework": "fastapi"
    },
    "frontend": {
      "root": "frontend",
      "framework": "vite"
    }
  },
  "rewrites": [
    { "source": "/health", "destination": { "service": "backend" } },
    { "source": "/api/search", "destination": { "service": "frontend" } },
    { "source": "/api/(.*)", "destination": { "service": "backend" } },
    { "source": "/(.*)", "destination": { "service": "frontend" } }
  ]
}
```

O [roteamento do frontend](../frontend/vercel.json) gera títulos, descrições e URLs canônicas no HTML da home e da lista de eventos durante o build. As rotas da SPA, como `/admin` e `/plano-de-ensino`, continuam aceitando acesso direto e recarga.

A função [de busca](../frontend/api/search.js) responde a `/sitemap.xml` e `/evento/<id>`. Configure a URL e a chave pública do Supabase do mesmo ambiente no build e na função. As leituras passam pela RLS anônima e selecionam apenas eventos aprovados. A CDN pode guardar respostas públicas por cinco minutos. Teste o sitemap, um evento aprovado e um ID inexistente no preview antes da promoção. Após o deploy, envie o sitemap e solicite indexação no Search Console.

A SPA consome a API através de URLs relativas (`/api/v1/...`), aproveitando o roteamento unificado da Vercel no mesmo domínio sem requisições cross-origin (CORS). Se necessário apontar para um backend externo, a variável `VITE_API_URL` pode ser preenchida no ambiente.

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
