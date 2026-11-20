---
title: "ADR-014 · Processamento assíncrono resiliente de planos com fila persistida, lease e orçamento"
description: "Decisão arquitetural do worker de extração de planos de ensino via IA: fila persistida em planos_ensino, lease com fencing, subprocessos isolados, orçamento controlado e validação estrita."
---

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-15 |
| Rastreabilidade | RF06; RNF02, RNF06, RNF10, RNF13 |
| Substitui | Nenhuma ADR |

Decisão implementada em `backend/src/modules/syllabus/` (`worker.py`, `processing_config.py`, `privacy.py`), `backend/scripts/check_syllabus_privacy.py`, `.github/workflows/production-jobs.yml` e nas migrações `20261109110000` e `20261110120000`. A execução externa do provedor permanece desativada por padrão até habilitação explícita das flags operacionais.

## Contexto

A extração de datas de provas e trabalhos por LLM (Google Gemini) é uma operação sujeita a latência externa, rate limits (`429`), timeouts e interrupções de processo (especialmente em runners efêmeros ou hospedagem gratuita). Executá-la na requisição HTTP ou em `BackgroundTasks` em memória perderia tarefas em reinícios e bloquearia a API. Além disso, o texto do plano é dado não confiável (risco de prompt injection), o tier gratuito do provedor possui cotas rígidas e o custo por arquivo precisa de teto previsível.

## Decisão

1. **Fila persistida com lease temporal e fencing:**
   - A própria tabela `planos_ensino` atua como fila persistida (ordenada por `enfileirado_em`), sem despacho duplicado em `BackgroundTasks`. O worker reivindica apenas linhas com autorização explícita e snapshot aprovado (`ADR-003`).
   - Em PostgreSQL, usa `FOR UPDATE SKIP LOCKED`, incrementa `execucao_atual`, reserva orçamento e grava `processando` com um UUID `token_processamento` (fencing) e lease de 90 segundos. Um processo antigo que perca o lease não consegue finalizar a linha após outro worker assumi-la.
   - O worker executa em processo independente (`python -m src.modules.syllabus.worker --drain --max-items 25` disparado sob demanda pela API após autorização e como rede de segurança agendada em `.github/workflows/production-jobs.yml`), sem compartilhamento de memória com a API.

2. **Isolamento em subprocesso `spawn` e limites operacionais:**
   - Cada tentativa executa em subprocesso `spawn` descartável com prazo total padrão de 18s (`SYLLABUS_ATTEMPT_TIMEOUT_SECONDS`, incluindo rede e validação, com até 2,2s de limpeza), timeout de rede de 12s (`SYLLABUS_AI_TIMEOUT_SECONDS`) e máximo de 2 tentativas (`SYLLABUS_MAX_ATTEMPTS`), sempre inferior ao lease de 90s.
   - Apenas JSON validado ou código de erro fixo cruza o pipe do subprocesso. `429` (com backoff dedicado de `SYLLABUS_RATE_LIMIT_DELAY_SECONDS=65`), `5xx` selecionados, timeout e falha de conexão permitem nova tentativa limitada; erros de autenticação, resposta malformada ou evidência inválida encerram em `falha` sem persistência parcial.

3. **Provedor, orçamento, deduplicação e reprocessamento controlado:**
   - Utiliza Google Gemini (`gemini-3.5-flash-lite`, Free Tier 15 RPM / 1M TPM / 1.500 RPD) via REST Interactions API (`v1beta`, `store=false`), sem ferramentas, busca, cache compartilhado, uploads remotos ou fallback silencioso de modelo. No modo `--drain`, aplica cadência mínima (`SYLLABUS_MIN_INTERVAL_SECONDS=4.0`) entre chamadas externas para respeitar 15 RPM.
   - Antes de acionar o provedor externo, o worker verifica se já existe plano `concluido` na mesma versão de processamento (`syllabus-v3-approved-text`) com exatamente o mesmo `approved_hash` (SHA-256 canônico do texto aprovado). Em caso positivo, clona os candidatos validados para a nova versão privada sem chamar o Gemini e estorna a reserva da tentativa, reduzindo chamadas redundantes no Free Tier sem expor textos entre contas.
   - Antes de cada tentativa, calcula e reserva orçamento conservador por bytes de entrada (`40.000` bytes de texto + `16.000` bytes de margem para instrução/esquema) e tokens de saída (`4.096`), respeitando teto por plano (`SYLLABUS_MAX_FILE_COST_USD = 0.06`; reserva padrão `USD 0,027040` por tentativa). Alterar `GEMINI_MODEL` exige configurar explicitamente `GEMINI_INPUT_USD_PER_MILLION` e `GEMINI_OUTPUT_USD_PER_MILLION`.
   - Reprocessar um plano finalizado exige `reprocess: true` e nova autorização (`POST /api/v1/syllabus/{id}/extractions`), preserva versões compartilhadas e candidatos confirmados, descarta pendentes de versões privadas anteriores e mantém acumulados os contadores de tentativas e orçamento (`409` ao esgotar limites, oferecendo cadastro manual).

4. **Validação estrita e proteção contra prompt injection:**
   - O conteúdo do plano é enviado isolado como dados JSON não confiáveis, separado da instrução de sistema. O servidor valida a resposta com Pydantic rejeitando campos extras, tipos fora de `prova`/`trabalho`, citações ausentes na página indicada e datas sem evidência completa no trecho.
   - Não se inferem meia-noite, fuso horário ou início de intervalo a partir do relógio do servidor. Datas com ano abreviado (`DD/MM/AA`) ou `DD/MM` com ano explícito no plano (ex.: `2026/2`) ou na oferta vinculada resolvem o ano de referência; datas sem referência de ano no documento/oferta ou ambíguas permanecem nulas e marcadas para correção humana. Documentos sem avaliações concluem com zero candidatos sem gerar erro.

5. **Gates operacionais e verificação de pré-requisitos:**
   - A execução do provedor exige três flags explícitas em `true` no runtime do servidor: `SYLLABUS_WORKER_ENABLED`, `SYLLABUS_PRIVACY_READY` e `SYLLABUS_PROVIDER_TERMS_READY`.
   - Na inicialização (e via `backend/scripts/check_syllabus_privacy.py`), o worker verifica catálogos do PostgreSQL (migrações, RLS, privilégios, políticas de leitura do dono, triggers de autoria/vínculo/snapshot e bucket fechado) e recusa iniciar se qualquer pré-requisito estiver ausente.

## Alternativas para comparação

Processar em `BackgroundTasks` na API perderia jobs durante spin-down ou reinício do container. Enviar o PDF inteiro ou usar um SDK com ferramentas habilitadas aumentaria superfície de dados e risco de execução indevida pelo modelo. Usar uma segunda fila paralela para o mesmo fluxo duplicaria despacho e controle de concorrência.

## Consequências

- A retomada após falha ou timeout pode incorrer em nova chamada ao provedor dentro do limite de tentativas (sem garantia de entrega exatamente-uma-vez externa), motivo pelo qual a reserva de orçamento permanece consumida mesmo em falha/timeout.
- **Débito técnico registrado:** a tabela `fila_processamento_ia` (`20261109185725_cria_fila_processamento_ia.sql`) não é consumida pelo worker atual (que utiliza `planos_ensino`). Sua política de consulta referencia `professor_id` e precisa ser alinhada ao contrato de propriedade por `user_id` antes de qualquer exposição ou adoção como endpoint de status de planos particulares.
- Medições locais no corpus sintético mantiveram o fluxo de fila + provedor abaixo da meta de 20s (RNF06), descontando preparação e revisão humana; esses resultados sintéticos não substituem homologação de latência e carga no ambiente publicado.

## Orientações para contribuição e verificação

- Executar `backend/scripts/check_syllabus_privacy.py` e os testes em PostgreSQL local (`TEST_SUPABASE_DB_URL` restrito a `localhost`/`127.0.0.1`) ao alterar políticas, triggers ou consultas do worker.
- Validar cenários de lease expirado, fencing de execução antiga, `429`/timeout, teto de orçamento, rejeição de datas inventadas/instruções maliciosas e ausência de dados sensíveis em logs (`syllabus_samples.py`, `test_syllabus_processing.py`, `test_syllabus_database.py`).
- Para medição controlada do corpus sintético sem alterar produção, utilizar `backend/scripts/benchmark_syllabus.py` (modo determinístico padrão ou `--live` opt-in).

## Fontes e relações

[ADR-002](/arquitetura/adrs/adr-002-separar-hospedagem-e-ambientes) · [ADR-003](/arquitetura/adrs/adr-003-minimizar-dados-de-planos) · [ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos) · [Dados de planos](/arquitetura/dados-de-planos) · [Contratos da API](/api-specs) · [Índice de ADRs](/arquitetura/adrs/index)
