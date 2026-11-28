---
title: "Uso de IA"
description: "Registro transparente do uso de inteligência artificial no projeto Agenda UnB, conforme exigido pelo plano de ensino de MDS."
---

Registro exigido pelo plano de ensino de MDS 2026/2. O princípio da disciplina é transparência, não proibição: não há penalidade por usar, há penalidade por não declarar e por não entender.

Cada integrante registra o próprio uso. Mantenha em ordem cronológica inversa (mais recente no topo).

**Onde o uso é esperado e deve ser registrado:** implementação, testes, documentação, exploração de bibliotecas e refatoração.

**Onde não é permitido:** arguições individuais presenciais, quizzes, avaliação por pares e o ensaio de reflexão crítica.

---

## Como preencher

Uma entrada por atividade relevante. Não precisa registrar autocompletar de editor ou consulta pontual de sintaxe — registre quando a IA produziu um artefato que entrou no repositório ou influenciou uma decisão.

```markdown
### [data] — [o que foi feito]
- **Quem:** nome
- **Ferramenta:** qual modelo/serviço
- **O que foi pedido:** em uma frase
- **O que entrou no repositório:** arquivos, PRs
- **O que foi verificado:** como você conferiu que estava certo
- **O que foi rejeitado ou corrigido:** o que a IA errou ou o que você decidiu não usar
```

O campo **verificado** é o mais importante. Sem ele, a entrada declara o uso mas não demonstra entendimento — e é entendimento que a disciplina avalia.

---

## Entradas

### 26/11/2026 — S8-B05: banco de dados e configuração para contingência de IA (fallback)
- **Quem:** Luis Davi
- **Ferramenta:** Google Antigravity (Gemini) e Pytest
- **O que foi pedido:** Preparar na branch `S8-B05` a parte de banco de dados e a configuração de variáveis/chaves para o roteamento de contingência OpenAI-compatível a custo zero (Groq/OpenRouter/Mistral), mantendo o Gemini como provedor primário, em commits atômicos.
- **O que entrou no repositório:** `docs/arquitetura/banco-de-dados.md` (documentação de `provedor_ia`, `provedor` e `modelo_ia` como `TEXT` livres), `backend/tests/test_syllabus_database.py` (teste parametrizado de persistência dos metadados de fallback no PostgreSQL), `.env.example` e `docs/deploy/render.env.example` (variáveis `SYLLABUS_FALLBACK_*`), `.github/workflows/production-jobs.yml` (repasse de secrets/vars de fallback ao job `worker`), `scripts/dev.py` (remoção de `SYLLABUS_FALLBACK_API_KEY` do ambiente do Vite) e esta entrada em `docs/processo/uso-de-ia.md`.
- **O que foi verificado:** Auditoria das migrações SQL e de `backend/src/database/models.py` confirmando zero migrações necessárias; `python -m pytest tests/test_schema_preflight.py -q` (`3 passed`), coleta de `tests/test_syllabus_database.py` (`23 tests collected`), validação de sintaxe Python (`py_compile`) em `scripts/dev.py` e YAML em `.github/workflows/production-jobs.yml`; configuração das variáveis no serviço `agenda-unb-api-homolog` no Render com deploy `live` confirmado.
- **O que foi rejeitado ou corrigido:** Nenhuma migração DDL foi criada e nenhum código de aplicação do backend ou frontend foi alterado nesta frente. A execução completa de `test_syllabus_database.py` no Supabase local foi interrompida por falta de espaço em disco no Docker local, ficando a execução no PostgreSQL isolado para validação no PR/CI.

### 24/11/2026 — Correção das falhas de extração, resiliência do worker e minimização de planos de ensino
- **Quem:** Luis Davi
- **Ferramenta:** Google Antigravity (Gemini) e Pytest
- **O que foi pedido:** Corrigir na branch `dev` as falhas de resiliência do worker, extração de datas/horários/siglas e minimização de planos de ensino diagnosticadas em produção, organizando em commits atômicos e registrando o uso em `uso-de-ia.md`.
- **O que entrou no repositório:** `backend/src/modules/syllabus/processing_config.py` (novos defaults de timeout `25s`/`35s`, até `3` tentativas configuráveis até `5`, `SYLLABUS_RETRY_DELAY_SECONDS`, orçamento `0.12` e `reference_schedule`); `render.yaml` e `.github/workflows/production-jobs.yml` (variáveis de resiliência do worker); `backend/src/modules/syllabus/worker.py` (espera de retentativas curtas no `--drain` via `drain_queue`/`next_short_retry_wait`, backoff progressivo, leitura de `ofertas_turma.horarios` e cache sensível ao horário da oferta); `backend/src/modules/syllabus/gemini.py` (migração para `v1beta/models/{model}:generateContent` com `client.post`, `responseJsonSchema` e remoção de caracteres de controle ASCII); `backend/src/modules/syllabus/processing_task.py` (`run_in_worker` com deadline em thread daemon evitando duplo `spawn` por tentativa); `backend/src/modules/syllabus/extraction.py` e `class_schedule.py` (aceitação de ordinais quebrados por quebra de linha, bloqueio de falso positivo de horário em rótulo antes de data, fallback de disciplina e horário da oferta vinculada); `backend/src/modules/syllabus/minimization.py` (suporte a rótulos em negrito Markdown `**` e `__`); `docs/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia.md`; testes em `backend/tests/test_syllabus_processing.py`, `test_syllabus_task.py`, `test_syllabus_minimization.py` e `test_syllabus_preparation.py`; e esta entrada em `docs/processo/uso-de-ia.md`.
- **O que foi verificado:** Execução da suíte completa do backend (`python -m pytest -q` com `453 passed, 150 skipped` — os ignorados dependem de PostgreSQL local/Gemini opt-in) e das suítes focadas de extração, worker, tarefas isoladas, minimização e preparação após cada commit atômico, validando também `git diff --check` e o histórico limpo na branch `dev`.
- **O que foi rejeitado ou corrigido:** A primeira versão do lookahead `_TIME_END_GUARD` bloqueava `\s*[/-]\s*\d`, fazendo falhar `test_alternative_or_range_hours_require_review[09:00 - 14:00]`; a regex foi ajustada para bloquear apenas barra (`\s*/\s*\d`) e formatos colados de data (`-\d{2}-\d{2,4}` e `\.\d{2}\.\d{2,4}`). Na minimização, `(?<!\w)` impedia casar rótulos com `__` (como `__Professor(a)__`) porque `_` pertence a `\w`; os limites foram ajustados para `(?<![^\W_])` e `(?![^\W_])`. Em `test_syllabus_preparation.py`, o teste `test_private_processing_omits_masked_values_from_provider_logs_and_candidates` passou a esperar `"Prova 1 - MDS"` devido ao fallback da disciplina da oferta vinculada. Fallback automático entre modelos Gemini não foi adicionado nesta entrega para preservar o contrato explícito de preços e auditoria da `ADR-014`.

### 20/11/2026 — Integração da Release 2 e endurecimento

- **Solicitante:** Thomas. **Ferramenta:** Codex.
- **Pedido:** Integrar a `dev` a `fix/s8-d02-endurecimento` e alinhar a documentação, o escopo e a preparação do deploy.
- **Entrega:** Revisão das descrições e discussões dos PRs pós-Sprint 6, incluindo o [#94](https://github.com/unb-mds/2026-2-AgendaUnB/pull/94). Retirada do histórico separado da agenda e da revisão manual do texto. Consolidação de cliques e fila de IA, correções de compatibilidade dos runtimes, retorno OAuth e atualização dos documentos legais.
- **Verificação** — 523 testes de backend, 62 unitários de frontend e 69 cenários de Playwright em cada navegador, Chromium, Edge e Firefox. A publicação atômica do catálogo passou em PostgreSQL isolado. Com Supabase local, um PDF sintético gerou dois candidatos em 7,91 s usando Gemini real e a confirmação criou um compromisso. Também passaram o ensaio de atualização a partir das versões remotas, o job local de lembretes, o container Render, o build Vercel e a verificação da documentação. Os ambientes hospedados foram consultados em leitura. [Evidências e ordem de publicação](/implantacao#estado-verificado-em-20112026).

### 19/11/2026 — S8-B02: consolidação de eventos salvos, redirecionamento deduplicado e históricos separados (#79)

- **Quem:** Thomaz Marra (solicitante).
- **Ferramenta:** Google Antigravity (Gemini), Pytest e Node Test Runner.
- **O que foi pedido:** Concluir na branch `feat/s8-b02-conferir-evento` a integração com a `dev`, os contratos de redirecionamento deduplicado, o cancelamento de lembretes futuros ao remover vínculo salvo e a separação dos históricos de eventos públicos salvos passados e compromissos privados passados.
- **O que entrou no repositório:** Conciliação das migrações `20261117151000_eventos_conferir_evento.sql` e `20261117200000_s8_f02_eventos_moderacao_categorias.sql` (evitando falha de `revoke` sobre `registrar_interesse` já removida e sincronizando a deduplicação entre `cliques_evento` e `eventos_cliques_redirecionamento`); endpoint `GET /api/v1/me/events/history`, suporte a `click_id`/`clickId` em `POST /api/v1/events/{id}/outbound-clicks` e sincronização/cancelamento de lembretes futuros no ORM (`backend/src/modules/events/router.py`, `schemas.py`, `models.py`); separação visual e lógica dos históricos de públicos salvos passados e compromissos privados passados em **Meus Eventos** (`frontend/src/lib/calendar.js`, `frontend/src/pages/SecondPage.jsx`, `frontend/src/lib/api.js`); testes em `backend/tests/test_saved_events_api.py`, `backend/tests/test_event_clicks_database.py` e `frontend/src/lib/calendar.test.js`; documentação atualizada em `docs/arquitetura/conferir-evento.md`, `docs/api-specs.md`, `docs/sprints/sprint-8.md` e `docs/matriz-release-2.md`.
- **O que foi verificado:** Execução da suíte automatizada do backend (`298 passed`) e dos testes unitários do frontend (`62/62 passed` em `node --test src/lib/*.test.js`), validação de sintaxe JSX com `esbuild` e `git diff --check`.
- **O que foi rejeitado ou corrigido:** A migração `20261117200000` executava `revoke all on function public.registrar_interesse(uuid)` assumindo que a função ainda existia, o que falharia após `drop function if exists public.registrar_interesse(uuid)` na migração `20261117151000`; o `revoke` foi protegido por verificação condicional `to_regprocedure('public.registrar_interesse(uuid)') is not null`. Também foi adicionado `email_confirmed_at = now()` às contas sintéticas de `test_event_clicks_database.py` para compatibilidade com a política restritiva de e-mail confirmado da `dev`.
### 19/11/2026 — Minimização de dados pessoais em planos de ensino (#132)

- **Quem** — Heitor Gomes Monteiro, com assistência do Codex.
- **Ferramentas** — Codex, Impeccable, pytest e Playwright.
- **O que foi pedido** — Aprimorar a sanitização de PDF e texto colado,
  manter o conteúdo acadêmico e mostrar as ocorrências mascaradas na revisão.
- **O que entrou no repositório** — Regras determinísticas, preparação
  compartilhada, contagem persistida, bloqueio de texto legado detectável,
  aviso acessível e testes de regressão e integração.
- **O que foi verificado** — Hash do snapshot privado, controle de acesso,
  procedência dos candidatos, privacidade no fluxo com provedor simulado e
  edição em celular e desktop. [Exemplos e resultados](/arquitetura/minimizacao-planos).
- **Ajuste durante a validação** — O teste de upload concorrente passou a
  manter o segundo envio aberto até o terceiro ter começado, permitindo
  medir a concorrência em ambientes com tempo de resposta diferente.

### 18/11/2026 — S8-F02: eventos, moderação, agenda, filtros múltiplos e melhorias de uso (#80)

- **Quem:** Gabriel Escramin (solicitante).
- **Ferramenta:** Google Antigravity (Gemini), Impeccable (`critique`, `polish`, `harden`, `colorize`), Vite e `node --test`.
- **O que foi pedido:** Concluir na branch `feat/s8-f02-eventos-e-melhorias` as entregas de banco, API, interface de calendário/detalhes/moderação, filtros combináveis com múltipla seleção, edição pública por professor/admin, menu de logout e acabamento visual da issue #80 (`S8-F02`).
- **O que entrou no repositório:** Migração `supabase/migrations/20261117200000_s8_f02_eventos_moderacao_categorias.sql` (`localizacao` em `eventos_pessoais`, redirecionamento deduplicado em `registrar_redirecionamento_evento`, gestão admin de categorias e projeção de intervalos/dia inteiro); endpoints FastAPI em `backend/src/modules/events/router.py` e `schemas.py` (`all_day`, `ends_at`, `POST /events/{id}/outbound-clicks`, `PUT /events/{id}` para `professor`/`admin` e CRUD admin em `/api/v1/categories`) com testes em `backend/tests/test_events_api.py`; calendário multi-dia em `America/Sao_Paulo` (`calendar.js`, `EventCalendar.jsx`), ações independentes em `PaginaDeEvento.jsx`, fila de coleta em `SuggestionsPage.jsx`, gestão de categorias em `AdminPage.jsx`, filtros múltiplos com checkbox (`CustomSelect.jsx`, `preferences.js`), edição de eventos públicos restrita a `professor`/`admin` e remoção do botão de voltar em `SecondPage.jsx`, `ProfileMenu.jsx` com logout na `NavBar.jsx`, polimento de contraste/responsividade em `global.css` e `management.css`, e atualização de `docs/api-specs.md`, `docs/sprints/sprint-8.md` e `docs/matriz-release-2.md`.
- **O que foi verificado:** Build de produção do frontend (`npm --prefix frontend run build`) e **50/50** testes unitários em `frontend/src/lib/*.test.js` (`npm --prefix frontend test`) aprovados após as últimas alterações; detector mecânico `impeccable detect --json` sem novos achados nos componentes e páginas alterados (restando apenas o aviso pré-existente da fonte `Inter`, definida no `DESIGN.md`); checagem de sintaxe Python (`python -m py_compile`) nos arquivos alterados do backend. A execução da suíte `pytest` com as dependências da `.venv`, a aplicação da migração no PostgreSQL de destino e a homologação manual dos critérios de aceite ficaram pendentes para a etapa final de PR.
- **O que foi rejeitado ou corrigido:** A barra de botões rápidos `"Campi UnB"` e a aba separada `"Histórico"` (RF18) adicionadas inicialmente em `SecondPage.jsx` foram removidas por decisão do solicitante, mantendo os cinco campi no seletor `Qualquer campus` e deixando a visualização do RF18 vinculada à integração com a `#79` (`S8-B02`). Nos ajustes de qualidade e UI, foram removidos `side-tab` (`borderLeft`), gradientes lineares e badges/botões translúcidos com borda colorida (substituídos por cores sólidas de alto contraste, inclusive no botão `"Sair da conta"`), equalizados os filtros em `<= 600px` e preservados `linkExterno` e visibilidade na edição de eventos públicos.

### 17/11/2026 — S8-B01: endpoints de compartilhamento, versões, procedência e votos (#77)

- **Quem:** Thomaz Marra (solicitante).
- **Ferramenta:** Google Antigravity (Gemini) e Pytest.
- **O que foi pedido:** Completar na branch `feat/s8-b01-compartilhamento-planos` os endpoints FastAPI, schemas, testes HTTP e documentação da issue #77 sobre a migração SQL já criada.
- **O que entrou no repositório:** Rotas de compartilhamento/retirada (`PUT/DELETE /syllabus/{id}/versions/{vid}/sharing`), criação e edição de revisão (`POST /syllabus/{id}/versions`, `PUT /syllabus/{id}/versions/{vid}`), validação de procedência institucional (`PUT .../provenance`), votação e resumo de divergência (`PUT .../vote`, `GET .../votes`), suporte a `versionId` em `POST /syllabus/{id}/confirm`, enriquecimento de `GET /class-offerings/{id}/shared-plans`, suíte `backend/tests/test_plan_sharing_api.py` e atualização de `docs/arquitetura/dados-de-planos.md`, `docs/api-specs.md` e `docs/sprints/sprint-8.md`.
- **O que foi verificado:** Execução de `pytest tests/test_plan_sharing_api.py tests/test_syllabus_review_api.py tests/test_class_catalog_api.py` (40 testes aprovados) e da suíte completa do backend (`226 passed`), validando isolamento de rascunhos privados diante de `professor`/`admin`, voto único editável sem alterar datas e preservação de cópias importadas e revisões após retirada.
- **O que foi rejeitado ou corrigido:** No SQLite de testes, `DateTime(timezone=True)` devolvia `starts_at` sem `tzinfo` quando o seguidor importava um candidato sem sobrescrever a data no payload, gerando `422` indevido; o fallback SQLite foi ajustado para preservar o fuso da avaliação não ambígua, alinhando-o ao comportamento de `confirmar_importacao` no PostgreSQL.

### 16/11/2026 — Links da documentação e execução local

- **Quem:** Codex, a pedido do mantenedor.
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Corrigir os links e redirecionamentos da documentação na `dev` e documentar a instalação e a execução local.
- **O que entrou no repositório:** Links e redirecionamentos atualizados, compatibilidade com o MkDocs e [guia de execução local](/processo/execucao-local).
- **O que foi verificado:** Links, âncoras e redirecionamentos na prévia do Mintlify, build estrito do MkDocs e inicialização do Supabase, da API e do frontend em cópia isolada.

### 15/11/2026 — Sugestão de horário de prova na revisão de datas

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI), Impeccable e Playwright.
- **O que foi pedido:** Usar o horário da oferta da turma para preencher a hora da prova na aba **Revisar datas**, com edição antes da confirmação.
- **O que entrou no repositório:** Conversão dos códigos SIGAA retornados pela API de turmas, sugestão no editor com indicação de origem, testes de regressão e documentação da sugestão na revisão de datas. Commits `53085ee`, `cf9afbd` e `b15c30c` na branch `feat/gemini-api` (regra consolidada na `ADR-010` após atualização com `dev`).
- **O que foi verificado:** A conversão foi conferida com a [grade SIGAA da UnB](https://design.unb.br/codigos-aulas-sigaa/) e exemplos do catálogo. Passaram 42 testes de lógica, o build do frontend e os cenários Playwright de sugestão, edição, confirmação e entrada manual com o catálogo indisponível. Os testes de navegador usaram respostas controladas da API.
- **O que foi rejeitado ou corrigido:** A sugestão só usa o início de um bloco único no dia da prova. Horários do plano e edições manuais são preservados. Os testes de revisão foram alinhados ao fuso fixo de Brasília e ao contrato atual de confirmação. Uma divergência na mensagem de erro do envio de texto bruto também foi reproduzida na branch base e fica fora deste ajuste.

### 13/11/2026 — Roteiro de homologação S7-B02 (#68)

- **Quem:** Heitor Gomes Monteiro, com assistência do Codex.
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** registrar as evidências da #68 e preparar os testes de Calendar, SMTP e retomada dos jobs para alinhamento dos acessos com Thomas.
- **O que entrou no repositório:** roteiro de homologação com pré-requisitos, passos, resultados esperados e links das provas anteriores.
- **O que foi verificado:** rotas e configurações conferidas no código candidato e nos PRs #110 e #113. O roteiro registra como evidências anteriores a sondagem do Followw, o benchmark sintético Gemini, o CI e os 92 testes locais de 13/11. As provas hospedadas do roteiro permanecem pendentes.

### 11/11/2026 — Revisão final e documentação da jornada (#73)

- **Quem:** Gabriel Escramin (solicitante).
- **Ferramenta:** Codex (OpenAI), Impeccable polish/harden e Playwright.
- **O que foi pedido:** Revisar o acabamento e consolidar evidências locais e pendências de homologação.
- **O que entrou no repositório:** Explicação dos campos obrigatórios e do bloqueio da confirmação, teste da orientação e guia atualizado da jornada particular.
- **O que foi corrigido:** O guia ainda descrevia revisão indisponível, variantes removidas e retenção de PDF no Storage como comportamento atual. Essas descrições foram substituídas pelo contrato vigente.
- **Verificação:** Inspeção visual do editor e estados de erro/sucesso em celular e desktop, conferência de links locais e cálculo de contraste dos pares de tokens de texto revisados. A execução final das suítes e seus limites está consolidada no guia de planos.
- **Limites:** Sem homologação, medição RNF06, auditoria WCAG completa ou aprovação humana. O build MkDocs não pôde ser executado porque o módulo não está instalado no ambiente.

### 11/11/2026 — Recuperação da jornada particular (#73)

- **Quem:** Gabriel Escramin 
- **Ferramenta:** Codex (OpenAI), project-standards e Impeccable (harden/polish).
- **O que foi pedido:** Completar validações, histórico e recuperação de falhas da jornada de planos.
- **O que entrou no repositório:** Contagem UTF-8, validação da prévia, consulta obrigatória após autorização incerta, proteção de respostas assíncronas, atualização do histórico e navegação de recuperação por PDF/texto.
- **O que foi corrigido:** Limite por caracteres divergente do servidor, prévia malformada causando falha de renderização, possibilidade de repetir autorização sem conferir estado salvo e histórico desatualizado após autorizar.
- **Limites da verificação:** Testes locais do frontend e navegador com respostas controladas. A jornada real e o tempo RNF06 precisam de homologação com backend, banco e provedor disponíveis.

### 11/11/2026 — Oferta seguida obrigatória no envio de planos (#73)

- **Quem:** Gabriel Escramin 
- **Ferramenta:** Codex (OpenAI), skills project-standards, code-review e Impeccable (harden/polish).
- **O que foi pedido:** Revisar as dependências e exigir vínculo da própria conta para PDF/texto, com autorização explícita para o ajuste de backend.
- **O que entrou no repositório:** Verificação de oferta disponível e vínculo antes da extração e antes da persistência, bloqueio de envio na interface até consultar as turmas seguidas, testes de regressão, ajuste da paginação em celular e contrato HTTP atualizado.
- **O que foi corrigido:** O identificador de uma oferta disponível podia ser inserido diretamente na URL ou enviado à API sem seguir a turma. O histórico particular permanece acessível ao dono após remover o vínculo.
- **Limites:** Testes locais utilizam SQLite e fixtures de autenticação; testes de navegador controlam as respostas da API. PostgreSQL concorrente e a jornada completa em homologação exigem validação própria. O merge da main preparado anteriormente permanece separado das alterações desta etapa no índice do Git.

### 10/11/2026 — Segurança (S8-D02), parte de dados de seis issues e privacidade (S8-D01)
- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic), interface web
- **O que foi pedido:** revisar a segurança do projeto e resolver a parte de banco das issues em que sou responsável ou corresponsável, deixando prontas as funções e a documentação que os responsáveis pela API, pelo coletor e pelo agendador precisam
- **O que entrou no repositório:** um PR por issue, conforme o template. [#84](https://github.com/unb-mds/2026-2-AgendaUnB/issues/84): migração `20261117130000` (endurecimento), proteções da API em `middlewares/security.py` e `docs/processo/seguranca.md`. [#75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75): `20261111140000` (datas civis e coleta). [#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72): `20261111141000` (confirmação idempotente). [#70](https://github.com/unb-mds/2026-2-AgendaUnB/issues/70): `20261110142000` (catálogo). [#77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77): `20261117150000` (compartilhamento e votos). [#79](https://github.com/unb-mds/2026-2-AgendaUnB/issues/79): `20261117151000` (Conferir evento). [#81](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81): `20261117152000` (lembretes). [#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83): `20261117160000`, módulo `account`, script de descarte de PDFs, política de privacidade e termos de uso. Cada PR traz os modelos do ORM, os testes de banco e o guia de integração da sua issue
- **O que foi verificado:** a IA executou cada branch em PostgreSQL 16 com um substituto mínimo do Supabase (papéis, `auth.users`, `storage.objects` e o histórico de migrações), aplicando todas as migrações do zero: #84 com 229 testes, #75 com 209, #72 com 215, #77 com 223, #81 com 229, #83 com 243, #79 com 194 e #70 com 194 (números sobre a `dev` de 10/11; após a atualização de 11/11 com a `main`, os números de cada branch estão na descrição do PR), além do build estrito da documentação. **Não foi exercitado** em Supabase hospedado: Auth, Storage, TLS e CORS reais ficam para a homologação. Minha conferência no Supabase local, antes de abrir os PRs: rodei #84 (229 passed), #75 (209), #72 (215) e #77 (223), com os mesmos números da IA; as demais não rodei localmente.
- **O que foi rejeitado ou corrigido:** os testes encontraram erros da própria IA durante o trabalho: a trava de conteúdo compartilhado impedia excluir um plano inteiro; um teste usava um hash mais curto do que a regra do banco aceita; e a exclusão de conta falhava porque `eventos_pessoais.user_id` não tinha `ON DELETE CASCADE`, um defeito antigo do esquema que virou correção. Ao atualizar com a `dev`, foram corrigidas a numeração das migrações (a nuvem já tinha a `20261110120000` e o `db push` recusa números menores), a escrita aberta na fila de processamento (#92) e uma política que deixava o dono do plano ler o rascunho de revisão de outra conta. Em 11/11, com a publicação do catálogo (`20261111120000`) já na `main`, as migrações destes PRs foram renumeradas para `20261117130000` em diante, para que rodem na mesma ordem no banco local e na nuvem, e cada branch recebeu a correção da CI da `dev`. Em 17/11, com a `dev` 110 commits à frente, as branches ainda abertas foram atualizadas de novo e as migrações renumeradas para `20261117...`: a `20261111150000` do compartilhamento coincidia com a da S7-F04, e a `dev` já tinha migrações até `20261114190000`. Na segurança, a regra de professor da S7-F04 substituiu a minha (eram equivalentes), e o endurecimento passou a manter o acesso às funções criadas depois dele (`listar_eventos_publicos`, conferências de e-mail e revisão da coleta). A privacidade foi alinhada ao fluxo de texto preparado da S7-B01, sem duplicar o registro de autorização da IA. A primeira entrega reunia várias issues em um PR; foi dividida em um PR por issue. Ficaram como decisões da equipe, e não da IA: o modelo da coleta (#75 e #93), a tabela de fila duplicada e o destino dos eventos públicos e das revisões de terceiros quando uma conta é excluída

### 10/11/2026 — Resolução dos conflitos do PR #108 (dev → main)

- **Quem:** Codex, a pedido de Thomas.
- **Ferramenta:** OpenAI Codex.
- **O que foi pedido:** Resolver os três conflitos e mesclar dev em main pelo PR #108.
- **O que entrou no repositório:** Atualizações da main preservadas nos documentos em `docs/processo/`, referência do template de PR atualizada e schema do Vercel mantido junto ao fallback SPA.
- **O que foi verificado:** Diff sem erros e sem arquivos não mesclados; JSON do Vercel válido; 17 testes do frontend e build aprovados; backend com 143 testes aprovados e 52 ignorados. MkDocs não executado por ausência do módulo no ambiente.
- **O que foi rejeitado ou corrigido:** Evitada a restauração dos documentos antigos, preservando seus redirecionamentos e o conteúdo novo nos caminhos canônicos.

### 10/11/2026 — Template de PR e fluxo por issue

- **Quem:** Codex, a pedido de Thomas.
- **Ferramenta:** OpenAI Codex.
- **O que foi pedido:** Reaplicar o template de PR na cópia atual do repositório, com uma branch e um PR por issue e status baseado nos checks da issue.
- **O que entrou no repositório:** `.github/PULL_REQUEST_TEMPLATE.md` e orientações em `docs/CONTRIBUTING.md` e `docs/processo/contribuindo.md`.
- **O que foi verificado:** Estado inicial limpo na main, ausência do template anterior e `git diff --check`. O build estrito da documentação foi tentado, mas o executável Python disponível não pôde ser iniciado neste ambiente.
- **O que foi rejeitado ou corrigido:** Evitada a duplicação do checklist da issue no PR. O template orienta atualização manual, sem sincronização automática ou bloqueio de merge.

### 10/11/2026 — Migração do Supabase Cloud e preparação Render/Vercel

- **Quem:** Heitor Gomes Monteiro, com assistência do Codex.
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** revisar e aplicar as cinco migrações pendentes no projeto Supabase da equipe, preservando os dados, e preparar a configuração para Render e Vercel.
- **O que entrou no repositório:** modelos de variáveis por provedor em `docs/deploy/`, guia de configuração e registro operacional com o estado do banco. Backup, scripts operacionais e arquivos com credenciais ficaram somente na pasta ignorada `.supabase/`.
- **O que foi verificado:** backup lógico consistente de 48 tabelas, restauração isolada, ensaio das cinco migrações e 49 testes PostgreSQL aprovados. Ensaio remoto com rollback e aplicação das cinco migrações em uma única transação, incluindo histórico. A comparação de hashes confirmou a preservação dos dados existentes. Após a transação, foram confirmadas 26 migrações e dez verificações de privacidade. Cinco campi e sete categorias foram preservados. A tabela legada estava vazia quando foi removida.
- **O que foi rejeitado ou corrigido:** não reaproveitar chaves públicas locais recusadas pelo projeto remoto, não executar wrappers de transação com commit intermediário e não versionar credenciais. A restauração de ensaio precisou preservar os proprietários e privilégios originais. A fila paralela não foi tratada como consumidor do worker atual. Naquela operação, as flags ficaram em `false`. O deploy integrado e a homologação ficaram para as issues #68 e #76.

### 09/11/2026 — S7-D01: turmas, vínculos, versões e isolamento dos planos (#69)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic)
- **O que foi pedido:** leitura da documentação do projeto (visão, requisitos, padrões, arquitetura e planejamento da R2) e modelagem das ofertas de turma, vínculos, versões de plano e regras de isolamento, com testes e documentação.
- **O que entrou no repositório:** migração `20261109120000_turmas_vinculos_versoes.sql`, modelos em `backend/src/database/models.py`, `backend/tests/test_classes_database.py`, dicionário de dados, DER e `padroes.md` (PR #88).
- **O que foi verificado:** a migração foi aplicada sobre dados já existentes (plano, candidatos e evento importado), e confirmei que todos ganharam a versão 1. Os 6 testes novos passam no PostgreSQL e falham num banco sem a migração. A suíte completa passou com o banco local (71 testes), e o `supabase start` subiu do zero.
- **O que foi rejeitado ou corrigido:** a decisão de manter `avaliacoes` como tabela de candidatos e remover `candidatos_avaliacao` foi minha, confirmada com o Thomas e o Thomaz. Não aceitei deixar a unicidade de importação global, porque bloquearia colegas ao importar uma versão compartilhada. O compartilhamento do PDF ficou para a S8-B01, como diz o planejamento.

### 04/11/2026 — Correção das migrações da S6-D02 que impediam o `supabase start` (PR #63)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic)
- **O que foi pedido:** descobrir por que a `dev` não subia o banco e corrigir.
- **O que entrou no repositório:** correção de nomes de coluna, tabela e bucket em `20261029153745_s6_d02_parte1_rls_tabelas.sql` e `20261029154524_s6_d02_parte2_rls_storage.sql`.
- **O que foi verificado:** reproduzi o erro (`column "proprietario_id" does not exist`), apliquei todas as migrações sem erro e testei que o dono vê os próprios planos, candidatos e PDFs, enquanto outro usuário e o visitante não veem nada.
- **O que foi rejeitado ou corrigido:** a função `confirmar_candidatos_transacional` também aponta para uma tabela inexistente, mas não a alterei, porque é do escopo do Luis. Registrei no PR para decisão do grupo.

### 28/10/2026 — S6-D01: planos particulares e candidatos (#53, PR #56) e compatibilização com o upload (#40)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic)
- **O que foi pedido:** modelagem dos planos particulares, estados de processamento e candidatos com procedência; depois, a correção do conflito com a migração do upload (#40), que quebrava o `supabase start`.
- **O que entrou no repositório:** migração `20261027120000_planos_particulares_e_candidatos.sql`, ajustes de status e `professor_id` no módulo de upload e seus testes, DER e dicionário de dados.
- **O que foi verificado:** apliquei as migrações com dados anteriores à #40 e com uma linha criada pelo código da #40; as constraints, a conversão de status e a idempotência foram testadas, e o pytest do back-end continuou passando.
- **O que foi rejeitado ou corrigido:** a primeira versão criava colunas próprias (`proprietario_id`, `arquivo_caminho`) que duplicavam as da #40; adotei os nomes que o back-end já usava. Mantive os status em português, como no plano da Sprint 6, em vez dos valores em inglês.

### 14/10/2026 — Issues #41, #42 e #43: sugestão de eventos, RLS do painel admin e bucket de planos

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic)
- **O que foi pedido:** migrações para as três issues.
- **O que entrou no repositório:** `20261014120000`, `20261014120100` e `20261014120200`.
- **O que foi verificado:** 50 testes em PostgreSQL simulando cada papel (visitante, aluno, professor, admin e back-end), e `supabase start` local antes do PR.
- **O que foi rejeitado ou corrigido:** durante a revisão, encontramos uma falha da minha migração de `profiles`: qualquer usuário logado podia se promover a admin pelo navegador. Ela foi fechada na #42 e reproduzida antes e depois da correção.

### 18/09/2026 — Ajustes de autenticação, correções de UI e modularização do CSS

- **Quem:** Thomas Augusto Amorim de Araujo
- **Ferramenta:** Google Antigravity (Gemini)
- **O que foi pedido:** Criar SVG para o botão de entrada como visitante, implementar função de fechar modais no Esc e modularizar o CSS em arquivo separado como boa prática.
- **O que entrou no repositório:** `src/App.jsx` (lógica dos modais, fechamento via tecla `Esc`) e `src/styles/global.css` (novo arquivo com todo o CSS da aplicação).
- **O que foi verificado:** Execução com sucesso do `npm run build` confirmando que o Vite empacotou o CSS estático sem erros, verificação da abertura/fechamento dos modais no clique e no `Esc`, validação do contraste de texto do botão no tema claro.
- **O que foi rejeitado ou corrigido:** Correção da cor do texto do botão de login no tema claro para garantir legibilidade com `#1a1a2e`, e correção da sintaxe das propriedades de tipografia nos links da navbar.

### 15/09/2026 — Modelagem do banco de dados (objeto de estudo, não adotado)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic), interface web
- **O que foi pedido:** schema PostgreSQL para o Agenda UnB, com políticas de Row Level Security, a partir dos requisitos e da stack definida (Supabase + SPA Vite)
- **O que entrou no repositório:** **nada.** O schema gerado foi usado como objeto de estudo, para eu entender Row Level Security, modelagem de agenda acadêmica e as limitações de uma arquitetura sem servidor. A modelagem que for para o repositório será escrita por mim, com as decisões discutidas pela equipe
- **O que foi verificado:** o schema foi executado num PostgreSQL 16 real, não apenas revisado por leitura. Uma suíte de 17 verificações cobriu constraints, o trigger de restrição de domínio institucional e — o que mais importa — cenários de vazamento: aluno não matriculado tentando ler avaliações e o PDF de turma alheia, e usuário tentando gravar registro em nome de terceiro
- **O que aprendi com o estudo:** que RLS não é camada extra num SPA sem servidor, é a única camada de segurança; que a data de uma avaliação pertence à turma e não ao aluno, senão o mesmo plano de ensino é reprocessado por cada matriculado e as datas divergem entre colegas; e que extração automática precisa registrar origem e confiança no próprio schema, porque agenda com data errada é pior que agenda nenhuma
- **O que foi rejeitado ou corrigido:**
  - A primeira versão da coluna gerada `eventos.periodo` produzia um erro críptico do PostgreSQL em vez da mensagem clara da constraint, porque colunas geradas são avaliadas antes das constraints. Corrigido com `greatest()`
  - A primeira suíte de testes passava com um vazamento dentro: rodava como dono da tabela, e **RLS não se aplica ao dono**. O teste foi reescrito para assumir o papel `authenticated`
  - Duas lacunas encontradas só depois de testar cenários de abuso: não havia policies de Storage, e qualquer aluno inseria no catálogo institucional sem rastreabilidade
  - Conflitos identificados entre o schema estudado e o `docs/requisitos.md`, ainda **não resolvidos**: o RF01 permite e-mail pessoal enquanto o trigger restringe ao domínio da UnB; o RNF01 exige hash de senha, que o Supabase Auth gerencia internamente; os papéis do RF04 (`student`/`professor`/`admin`) divergem dos do schema. São decisões de equipe, não correções técnicas

### 09/09/2026 — Limpeza do versionamento (PR #2)

- **Quem:** Felipe Couto Duque
- **Ferramenta:** Claude (Anthropic), interface web
- **O que foi pedido:** diagnóstico do estado do repositório e correção do versionamento
- **O que entrou no repositório:** commits `1c65b8c`, `0f01481`, `eb9115d` — remoção de `node_modules` e `dist` do índice, ampliação do `.gitignore`, criação de `.env.example` e `.gitattributes`, correção do `package.json`
- **O que foi verificado:** a justificativa do PR não é teórica. Um clone limpo em Linux falhou no build com `Cannot find module @rollup/rollup-linux-x64-gnu`, provando que o `node_modules` versionado não substituía a instalação. Também foi verificado, em repositório isolado, que `git rm --cached` preserva os arquivos no disco de quem executa mas os remove do disco de quem faz `pull` — o que motivou o aviso ao grupo
- **O que foi rejeitado ou corrigido:** o diagnóstico inicial afirmava que o repositório tinha um único commit. Era erro de método — o clone havia sido feito com `--depth 1`. São 15 commits, e o grupo já usava branches de feature com PR. A correção foi registrada antes do PR ser aberto

---

## Nota de honestidade

Este arquivo foi redigido com auxílio da I.A. A estrutura e o texto das entradas contém ajuda da I.A; os fatos, as verificações e as correções descritas aconteceram de fato e podem ser conferidos no histórico do Git e nos arquivos citados.


## Histórico técnico da extração Gemini (S6/S7)

### 10/11/2026 — Interface de autorização e validação final S7-B01

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI), Chromium/Playwright, PostgreSQL/Supabase locais e Gemini com corpus sintético.
- **O que foi pedido:** Concluir o escopo atualizado da Sprint 07 e realizar commits na `feat/geminiapi`, preservando o Supabase na nuvem.
- **O que entrou no repositório:** Entrada de texto, revisão editável por página, confirmações independentes e desmarcadas ao editar, hash canônico, reprocessamento explícito e caminho manual. Controle de privacidade/imutabilidade, fechamento do temporário antes do registro, descarte do rascunho anterior às correções, ajustes dos testes legados e evidências/documentação do protocolo S7.
- **O que foi verificado:** **171 testes de backend aprovados e um ignorado**, incluindo 31 testes SQL reais e o transporte HTTP Auth/Storage/PostgREST local. **25 testes de preparação no Windows**, **16 de lógica frontend** e **38 de navegador** aprovados. Build frontend aprovado. Inspeção visual em desktop escuro/celular claro e detector mecânico sem achados nos alvos. Gemini real: sete acertos, zero omissões/extras/divergências/datas inventadas; máximo de 10,026s entre fila/provedor no corpus de até dez páginas. Preparação e tempo humano registrados separadamente. Nenhum evento antes de revisão explícita; confirmação repetida não duplicou.
- **O que foi rejeitado ou corrigido:** Teste reproduziu hash instável quando JSONB reordena campos; o formato passou a ser canônico. A revisão legada foi preservada para planos sem preparação S7. A negação de UPDATE por privilégio revogado exige `42501`, não somente contagem zero por RLS. O WSL relay interceptava as portas Windows; a suíte rodou na rede do contêiner descartável, com proxy loopback para seu próprio gateway e credenciais locais só em memória. Não houve migração/alteração na nuvem, habilitação de flags no `.env` ou exposição de credenciais. Revisão humana, aprovação S7-B02, integração dos consumidores e versão implantada permanecem identificadas como pendentes.

### 10/11/2026 — Preparação privada e autorização do texto na S7-B01

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Completar o escopo atualizado da Sprint 07 na branch `feat/geminiapi`, com commits e sem alterar o Supabase na nuvem.
- **O que entrou no repositório:** Preparação de PDF/texto sem retenção do original, minimização inicial, revisão privada com hash do texto exato, autorização explícita, worker limitado ao snapshot aprovado e bloqueio por termos/elegibilidade S7-B02. Migração versionada de suporte, ainda não aplicada na nuvem.
- **O que foi verificado:** Dez testes novos passaram com SQLite: nenhuma fila antes da autorização, páginas físicas para PDF e nulas para texto bruto, consentimento e hash obrigatórios, controle do dono, reprocessamento explícito e ausência de eventos automáticos. A suíte legada está sendo atualizada para o novo contrato antes da entrega final.
- **O que foi rejeitado ou corrigido:** O requisito trazido pelo solicitante substitui a retenção do PDF prevista no plano anterior. A regex não é tratada como anonimização garantida. Credenciais e conteúdo não são registrados em logs; habilitação em produção continua condicionada à S7-B02.

### 09/11/2026 — Sincronização da branch remota antes do push

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Publicar a `feat/geminiapi` para abrir PR, sem alterar o Supabase.
- **O que entrou no repositório:** Merge das atualizações já presentes na branch remota, preservando os 11 commits locais, as rotas de revisão legadas, limites de upload, autenticação/Storage da equipe e o worker privado. Conflitos de modelos, upload e documentação resolvidos; mocks de Storage restritos aos testes.
- **O que foi verificado:** 113 testes locais aprovados e 31 ignorados por exigirem PostgreSQL/HTTP local ou Gemini opt-in. Suíte executada com banco SQLite, sem habilitar integrações externas. Documentação estrita e ausência de marcadores de conflito verificadas. Nenhum comando de banco, migração ou configuração do Supabase foi executado nesta etapa; `.env` permanece fora do Git.
- **O que foi rejeitado ou corrigido:** O push inicial foi recusado porque o remoto continha atualizações da equipe. Foi preservado o histórico remoto em vez de sobrescrevê-lo. A sincronização do código não foi tratada como integração entre as avaliações legadas da API e os candidatos privados do worker; essa conciliação permanece para o próximo PR.

### 09/11/2026 — Leitura limitada e pré-validação de PDF com timeout

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI), PostgreSQL/Auth/Storage locais.
- **O que foi pedido:** Concluir os ajustes e testes restantes da S6-B01, continuar commits na `feat/geminiapi` e manter a nuvem intacta.
- **O que entrou no repositório:** Leitura de no máximo limite + 1 byte, parser em subprocesso descartável com timeout configurável, espera e operações de Storage/banco fora do event loop, testes de limite/travamento/responsividade/privacidade, métricas HTTP desde o upload, contrato de erros e checklist S6-B01 com evidências locais.
- **O que foi verificado:** **129 testes aprovados e um ignorado** (Gemini real, desabilitado nesta execução), incluindo PostgreSQL e transporte HTTP local nas portas 15322/15321. O parser travado foi encerrado sem processo órfão. `/health` respondeu durante validação e Storage bloqueados. Upload de 1,725s e chegada aos candidatos em 9,880s com provedor de referência; dois candidatos, zero eventos antes de revisar e um após confirmação, sem duplicação. Documentação estrita e diff verificados.
- **O que foi rejeitado ou corrigido:** Timeout apenas de thread deixaria o parser continuar; o processo filho é encerrado. O teste inicial de travamento carregava toda a aplicação ao importar seu inspector no Windows, consumindo o prazo antes de chegar à etapa simulada; o inspector passou a um módulo leve e o teste exige comprovação de entrada nessa etapa. `totalDurationMs` começa após a pré-validação; o relatório HTTP passou a registrar também o tempo desde o início do upload. Não houve chamada externa, migração do banco da aplicação, alteração de `.env` ou operação na nuvem.

### 09/11/2026 — Integração HTTP local e preparação da entrega à equipe

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI), Supabase local e Gemini API com PDF inteiramente sintético.
- **O que foi pedido:** Continuar desenvolvendo e testando localmente; levar as migrações ao projeto Supabase preparado por Felipe Couto Duque quando estiver disponível.
- **O que entrou no repositório:** Testes HTTP de Auth/Storage/PostgREST com JWT real, fluxo FastAPI/worker/PostgreSQL, teste de revisão explícita/idempotência, executor restrito à instância local descartável, relatório de métricas sem segredos e orientação de transição para o projeto da equipe.
- **O que foi verificado:** **121 testes passaram, nenhum ignorado**, com uma chamada real ao Gemini somente com PDF sintético. Download público/cruzado e upload em pasta alheia/subpasta/MIME inválido foram negados. Processamento Gemini total de 16,917s, incluindo fila, e última tentativa de 5,340s. O fluxo completo de checagens/revisão levou 20,563s e foi registrado separadamente. Zero eventos antes da revisão e um após confirmação; repetição não duplicou. Contas/objetos de teste foram removidos ao final.
- **O que foi rejeitado ou corrigido:** A aprovação SQL de RLS não foi tratada como aprovação do transporte HTTP. As chaves locais foram lidas do CLI só em memória, sem `.env` nem saída com valores; a suíte rejeita hosts remotos e exige opção explícita para Gemini real. Não houve vínculo/alteração em projeto na nuvem nem migração do banco da aplicação 14322.

### 09/11/2026 — Liberação condicionada à verificação do banco S6-D02

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Verificar o que falta para liberar a integração e rodar PostgreSQL local, mantendo commits na `feat/geminiapi`.
- **O que entrou no repositório:** Checagem de migração/RLS/privilégios/políticas/triggers/RPC/bucket antes de iniciar o worker, comando de auditoria local sem IA, testes de regressão e recuperação nativa com `SKIP LOCKED`/fencing, documentação atualizada para distinguir implementação local de implantação no destino.
- **O que foi verificado:** Suíte completa com **118 testes passando, nenhum ignorado**, incluindo 28 PostgreSQL na instância isolada 15322. O auditor retornou `ready: true` com oito verificações aprovadas nesse banco. Consulta somente de leitura no banco da aplicação 14322 identificou duas migrações pendentes: `20261109120000` e `20261109130000`. Documentação estrita e diff passaram. Não houve chamadas Gemini, habilitação de flags, alteração do banco da aplicação ou implantação remota.
- **O que foi rejeitado ou corrigido:** A flag `SYLLABUS_PRIVACY_READY` sozinha não bastava para detectar banco sem políticas. O worker agora recusa pré-requisitos ausentes, inclusive permissões indevidas por coluna ou RPC/política de Storage exposta a anônimos. A auditoria de metadados foi documentada como complemento, não substituta dos testes comportamentais de RLS.

### 09/11/2026 — Políticas e revisão transacional S6-D02

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Identificar/corrigir as pendências S6-D02, executar PostgreSQL local e continuar commits na `feat/geminiapi`.
- **O que entrou no repositório:** Migração de privacidade de planos, candidatos, avaliações e Storage, proteção de autoria/vínculo, RPC de revisão explícita e atômica, testes reais de acesso/rollback/idempotência/concorrência e guia de operação/contrato S6-B02.
- **O que foi verificado:** 26 testes PostgreSQL passaram em uma instância Supabase isolada na porta 15322, com todas as migrações aplicadas do zero. Testes incluem `anon`, dono, outro usuário, professor/admin, RLS de objetos do Storage, rollback e duas confirmações simultâneas sem duplicação. O banco já existente na porta 14322 foi preservado.
- **O que foi rejeitado ou corrigido:** A leitura pública de avaliações foi removida e a inserção direta de planos pelo cliente foi fechada para impedir metadados forjados. A inicialização ampla foi bloqueada pela revisão automática; a alternativa mais restrita `supabase db start`, somente PostgreSQL isolado, foi aceita. A aprovação local não foi tratada como implantação de políticas no ambiente real; flags continuam desativadas.

### 09/11/2026 — Medição de fila/retentativas e orçamento por modelo

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Continuar o fechamento dos critérios de processamento e registrar commits incrementais.
- **O que entrou no repositório:** `totalDurationMs` na consulta privada, medição de desvios em logs usando o tempo desde o envio, verificação de orçamento antes de reagendar uma falha e exigência de preços explícitos para modelo não padrão.
- **O que foi verificado:** Suíte completa com 88 testes passando e nove PostgreSQL ignorados sem banco local, incluindo espera de 31s na fila com tentativa rápida, preservação do erro de timeout quando o orçamento termina e cálculo de reserva com tarifas específicas do modelo. Documentação estrita, HTML gerado (tabelas/diagrama e parâmetros), diff e ausência de credenciais nos arquivos alterados foram conferidos. Nenhuma chamada ao provedor foi necessária nesta correção.
- **O que foi rejeitado ou corrigido:** Usar apenas a duração da última tentativa ocultava fila/retentativas na meta de 20s. Reagendar sem saldo substituía a causa original por erro genérico; agora a falha é finalizada com a causa correta.

### 09/11/2026 — Prazo total e encerramento de tentativas travadas

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI) e Gemini API com PDFs sintéticos.
- **O que foi pedido:** Retomar a implementação e continuar realizando commits na `feat/geminiapi`.
- **O que entrou no repositório:** Subprocesso por tentativa com prazo total de 18s, limpeza/encerramento após timeout, comunicação JSON validada e sem logs de conteúdo; benchmark atualizado para incluir a criação do subprocesso.
- **O que foi verificado:** Suíte completa com 82 testes passando e nove PostgreSQL ignorados sem banco local, incluindo subprocessos reais travados em Storage/parser/provedor, limpeza sem processos órfãos, exceções sanitizadas e persistência de timeout com tentativas/orçamento limitados. Nova execução Gemini identificou sete candidatos corretos em cinco PDFs sintéticos, sem omissões, extras ou datas inventadas persistidas. O documento de dez páginas levou 5,171s e o caso mais lento 6,933s, incluindo subprocessos. Documentação estrita e verificação do diff passaram.
- **O que foi rejeitado ou corrigido:** Timeout de rede por operação não limitava a leitura do PDF nem a tentativa inteira. A transação da fila permanece no processo pai e somente o trabalho sem banco roda no subprocesso; isso mantém a recuperação por lease e impede que o encerramento deixe uma transação de candidatos incompleta.

### 09/11/2026 — Ambiguidade de horários no extrator Gemini

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI).
- **O que foi pedido:** Continuar a implementação da issue e registrar commits na branch `feat/geminiapi`.
- **O que entrou no repositório:** Validação de horários alternativos/intervalos e horários explicitamente incertos, sem escolher um horário para o estudante; versão do processamento atualizada para `syllabus-v2`.
- **O que foi verificado:** 32 testes do processamento passaram, incluindo nove novos casos de horários; datas válidas permanecem intactas e horários únicos por extenso numérico são preservados.
- **O que foi rejeitado ou corrigido:** A presença de um horário no trecho não bastava quando o mesmo trecho continha outra alternativa. A escolha foi substituída por hora nula com marcação de ambiguidade.

### 09/11/2026 — Processamento de planos particulares com Gemini (S6-B01)

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex (OpenAI) e Gemini API (`gemini-3.5-flash-lite`, somente corpus sintético).
- **O que foi pedido:** Implementar extração de avaliações de PDFs em candidatos estruturados, com processamento persistente fora da requisição, sem criar compromissos.
- **O que entrou no repositório:** Worker SQL com lease/fencing e orçamento acumulado, integração REST Gemini, validação de evidências e datas, modelo ORM de candidatos, migração da fila, metadados no GET privado, corpus e benchmark sintéticos, testes e documentação operacional.
- **O que foi verificado:** 66 testes passaram e nove testes PostgreSQL foram ignorados sem configuração local; chamada real com cinco PDFs sintéticos identificou sete candidatos corretos, sem omissões, extras ou datas inventadas persistidas. Documento de dez páginas com conteúdo adicional concluiu em 4,143s; nenhum caso excedeu 20s. `mkdocs build --strict` e `git diff --check` passaram. Logs/erros próprios foram revisados para não registrar texto integral, respostas brutas ou credenciais. Worker desativado por padrão; nenhum PDF real, migração remota ou deploy foi realizado.
- **O que foi rejeitado ou corrigido:** O Gemini rejeitou o primeiro esquema JSON por complexidade; o esquema enviado foi simplificado, mantendo validação local completa. A avaliação passou a associar título literal com sufixo e página para não contar variações válidas como datas inventadas. O teste de upload foi isolado do Supabase configurado no `.env`. A S6-D02 não foi presumida pronta: integração real e homologação de RLS/PostgreSQL continuam pendentes.


### 10/11/2026 — Conciliação da extração com a `dev`

- **Quem:** Heitor Gomes Monteiro (solicitante).
- **Ferramenta:** Codex, testes Python/Playwright e Supabase local.
- **O que foi pedido:** Atualizar `feat/geminiapi` contra a base `dev`, resolver conflitos e corrigir incompatibilidades, continuando os commits sem alterar a nuvem.
- **O que entrou:** Merge da base `3922797`, documentação nos diretórios oficiais, migrações inéditas sem números duplicados e extrator na tabela oficial `avaliacoes`, com versão privada fixada, datas civis separadas, proveniência e preservação de versões compartilhadas. Retry particular não recria evento apagado.
- **Verificado:** 191 testes de backend aprovados e um ignorado no ambiente local, 17 testes de lógica, 38 de navegador, build frontend/documentação e lint SQL sem achados. Corpus de referência: sete acertos e nenhuma data inventada. Nenhuma chamada Gemini nova ou alteração no Supabase hospedado nesta revisão.
- **Corrigido/rejeitado:** Manter duas tabelas de candidatos contrariaria S7-D01. Políticas de compartilhamento não foram apagadas para impor privacidade indiscriminada; o texto aprovado permanece privado. A fila S7-B02 não foi ativada como segundo executor. Produção, revisão humana e integrações dependentes continuam pendentes.

### 10/11/2026 — Integração de catálogo e seleção de ofertas (#70/#71)

- **Solicitante:** Thomas. **Ferramenta:** Codex.
- **Pedido:** testar implementações da API do Followw.
- **Verificações:** testes automatizados HTTP, adaptador, PostgreSQL isolado e Playwright; build frontend; migrações na atualização e em base sem tabelas da aplicação. Sondagem pública pequena retornou 211 unidades e duas ofertas de FGA0108/2026.2, ambas com ID inequívoco. Detalhes e limitações em `docs/arquitetura/catalogo-de-turmas.md`.
- **Limites:** sem deploy, escrita no Supabase hospedado, varredura integral, mensagens em issues ou fechamento de issues. Revisor humano e homologação ainda pendentes.

### 13/11/2026 — SEO do Agenda UnB

- **Solicitante:** Thomas. **Ferramenta:** Codex.
- **Pedido:** melhorar a descoberta do site pelo Google e abrir um PR para a `dev`.
- **O que entrou:** HTML e metadados para páginas públicas, guias com fontes oficiais da UnB, sitemap de eventos aprovados e regras de indexação.
- **Verificações:** build e 25 testes do frontend, HTTP local dos guias e testes da função com respostas simuladas do Supabase. A validação do roteamento e do cache na Vercel fica para a homologação.
- **Decisão:** a marcação estruturada de eventos depende de endereços completos no catálogo. As páginas públicas usam o campo de local disponível e não inferem um endereço.

### 18/11/2026 — Lembretes persistentes (#81)

- **Ferramenta** — Codex, com pytest, Supabase local e Chromium.
- **Pedido** — Concluir o job, os contratos e a central de lembretes em commits separados.
- **Entrega** — Migração incremental para a corrida de reagendamento, SQL de ativação do Supabase Cron, rotas autenticadas e estados de leitura no sino.
- **Verificação** — Testes SQL e HTTP, reinício do banco com job real e retorno à sessão no navegador com duas contas sintéticas. [Evidências locais e pendências](/arquitetura/dados-de-eventos#aceite-local-da-s8-b03).
