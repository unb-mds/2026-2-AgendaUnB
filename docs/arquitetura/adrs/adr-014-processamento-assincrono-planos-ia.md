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

2. **Isolamento em subprocesso `spawn` e limites operacionais:**
   - Cada tentativa executa em subprocesso `spawn` descartável com prazo total padrão de 18 segundos (`SYLLABUS_ATTEMPT_TIMEOUT_SECONDS`, incluindo rede e validação, com até 2,2 segundos de limpeza), timeout de rede de 12 segundos (`SYLLABUS_AI_TIMEOUT_SECONDS`) e máximo de 2 tentativas (`SYLLABUS_MAX_ATTEMPTS`), sempre inferior ao lease de 90 segundos.
   - Apenas JSON validado ou código de erro fixo cruza o pipe do subprocesso. Respostas `429` (com backoff de `SYLLABUS_RATE_LIMIT_DELAY_SECONDS = 65`), `5xx` selecionados, timeout e falha de conexão permitem nova tentativa limitada; erros de autenticação, resposta malformada ou evidência inválida encerram em `falha` sem persistência parcial.

3. **Provedor, orçamento, deduplicação e reprocessamento controlado:**
   - Utiliza Google Gemini (`gemini-3.5-flash-lite`) via REST Interactions API (`v1beta`, `store=false`), sem ferramentas, busca, cache compartilhado, uploads remotos ou fallback silencioso de modelo. No modo `--drain`, aplica cadência mínima (`SYLLABUS_MIN_INTERVAL_SECONDS = 4.0`) entre chamadas externas para respeitar 15 RPM.
   - Antes de acionar o provedor externo, o worker procura um plano `concluido` com a mesma versão de processamento (`syllabus-v8-catalog-titles`), o mesmo ano e nome de disciplina registrados no envio e o mesmo `hash_texto_aprovado` (SHA-256 do texto autorizado). Quando encontra, clona os candidatos validados para a nova versão privada e devolve a reserva da tentativa.
   - Antes de cada tentativa, calcula e reserva orçamento conservador por bytes de entrada (40.000 bytes de texto + 16.000 bytes de margem para instrução e esquema) e tokens de saída (4.096), respeitando teto por plano (`SYLLABUS_MAX_FILE_COST_USD = 0.06`; reserva padrão `USD 0,027040` por tentativa). Alterar `GEMINI_MODEL` exige configurar explicitamente `GEMINI_INPUT_USD_PER_MILLION` e `GEMINI_OUTPUT_USD_PER_MILLION`.
   - Reprocessar um plano finalizado exige `reprocess: true` e nova autorização (`POST /api/v1/syllabus/{id}/extractions`), preserva versões compartilhadas e candidatos confirmados, descarta pendentes de versões privadas anteriores e mantém acumulados os contadores de tentativas e orçamento (`409` ao esgotar limites, oferecendo cadastro manual).

4. **Validação estrita e proteção contra prompt injection:**
   - O conteúdo do plano segue como dados JSON, separado da instrução de sistema. O servidor valida o esquema da resposta e verifica trecho, título, data e hora na evidência. A validação do título aceita acentos restaurados e a numeração de rótulos genéricos quando o trecho contém uma avaliação do tipo correspondente.
   - Quando o provedor altera acentos, a validação pode recuperar o trecho contínuo da página original por equivalência de caracteres. A data e a hora continuam sujeitas à validação na evidência recuperada.
   - Para um plano com disciplina identificada no texto, o servidor preserva o rótulo da avaliação e acrescenta uma sigla. A sigla usa o nome registrado da disciplina da turma vinculada, quando disponível. Sem esse nome, o servidor mantém a sigla explícita do plano ou usa as iniciais das palavras principais e os números do nome. Se uma prova tem data confiável e não informa hora, o servidor usa o início do bloco de aulas no dia correspondente quando a grade SIGAA do documento resolve o horário. Horários explícitos da avaliação têm prioridade e conflitos exigem revisão.
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
