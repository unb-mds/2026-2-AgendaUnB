---
title: "ADR-003 · Minimização de dados de planos de ensino"
description: "Decisão de descartar PDFs após extração local de texto e autorizar apenas o snapshot sanitizado."
---

# ADR-003 · Descartar PDFs e autorizar apenas texto sanitizado para processamento externo

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-15 |
| Rastreabilidade | RF06; RNF02 |
| Substitui | Nenhuma ADR |

## Contexto

Planos de ensino podem conter informações pessoais ou confidenciais além do cronograma necessário para extrair datas de provas e trabalhos. A persistência integral dos PDFs originais no Storage ampliava a superfície de dados pessoais sob custódia. A arquitetura exige minimizar os dados retidos pela aplicação e transmitidos ao provedor externo de IA.

## Decisão

Extrair o texto localmente na preparação e descartar o PDF original imediatamente. A autorização para novos planos é dada no envio e registrada sobre as páginas sanitizadas antes de qualquer chamada externa. Planos preparados permanecem na lista **Seus planos** e podem ser retomados quando a extração estiver disponível.

1. **Preparação e descarte imediato do PDF:**
   - `POST /api/v1/syllabus/upload` aceita PDF digital de até 10 MiB (`MAX_UPLOAD_SIZE_BYTES`, lido com limite `MAX_UPLOAD_SIZE_BYTES + 1` para rejeitar excessos sem carregar em memória) e no máximo 10 páginas (`MAX_PDF_PAGES`).
   - Extensão, MIME e assinatura são conferidos antes de iniciar um subprocesso `spawn` descartável (prazo padrão de 8s + 2,2s de limpeza). O arquivo temporário é fechado e descartado tanto no sucesso quanto na falha; novos envios não gravam o PDF no Storage.
   - Alternativa em texto bruto via `POST /api/v1/syllabus/text` aceita até 40.000 bytes UTF-8 sem truncamento, mantendo referência de página nula.
2. **Minimização e autorização explícita:**
   - PDF e texto colado passam pelo mesmo pipeline determinístico de [minimização](/arquitetura/minimizacao-planos) antes de gravar o texto preparado. A prévia do dono em `GET /api/v1/syllabus/{id}/text` usa `Cache-Control: no-store` e informa o número de trechos mascarados na preparação inicial (`redactedCount`). A interface recebe o snapshot para vinculá-lo à autorização.
   - A autorização verifica novamente as regras de minimização. O worker também bloqueia snapshots legados com identificadores detectáveis (`texto_com_dados_pessoais`), orientando o estudante a reenviar o plano para aplicar a preparação vigente.
   - A submissão à fila (`POST /api/v1/syllabus/{id}/extractions`) exige `authorize: true` e `textHash`. Em planos pendentes, a interface aciona a extração utilizando as páginas sanitizadas preparadas. O SHA-256 canônico do JSON UTF-8 compacto contendo `[{"pagina": ..., "texto": ...}]` é calculado de forma idêntica em `frontend/src/lib/approvedText.js` e no servidor.
3. **Isolamento, RLS e proteção de logs:**
   - As políticas de banco restringem `SELECT` de planos, textos preparados e versões privadas ao próprio dono, fecham escrita direta do cliente no bucket `syllabus_files`, bloqueiam alteração de autoria e tornam o snapshot em `processando` imutável por trigger (inclusive para conexões privilegiadas).
   - Logs de aplicação e erros devolvidos ao cliente não registram PDF, texto integral, parâmetros SQL ou resposta bruta do provedor. O cadastro manual em **Meus Eventos** permanece disponível para PDFs escaneados, limites excedidos ou conteúdo inadequado ao provedor.

## Alternativas para comparação

Reter o PDF em armazenamento privado permitiria reprocessar o original, mas aumentaria a superfície de dados sensíveis sob custódia. Enviar o documento completo automaticamente ao provedor simplificaria o fluxo, mas exporia dados pessoais sem filtragem prévia nem ciência explícita do usuário.

## Consequências

Se uma nova extração depender de conteúdo removido após o descarte do PDF, o usuário precisa reenviar o arquivo ou fornecer novo texto. A integração com o Gemini usa `store=false` para desativar o armazenamento de interações na API externa. A disponibilidade do processamento externo em cada ambiente depende da configuração das flags operacionais (`SYLLABUS_WORKER_ENABLED`, `SYLLABUS_PRIVACY_READY`, `SYLLABUS_PROVIDER_TERMS_READY`).

## Fontes e relações

[Minimização de dados](/arquitetura/minimizacao-planos) · [ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos) · [ADR-014](/arquitetura/adrs/adr-014-processamento-assincrono-planos-ia) · [Índice de ADRs](/arquitetura/adrs/index)
