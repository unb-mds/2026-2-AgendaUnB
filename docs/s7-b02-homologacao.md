# Roteiro de homologação da S7-B02

Use este roteiro para registrar as provas pendentes da [issue #68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68). O [PR #116](https://github.com/unb-mds/2026-2-AgendaUnB/pull/116) registra a migração e a preparação do ambiente. Os resultados abaixo distinguem as verificações já executadas das provas ainda previstas.

## Acessos para alinhar com Thomas

| Prova | Acesso e preparação |
| --- | --- |
| Google Calendar | Responsável pelo projeto Google Cloud que possa habilitar a Calendar API, cadastrar o callback e incluir uma conta Google de teste. Backend de homologação com o código e a migração do [#110](https://github.com/unb-mds/2026-2-AgendaUnB/pull/110). A pessoa que controla a conta de teste faz o consentimento. |
| SMTP | Responsável pelo Supabase Auth de homologação e pelo provedor SMTP. Uma caixa de teste cujo endereço esteja fora da equipe do projeto Supabase, com alguém disponível para abrir os links recebidos. |
| Retomada | Runner ou serviço de homologação com permissão para iniciar e interromper o worker e ler logs. Banco Supabase persistente e isolado, com permissão de leitura dos estados do plano. Confirmar a revisão do código, o mecanismo de disparo e os limites do plano de hospedagem. |
| Gemini | Responsável pelo projeto Google AI que possa conferir o tier e as cotas do modelo no AI Studio. Decisão da equipe sobre elegibilidade do público e tratamento de conteúdo antes de habilitar o provedor para usuários. |

Registre o commit implantado, as URLs da API e do frontend de homologação e o projeto Supabase correspondente. O responsável por cada serviço pode cadastrar os segredos diretamente no painel. Use contas, eventos e planos sintéticos. Nos registros compartilhados, use identificadores de teste e remova tokens, códigos OAuth, links de e-mail e credenciais.

## Google Calendar

1. Habilite a Calendar API no projeto Google de homologação. Confirme o estado do aplicativo na tela de consentimento, as contas de teste, as cotas do projeto e os requisitos de publicação. Cadastre o callback HTTPS exato em `GOOGLE_CALENDAR_REDIRECT_URI`, com o caminho `/api/v1/me/google-calendar/callback`. Configure `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET`, `GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI` e `GOOGLE_TOKEN_ENCRYPTION_KEY` no backend. Aplique em homologação a migração `20261111150000_s7_f04_auth_calendar_connection.sql` antes do teste da API.
2. Entre na Agenda UnB com uma conta confirmada que tenha o mesmo e-mail verificado no Google. Com a sessão dessa conta, inicie `POST /api/v1/me/google-calendar/authorization` e abra a URL recebida no navegador. Após consentir, confira o retorno `google_calendar=connected`. Consulte `GET /api/v1/me/google-calendar/connection` e verifique `connected: true` e o escopo `https://www.googleapis.com/auth/calendar.app.created`.
3. Em uma execução de teste no servidor, use o helper `get_access_token` do #110 e o escopo concedido para chamar `calendars.insert` e criar uma agenda secundária sintética. Com o ID retornado, chame `events.insert` com um evento de teste e confirme sua presença no Google Calendar. Guarde os códigos HTTP e os identificadores de teste. O #110 oferece as rotas de conexão. A prova de escrita é feita com as chamadas da Calendar API, pois a jornada de exportação está na [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82). [Criar agenda](https://developers.google.com/workspace/calendar/api/v3/reference/calendars/insert) · [Criar evento](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert)
4. Após o token expirar, repita uma consulta à agenda usando `get_access_token` e confira que a validade registrada avançou e que a chamada funcionou. Limpe o evento e a agenda sintéticos antes de desconectar. Chame `DELETE /api/v1/me/google-calendar/connection`, verifique `revocation: confirmed` e confirme `connected: false` na consulta seguinte. Se a revogação ficar sem confirmação, registre a falha e verifique a remoção do acesso pelo painel da conta Google de teste.

**Evidência esperada.** SHA implantado, escopo concedido, resultado da conexão, criação da agenda e do evento, renovação e revogação, mais as cotas e condições de publicação. A última evidência hospedada registrou HTTP `404` para o endpoint de Calendar. [Contrato do #110](https://github.com/unb-mds/2026-2-AgendaUnB/pull/110) · [Verificação publicada da #76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76#issuecomment-6837018351)

## SMTP externo no Supabase

1. Confirme o SMTP personalizado, o remetente e as URLs permitidas de retorno em Auth no Supabase de homologação. Use a origem HTTPS do frontend de teste e a rota de redefinição que existir na versão implantada. Registre o provedor, os limites do plano e a data do teste. [Configurar SMTP](https://supabase.com/docs/guides/auth/auth-smtp)
2. Cadastre uma conta sintética com endereço fora da equipe Supabase. Anote o horário do pedido e do recebimento. Abra o link de confirmação, confira o retorno ao frontend de homologação e verifique que a conta confirmada consegue iniciar sessão.
3. Solicite recuperação de senha pela interface implantada. Se a interface ainda estiver pendente, isole a prova de entrega usando `supabase.auth.resetPasswordForEmail` no cliente de homologação. Abra o link recebido, defina uma nova senha no fluxo de recuperação e confirme um novo login. Se o teste tiver usado o SDK, registre separadamente a pendência da interface. [Solicitar recuperação com o SDK](https://supabase.com/docs/reference/javascript/auth-resetpasswordforemail)
4. Para cada mensagem, registre o tempo observado, se chegou à caixa de entrada ou ao spam, a origem de retorno e o resultado de confirmação ou recuperação. Se falhar, anote o erro sanitizado dos logs do Supabase ou do provedor SMTP.

**Evidência esperada.** Os dois e-mails chegam à caixa externa e os links concluem confirmação e redefinição em homologação. A evidência atual da #76 cobre o início do login Google. Os dois envios SMTP ainda estão pendentes.

## Retomada dos jobs na hospedagem

1. Defina o candidato e registre onde rodam API, worker, coletor e scheduler. O [#113](https://github.com/unb-mds/2026-2-AgendaUnB/pull/113) propõe FastAPI no Render Free e jobs no GitHub Actions. O workflow dessa proposta exige `main` e usa `production-jobs`. Para a prova, combine uma execução manual equivalente com segredos e banco próprios de homologação. Registre o runner, a cadência, o tempo e o custo observados.
2. Prepare um único plano sintético. Se o provedor estiver habilitado em homologação, autorize o texto pela jornada de planos. Se a autorização ainda estiver bloqueada pela validação do provedor, prepare a tarefa por uma fixture de teste no banco isolado. Use como referência `approved_source` e a fixture `job` de `backend/tests/test_syllabus_processing.py`. Confira que o plano está `pendente`, com texto autorizado, e registre sua execução inicial. Confirme que restam pelo menos duas tentativas e orçamento para duas reservas. O lease é registrado em `planos_ensino`, com expiração padrão de 90 segundos.
3. Inicie a execução A. Observe `processando`, a tentativa incrementada e a reserva no banco. Interrompa o processo depois da aquisição do lease e antes da gravação dos candidatos. Se a extração terminar antes do cancelamento, repita com um novo plano e uma execução de teste que pause o `runner` logo após a aquisição, usando o ponto de injeção de `SyllabusWorker` apenas no ambiente de teste. Registre se o provedor foi simulado ou real. O cenário só vale como interrupção se o plano ficar `processando` com lease persistido após a saída do processo.
4. Aguarde o lease expirar e inicie a execução B no mesmo banco. Confira que ela assumiu o mesmo plano com uma nova tentativa e preservou a reserva anterior. Ao terminar, verifique `concluido`, a ausência de candidatos duplicados e a ausência de compromissos criados automaticamente. Para o provedor real, use `python -m src.modules.syllabus.worker --once` na pasta `backend`, com as verificações de privacidade e elegibilidade concluídas. Para o ensaio simulado, execute `SyllabusWorker.run_once()` com o provedor de teste da fixture. Registre a recuperação simulada e a chamada real do Gemini como provas distintas.
5. Use os testes existentes como evidência complementar de `429`, timeout, lease expirado e limite de tentativas. Na prova hospedada, registre IDs das duas execuções, horários, estados, tentativas, reservas e quantidade final de candidatos. Separe a reserva interna da cobrança ou do consumo efetivo dos planos de hospedagem e do Gemini.

**Evidência esperada.** Dois processos distintos usam o mesmo banco persistente, a execução A é interrompida com a tarefa assumida e a execução B conclui essa tarefa após a expiração do lease. Os 92 testes de 13/11 verificaram a recuperação local, incluindo concorrência e proteção contra finalização com lease antigo.

## Evidências já reunidas

| Prova | Resultado verificado | Limite |
| --- | --- | --- |
| Followw | Cinco consultas públicas em 13/11 retornaram HTTP 200. Foram observadas 211 unidades, 2 ofertas e 1 disciplina por código, e 229 ofertas e 304 disciplinas na unidade 673. A issue registra a paginação observada e o limite documentado. | Amostra no período `2026.2`. A varredura integral do catálogo é outra validação. |
| Gemini | Cinco PDFs sintéticos com `gemini-3.5-flash-lite` produziram sete candidatos corretos. Maior duração medida de 13,511 s. [Benchmark](benchmarks/syllabus-s7-gemini-2026-11-10.json) | Ainda faltam tier, RPM, TPM e RPD do projeto e a avaliação de elegibilidade. [Cotas](https://ai.google.dev/gemini-api/docs/rate-limits) · [Termos](https://ai.google.dev/gemini-api/terms) |
| Base existente | Em 10/11, a nuvem passou de 21 para 26 migrações. Em 13/11, a cópia local passou de 26 para 28, com campi e categorias preservados. [Registro da migração](supabase-nuvem-2026-11-10.md) | A consulta ao histórico remoto de 13/11 falhou na conexão. O estado remoto das duas migrações de catálogo precisa ser conferido. |
| Base limpa e CI | O #113 registra aplicação das 28 migrações do zero e lint aprovado. Os dois workflows do candidato `9bdb963` passaram. [CI Supabase](https://github.com/unb-mds/2026-2-AgendaUnB/actions/runs/43319542306) · [CI Application](https://github.com/unb-mds/2026-2-AgendaUnB/actions/runs/43319542392) | Os resultados descrevem o candidato testado. |
| Retomada, `429` e timeout | 92 testes passaram em `8d437ef`, incluindo PostgreSQL local, lease expirado e limites de tentativas. | Falta o ensaio em dois processos na hospedagem candidata. |

O [registro na #68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68) contém o comando da suíte local e os resultados da sondagem Followw.

## Registro de cada execução

Copie para a #68 ao concluir uma prova. Em caso de bloqueio, registre o impedimento, a alternativa escolhida pela equipe e quem pode confirmá-la.

```text
Prova e data:
Ambiente e SHA implantado:
Configuração ou comando reproduzível, sem segredos:
Resultado observado e link da evidência:
Limites, custo medido e pendências aplicáveis:
Pessoa responsável pela execução:
Revisor humano e resultado da revisão:
```

O PR #116 segue o checklist da #68 para passar a pronto para revisão. Além das provas, registre as cotas e a decisão de elegibilidade do Gemini, a versão implantada e a revisão humana.
