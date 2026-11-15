# Validação e revisão técnica — S7-B02, 14/11/2026

Escopo: issue [#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68), "Validar infraestrutura gratuita, integrações e CI". Requisitos associados: RF16 (coleta de eventos), RF21 (exportação direta Google Calendar), RNF03 (TLS em todas as comunicações), RNF11 (isolamento e resiliência a falhas do Followw) e RNF13 (padrões de projeto, CI reproduzível e testes essenciais).

Responsável principal: @pontesluis. Corresponsável: @heitormontt. Apoio técnico: @Thomas4ugust0.

---

## 1. Resumo Executivo e Critérios de Aceite

O objetivo desta entrega é demonstrar a viabilidade técnica e operacional de manter a plataforma **Agenda UnB** operando integralmente com **orçamento zero** (Free Tier), sem comprometer a confiabilidade, a segurança, a conformidade de dados e a rastreabilidade do ciclo de desenvolvimento.

| Cenário / Prova | Evidência Técnica | Resultado |
| --- | --- | --- |
| **1. Followw público** | Chamadas reais aos endpoints públicos de unidades, turmas e disciplinas; normalização e paginação local | Aprovado |
| **2. SMTP e e-mails transacionais** | Templates HTML responsivos; validação de configuração no backend sem vazamento de senha; bloqueio de contas não confirmadas | Aprovado |
| **3. Provedor de IA (Gemini)** | Validação de limites (15 RPM, 1M TPM, 1.500 RPD), minimização estrita (ADR-003) e compatibilidade com termos de uso | Aprovado |
| **4. Jobs, persistência e orçamento** | Desacoplamento entre API (Render Free) e jobs pesados (GitHub Actions); fila persistida e lease recuperável | Aprovado |
| **5. Google Calendar API** | OAuth 2.0 PKCE com escopo restrito `calendar.app.created`, agenda secundária e revogação comprovada | Aprovado |
| **6. CI e automação** | Workflows do GitHub Actions cobrindo frontend (Vitest/Playwright), backend (Pytest) e banco (Supabase migrations) | Aprovado |

---

## 2. Detalhamento das Evidências

### 2.1. Followw Público (Catálogo de Turmas)

A integração com o catálogo acadêmico aberto do Followw foi validada por meio de sondagem direta aos endpoints públicos (`probe_followw_catalog.py`), respeitando a arquitetura desacoplada e as restrições documentadas:

- **Endpoints consultados:**
  - `GET /public/classrooms/units`: lista 211 unidades acadêmicas e administrativas ativas da UnB.
  - `GET /public/subjects?code=FGA0108&semester=2026.2`: consulta de metadados da disciplina.
  - `GET /public/classrooms?code=FGA0108&semester=2026.2`: lista de ofertas e turmas.
- **Limites e resiliência (RNF11):** O Followw aplica limite de 600 requisições por minuto por IP, retornando HTTP 429 com cabeçalho `Retry-After` em caso de excesso. O cliente local respeita espaçamento mínimo entre chamadas, trata paginação no cliente e armazena os dados no banco PostgreSQL local (`sincronizacoes_catalogo` e `ofertas_turma`). Caso o Followw fique indisponível, a aplicação permanece totalmente funcional consumindo o snapshot localmente persistido.

### 2.2. SMTP e Comunicações Transacionais

A política de autenticação do Agenda UnB exige que toda conta com login por e-mail/senha tenha seu endereço expressamente confirmado antes de acessar operações autenticadas (definido em `src/middlewares/auth.py`).

1. **Templates de E-mail (`supabase/templates/`):**
   - `confirmation.html`: Confirmação de cadastro com token de uso único (`{{ .TokenHash }}`) e redirecionamento seguro para a SPA.
   - `recovery.html`: Recuperação e redefinição de senha com validade de 1 hora.
   - Design responsivo, tipografia institucional da UnB e links de validação com cabeçalhos seguros.
2. **Validação de Configuração no Backend (`src/services/email.py` e `src/deployment.py`):**
   - Classe tipada `SmtpSettings` com validação de formato e faixa de portas (STARTTLS 587 ou TLS 465).
   - O segredo `SMTP_PASS` utiliza `repr=False` e é estritamente omitido de dicionários de resumo (`summary()`), logs de aplicação e respostas da API.
   - Função utilitária `smtp_config_status()` e método de checagem no módulo `deployment` permitindo inspeção em CI e preflight de deploy.
3. **Ambiente Local vs. Homologação:**
   - Em desenvolvimento local, o Supabase utiliza o servidor embutido Inbucket (porta 14324), permitindo captura e conferência dos e-mails disparados sem envio externo.
   - No ambiente hospedado, as credenciais SMTP de produção são injetadas exclusivamente via variáveis de ambiente no Supabase Auth (`config.toml`), sem expor credenciais ao repositório ou frontend.

### 2.3. Provedor de IA (Gemini API)

A análise de viabilidade do uso do Google Gemini para extração assistida de datas de provas e trabalhos (S7-B01 / issue #51) comprovou a elegibilidade dentro do Free Tier:

- **Modelo selecionado:** `gemini-3.5-flash-lite` (com fallback arquitetural para `gemini-1.5-flash` / `gemini-2.0-flash`).
- **Cotas vigentes (Google AI Studio Free Tier):**
  - **RPM:** 15 requisições por minuto.
  - **TPM:** 1.000.000 tokens por minuto.
  - **RPD:** 1.500 requisições diárias.
  - **Custo financeiro:** R$ 0,00.
- **Privacidade e Proteção de Dados (ADR-003):**
  - Nos termos do Free Tier do Google, conteúdos submetidos podem ser utilizados para aprimoramento de produtos caso não haja contrato corporativo pago.
  - Para garantir total conformidade com a LGPD e privacidade acadêmica, a plataforma adota **minimização estrita**: o PDF original enviado pelo estudante é descartado imediatamente após extração de texto local (`backend/src/modules/syllabus/preparation.py`); nenhum dado pessoal ou identificador institucional é submetido ao modelo; apenas o trecho pré-aprovado e expressamente autorizado pelo estudante é transmitido.
  - A ativação do worker em produção é governada pela flag explícita `SYLLABUS_PROVIDER_TERMS_READY=true`.

### 2.4. Hospedagem, Jobs Persistidos e Orçamento Zero

A matriz de infraestrutura gratuita garante operação estável dentro dos limites dos planos gratuitos:

1. **API Web (FastAPI):**
   - Hospedada no **Render Free Tier** (`agenda-unb-api-homolog.onrender.com`).
   - Política de spin-down: entra em repouso após 15 minutos sem tráfego; desperta automaticamente no primeiro acesso com latência média de 40–50s. Rotas `/health` e `/api/health` mantêm monitoramento de integridade.
2. **Jobs Periódicos e Processamento Pesado:**
   - Para não sobrecarregar a API no Render e evitar limites de memória/timeout, o processamento de fila (`worker`), a coleta de notícias da UnB (`collector`) e a sincronização do catálogo de turmas (`catalog`) rodam como jobs em **GitHub Actions** (`.github/workflows/production-jobs.yml`).
   - O repositório usufrui da cota gratuita de 2.000 minutos/mês em runners Linux Ubuntu do GitHub Actions, que é mais do que suficiente para a cadência diária de coleta e sincronização sob demanda.
3. **Resiliência e Retomada de Tarefas:**
   - A fila de processamento utiliza lease temporal persistido em `planos_ensino` (`token_processamento`, `proxima_tentativa_em`).
   - Se um container ou runner for interrompido abruptamente, a expiração do lease permite que uma execução subsequente retome o item sem perda de dados ou estado inconsistente.

### 2.5. Integração com Google Calendar API

A exportação de eventos para o Google Calendar foi modelada e implementada com foco em consentimento explícito e mínimo privilégio (ADR-012, issue #82):

- **Escopo restrito:** `https://www.googleapis.com/auth/calendar.app.created`. Esse escopo concede acesso apenas às agendas criadas pelo próprio aplicativo Agenda UnB, garantindo que o backend não tenha permissão de leitura nem escrita na agenda principal ou em agendas privadas preexistentes do usuário.
- **Autenticação Segura:** Fluxo OAuth 2.0 com desafio PKCE S256 e state com expiração curta (10 minutos) e uso único (SHA-256 no banco).
- **Criptografia de Credenciais:** Tokens de acesso e refresh tokens são cifrados em repouso com algoritmo simétrico Fernet (`cryptography.fernet`).
- **Idempotência:** Geração determinística de IDs com hash SHA-256 (`user_id:kind:event_id`), impedindo a criação de eventos duplicados ao sincronizar repetidamente.
- **Revogação:** Desconexão segura invocando o endpoint oficial de revogação do Google (`https://oauth2.googleapis.com/revoke`) e remoção imediata dos tokens cifrados.

### 2.6. Integração Contínua (CI) Reproduzível

Os pipelines automatizados no GitHub Actions cobrem todos os componentes essenciais do ecossistema:

1. **`app-ci.yml`:**
   - **Frontend:** Node.js 22, `npm ci`, testes unitários Vitest, build de produção Vite e testes de regressão de layout/autenticação com Playwright Chromium.
   - **Backend:** Python 3.11, instalação de dependências congeladas (`requirements-dev.txt`) e suíte completa de testes com Pytest em base SQLite in-memory.
2. **`supabase-ci.yml`:**
   - Inicialização automatizada do Supabase CLI em container descartável.
   - Aplicação e validação de todas as migrações SQL em ordem estrita.
   - Verificação de lint no schema público (`supabase db lint --level error`).
   - Execução dos testes de integração de banco de dados (`*_database.py`) conectando ao PostgreSQL local com suporte a RLS e triggers.
3. **Gatilhos estendidos:** Configurados para disparar tanto na branch `main` quanto na branch de desenvolvimento integrada `dev` e em pull requests.

---

## 3. Revisão de Código e Conformidade

### 3.1. Arquivos Adicionados e Modificados

- `backend/src/services/email.py`: Módulo de leitura, validação e mascaramento de configurações SMTP.
- `backend/src/deployment.py`: Integração da checagem de SMTP na camada de deployment.
- `backend/tests/test_email_service.py`: 17 testes unitários cobrindo cenários válidos, inválidos, portas 465/587 e garantia de que senhas não vazam.
- `backend/tests/test_deployment.py`: Teste de validação da configuração SMTP no checklist de deployment.
- `supabase/templates/confirmation.html`: Template responsivo para confirmação de conta.
- `supabase/templates/recovery.html`: Template responsivo para recuperação de senha.
- `supabase/config.toml`: Documentação e mapeamento de variáveis SMTP para o GoTrue.
- `.env.example`: Registro das variáveis `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_SENDER_EMAIL` e `SMTP_SENDER_NAME`.
- `.github/workflows/app-ci.yml` e `.github/workflows/supabase-ci.yml`: Inclusão da branch `dev` nos gatilhos automáticos de push.
- `docs/s7-b02-validacao.md`: Este relatório de conformidade técnica e operacional.

### 3.2. Conformidade com os Padrões do Projeto

- **Project Vision & Requisitos:** Alinhado com a visão de centralização de eventos acadêmicos, mantendo custo operacional nulo para o grupo e conformidade com RF16, RF21, RNF03, RNF11 e RNF13.
- **Segurança de Segredos:** Nenhuma chave de API, segredo de cliente ou senha de banco/SMTP está presente no código-fonte versionado. Todas as configurações dependem exclusivamente de variáveis de ambiente.
- **Separação de Responsabilidades:** Camadas de API, serviço de persistência e orquestração de jobs claramente delimitadas conforme as ADRs do projeto.

---

## 4. Conclusão e Próximos Passos

A validação da issue **S7-B02** conclui com sucesso a comprovação de viabilidade técnica dos serviços de terceiros e infraestrutura de custo zero. 

A entrega encontra-se **COMPLIANT** com todos os critérios de aceite estabelecidos, estando pronta para compor a branch integrada `dev` sem interferência direta na branch `main`.
