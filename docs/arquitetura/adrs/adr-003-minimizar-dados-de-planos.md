---
title: "ADR-003 · Minimização de dados de planos de ensino"
---

# ADR-003 · Descartar PDFs e autorizar apenas texto revisado para processamento externo

**Estado** Implementada (contrato `syllabus-v3-approved-text`; ativação do provedor externo controlada por flags operacionais).

## Contexto

Planos de ensino podem conter informações pessoais ou confidenciais além do cronograma necessário para extrair datas de provas e trabalhos. O fluxo legado da Sprint 6 armazenava o PDF em bucket privado (`syllabus_files`) para leitura posterior pelo worker. Na Release 2, adotou-se minimização estrita dos dados retidos sob custódia e transmitidos ao provedor de IA, garantindo conformidade com a LGPD e com os termos do tier gratuito do provedor.

## Decisão

Extrair o texto localmente na preparação, descartar o PDF original imediatamente e exigir revisão e autorização explícita do usuário sobre o trecho exato antes de qualquer envio externo:

1. **Preparação e descarte imediato do PDF:**
   - `POST /api/v1/syllabus/upload` aceita PDF digital de até 10 MiB (`MAX_UPLOAD_SIZE_BYTES`, lido com limite `MAX_UPLOAD_SIZE_BYTES + 1` para rejeitar excessos sem carregar em memória) e no máximo 10 páginas (`MAX_PDF_PAGES`).
   - Extensão, MIME e assinatura são conferidos antes de iniciar um subprocesso `spawn` descartável (prazo padrão de 8s + 2,2s de limpeza). O arquivo temporário é fechado e descartado tanto no sucesso quanto na falha; novos envios não gravam o PDF no Storage.
   - Alternativa em texto bruto via `POST /api/v1/syllabus/text` aceita até 40.000 bytes UTF-8 sem truncamento, mantendo referência de página nula (não inventa página 1).
2. **Minimização e autorização explícita:**
   - A preparação (`backend/src/modules/syllabus/preparation.py`) remove por regex padrões comuns de e-mail, CPF/matrícula, telefone e linhas rotuladas com identificadores. Como regex não garante anonimização contextual, o estudante revisa o texto exato via `GET /api/v1/syllabus/{id}/text` (resposta com `Cache-Control: no-store`, retornando 404 para não donos).
   - A submissão à fila (`POST /api/v1/syllabus/{id}/extractions`) exige duas declarações desmarcadas por padrão (`authorize: true` e `contentEligible: true`) e `textHash` (SHA-256 canônico do JSON UTF-8 sem espaços contendo `[{"pagina": ..., "texto": ...}]`, implementado de forma idêntica em `frontend/src/lib/approvedText.js` e no servidor). Qualquer edição de texto na interface revoga ambas as confirmações.
3. **Isolamento, RLS e proteção de logs:**
   - Migrações `20261109113000_privacidade_e_revisao_planos.sql` e `20261110120000_texto_revisado_e_autorizacao_s7.sql` restringem `SELECT` de planos, textos preparados e versões privadas ao próprio dono, fecham upload direto do cliente ao bucket `syllabus_files` (preservando objetos históricos privados), bloqueiam alteração de autoria e tornam o snapshot em `processando` imutável por trigger (inclusive para conexões privilegiadas).
   - Logs de aplicação e erros devolvidos ao cliente não registram PDF, texto integral, parâmetros SQL ou resposta bruta do provedor. O cadastro manual em Meus Eventos permanece disponível para PDFs escaneados, limites excedidos ou conteúdo inadequado ao provedor.

## Alternativas para comparação

Reter o PDF em armazenamento privado permitiria reprocessar o original, mas aumentaria a superfície de dados sensíveis sob custódia. Enviar o documento completo automaticamente ao provedor simplificaria a UX, mas exporia dados pessoais sem ciência explícita do usuário.

## Consequências

Se uma nova extração depender de conteúdo removido após o descarte do PDF, o usuário precisa reenviar o arquivo ou fornecer novo texto. Edições de texto ainda não autorizadas não são persistidas pelo navegador. `store=false` no provedor externo não substitui a revisão humana nem a verificação dos termos de elegibilidade em produção (`SYLLABUS_PROVIDER_TERMS_READY`).

[Contrato da Release 2](../../atualizacoes.md#contratos-da-release-2) · [ADR-010](adr-010-versoes-e-confirmacao-de-planos.md) · [ADR-014](adr-014-processamento-assincrono-planos-ia.md)

## Leitura e manutenção

Data deste registro: **2026-11-15** (consolida o protocolo S7-B01 e as garantias de privacidade S6-D02 a partir do registro de 2026-11-08). Nomes de usuários, identificadores de ambiente e benchmarks de execução não compõem esta decisão.
