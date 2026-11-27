---
title: "ADR-014 · Processamento assíncrono resiliente de planos com fila persistida, lease e orçamento"
description: "Decisão arquitetural do worker de extração de planos de ensino via IA: fila persistida em planos_ensino, lease com fencing, subprocessos isolados, orçamento controlado e validação estrita."
---

# ADR-014 · Processamento assíncrono resiliente de planos com fila persistida, lease e orçamento

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-15 |
| Rastreabilidade | RF06; RNF02, RNF06, RNF10, RNF13 |
| Substitui | Nenhuma ADR |

## Contexto

A extração de datas de provas e trabalhos por LLM (Google Gemini) é uma operação sujeita a latência externa, rate limits (`429`), timeouts e interrupções de processo. Executá-la na requisição HTTP ou em `BackgroundTasks` em memória perderia tarefas em reinícios e bloquearia a API. Além disso, o texto do plano é entrada não confiável (risco de *prompt injection*), o plano gratuito do provedor possui cotas rígidas e o custo por arquivo exige teto previsível.

## Decisão

1. **Fila persistida com lease temporal e fencing:**
   - A própria tabela `planos_ensino` atua como fila persistida (ordenada por `enfileirado_em`), sem despacho duplicado em `BackgroundTasks` nem tabela de fila paralela. O worker reivindica apenas linhas com autorização explícita e snapshot aprovado ([ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos)).
   - Em PostgreSQL, usa `FOR UPDATE SKIP LOCKED`, incrementa `execucao_atual`, reserva orçamento e grava `processando` com um UUID `token_processamento` (*fencing*) e lease de 90 segundos. Um processo antigo que perca o lease não consegue finalizar a linha após outro worker assumi-la.
   - O worker executa em processo independente (`python -m src.modules.syllabus.worker --drain --max-items 25`), disparado sob demanda após autorização e como rede de segurança agendada em `.github/workflows/production-jobs.yml`, sem compartilhamento de memória com a API.

2. **Execução com deadline real e limites operacionais:**
   - Como o worker já roda em processo independente da API (via `subprocess.Popen` ou GitHub Actions) e processa apenas snapshots JSON já aprovados, cada tentativa executa no próprio processo do worker com deadline em thread daemon (`run_in_worker`, mantendo `run_isolated` para isolamento de parser PDF quando necessário), evitando o overhead de duplo `spawn`. O prazo total padrão da tentativa é de 35 segundos (`SYLLABUS_ATTEMPT_TIMEOUT_SECONDS`), timeout HTTP de 25 segundos (`SYLLABUS_AI_TIMEOUT_SECONDS`), até 3 tentativas (`SYLLABUS_MAX_ATTEMPTS`, configurável até 5) e intervalo base de retentativa de 4 segundos (`SYLLABUS_RETRY_DELAY_SECONDS`, com backoff progressivo até 15 segundos), sempre inferior ao lease de 90 segundos.
   - No modo `--drain`, quando um erro transitório reagenda uma retentativa curta (até 15 segundos), o loop aguarda o intervalo antes de encerrar, evitando depender do polling da interface para re-spawnar o worker. Respostas `429` (com backoff de `SYLLABUS_RATE_LIMIT_DELAY_SECONDS = 65`), `5xx` selecionados, timeout e falha de conexão permitem nova tentativa limitada; erros de autenticação, resposta malformada ou evidência inválida encerram em `falha` sem persistência parcial.

3. **Provedor, orçamento, deduplicação e reprocessamento controlado:**
   - Utiliza Google Gemini (`gemini-3.5-flash-lite`) via REST `v1beta/models/{model}:generateContent` com `responseJsonSchema`, sem ferramentas, busca, cache compartilhado, uploads remotos ou fallback silencioso de modelo, removendo caracteres de controle ASCII inválidos da resposta JSON. No modo `--drain`, aplica cadência mínima (`SYLLABUS_MIN_INTERVAL_SECONDS = 4.0`) entre chamadas externas para respeitar 15 RPM.
   - Antes de acionar o provedor externo, o worker procura um plano `concluido` com a mesma versão de processamento (`syllabus-v9-dated-exam-rows`), o mesmo ano, disciplina, horário da oferta vinculada e o mesmo `hash_texto_aprovado` (SHA-256 do texto autorizado). Quando encontra, clona os candidatos validados para a nova versão privada e devolve a reserva da tentativa.
   - Antes de cada tentativa, calcula e reserva orçamento conservador por bytes de entrada (40.000 bytes de texto + 16.000 bytes de margem para instrução e esquema) e tokens de saída (4.096), respeitando teto por plano (`SYLLABUS_MAX_FILE_COST_USD = 0.12`; reserva padrão `USD 0,027040` por tentativa). Alterar `GEMINI_MODEL` exige configurar explicitamente `GEMINI_INPUT_USD_PER_MILLION` e `GEMINI_OUTPUT_USD_PER_MILLION`.
   - Utiliza Google Gemini (`gemini-3.5-flash-lite`) via REST `v1beta/models/{model}:generateContent` com `responseJsonSchema`, sem ferramentas, busca, cache compartilhado ou uploads remotos, removendo caracteres de controle ASCII inválidos da resposta JSON. No modo `--drain`, aplica cadência mínima (`SYLLABUS_MIN_INTERVAL_SECONDS = 4.0`) entre chamadas externas para respeitar 15 RPM.
   - Opcionalmente, um fallback explícito pode usar Groq (`llama-3.3-70b-versatile`), OpenRouter (`openrouter/free` ou sufixo `:free`) ou Mistral (`mistral-small-latest`) via endpoints HTTPS fixos e payload OpenAI-compatible sem `store` nem `tools`. O fallback fica desativado sem configuração explícita e chave no servidor; somente uma falha remota do Gemini ou uma resposta que não passe pelo schema/validação aciona a contingência. Sucesso do Gemini, inclusive zero candidatos, ausência de termos e limites locais não acionam fallback. O mesmo snapshot aprovado e as validações da disciplina/oferta se aplicam aos dois provedores.
   - A chamada secundária precisa caber no prazo restante da tentativa (com pelo menos 2s disponíveis); redirecionamentos HTTP e URLs arbitrárias são bloqueados. Provedor, modelo e uso do fallback são persistidos em `planos_ensino`/`avaliacoes` e registrados em logs estruturados, sem texto nem chaves. O texto autorizado também será enviado ao provedor de contingência configurado, então os termos e a elegibilidade do provedor escolhido precisam ser verificados antes de habilitar a chave.
   - Antes de acionar o provedor externo, o worker procura um plano `concluido` com a mesma versão de processamento (`syllabus-v9-dated-exam-rows`), o mesmo ano, disciplina, horário da oferta vinculada e o mesmo `hash_texto_aprovado` (SHA-256 do texto autorizado). Quando encontra, clona os candidatos validados para a nova versão privada e devolve a reserva da tentativa.
   - Antes de cada tentativa, calcula e reserva orçamento conservador por bytes de entrada (40.000 bytes de texto + 16.000 bytes de margem para instrução e esquema) e tokens de saída (4.096), respeitando teto por plano (`SYLLABUS_MAX_FILE_COST_USD = 0.12`; reserva padrão `USD 0,027040` por tentativa). Modelos Gemini com preço alterado exigem configurar explicitamente os dois preços por milhão de tokens. A tentativa concluída pelo tier gratuito de fallback devolve a reserva da chamada Gemini.
   - Reprocessar um plano finalizado exige `reprocess: true` e nova autorização (`POST /api/v1/syllabus/{id}/extractions`), preserva versões compartilhadas e candidatos confirmados, descarta pendentes de versões privadas anteriores e mantém acumulados os contadores de tentativas e orçamento (`409` ao esgotar limites, oferecendo cadastro manual).

4. **Validação estrita e proteção contra prompt injection:**
   - O conteúdo do plano segue como dados JSON, separado da instrução de sistema. O servidor valida o esquema da resposta e verifica trecho, título, data e hora na evidência. A validação do título aceita acentos restaurados e a numeração de rótulos genéricos quando o trecho contém uma avaliação do tipo correspondente.
   - Quando o provedor altera acentos ou junta ordinais quebrados por espaços/quebras de linha no PDF (ex.: `1\na\n Avaliação`), a validação pode recuperar o trecho contínuo da página original por equivalência de caracteres, inclusive com acentos separados ao copiar texto de PDF. Linhas explícitas de provas com data numérica e dia da semana também podem ser recuperadas diretamente do cronograma. O servidor usa o ano da oferta ou do plano e só sugere uma data quando ela coincide com o dia informado.
   - Para um plano com disciplina identificada no texto ou na oferta vinculada (`ofertas_turma` / `disciplinas.nome` como fallback), o servidor preserva o rótulo da avaliação e acrescenta uma sigla. A sigla usa o nome registrado da disciplina da turma vinculada, quando disponível. Sem esse nome, o servidor mantém a sigla explícita do plano ou usa as iniciais das palavras principais e os números do nome. Se uma prova tem data confiável e não informa hora, o servidor usa o início do bloco de aulas no dia correspondente a partir da grade SIGAA do documento ou, como fallback, da coluna `ofertas_turma.horarios` da oferta vinculada. Horários explícitos da avaliação têm prioridade e conflitos exigem revisão.
   - Não se inferem meia-noite, fuso horário ou início de intervalo a partir do relógio do servidor. Datas com ano abreviado (`DD/MM/AA`) ou `DD/MM` com ano explícito no plano ou na oferta vinculada resolvem o ano de referência; datas sem referência de ano ou ambíguas permanecem nulas e marcadas para correção humana. Documentos sem avaliações concluem com zero candidatos sem gerar erro.

5. **Gates operacionais e verificação de pré-requisitos:**
   - A execução do provedor exige três flags explícitas em `true` no runtime do servidor: `SYLLABUS_WORKER_ENABLED`, `SYLLABUS_PRIVACY_READY` e `SYLLABUS_PROVIDER_TERMS_READY`.
   - Na inicialização (e via `backend/scripts/check_syllabus_privacy.py`), o worker verifica catálogos do PostgreSQL (migrações, RLS, privilégios, políticas de leitura do dono, triggers de autoria/vínculo/snapshot e bucket fechado) e recusa iniciar se qualquer pré-requisito estiver ausente.

## Alternativas para comparação

Processar em `BackgroundTasks` na API perderia jobs durante spin-down ou reinício do container. Enviar o PDF inteiro ou usar um SDK com ferramentas habilitadas aumentaria superfície de dados e risco de execução indevida pelo modelo. Manter uma segunda tabela de fila duplicaria despacho e controle de concorrência.

## Consequências

A retomada após falha ou timeout pode incorrer em nova chamada ao provedor dentro do limite de tentativas, motivo pelo qual a reserva de orçamento permanece consumida mesmo em falha ou timeout. A fila de processamento opera exclusivamente sobre o estado e o lease de `planos_ensino`.

## Orientações para contribuição e verificação

- Executar `backend/scripts/check_syllabus_privacy.py` e os testes em PostgreSQL local (`TEST_SUPABASE_DB_URL` restrito a `localhost`/`127.0.0.1`) ao alterar políticas, triggers ou consultas do worker.
- Validar cenários de lease expirado, fencing de execução antiga, `429`/timeout, teto de orçamento, rejeição de datas inventadas/instruções maliciosas e ausência de dados sensíveis em logs (`test_syllabus_processing.py`, `test_syllabus_database.py`).
- Para medição controlada de corpus sintético sem alterar produção, utilizar `backend/scripts/benchmark_syllabus.py`.

## Fontes e relações

[ADR-002](/arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes) · [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos) · [ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos) · [Dados de planos](/arquitetura/dados-de-planos) · [Contratos da API](/api-specs) · [Índice de ADRs](/arquitetura/adrs/index)
