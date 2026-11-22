---
title: "Privacidade e ciclo de vida dos dados"
description: "Inventário de dados pessoais, direitos do titular, descarte de PDFs e procedimento de resposta a incidentes."
---

Este documento especifica o ciclo de vida dos dados pessoais, as bases legais de referência, os mecanismos de exclusão e portabilidade e os procedimentos operacionais de privacidade do Agenda UnB. Os textos voltados ao usuário final estão na [Política de Privacidade](/produto/politica-de-privacidade) e nos [Termos de Uso](/produto/termos-de-uso).

## Diretrizes de privacidade adotadas

| # | Tema | Decisão adotada | Fundamentação técnica |
| --- | --- | --- | --- |
| D1 | Contato e canal de atendimento ao titular | Canal oficial pelo e-mail `unbagenda@gmail.com` | Mantido na Política de Privacidade e nos Termos de Uso |
| D2 | Eventos públicos de uma conta excluída | Excluídos com a conta (`eventos.autor_id ON DELETE CASCADE`); referências cruzadas (`moderado_por`, `possivel_duplicata_de`) usam `ON DELETE SET NULL`; eventos coletados (`fonte` preenchida, `autor_id` nulo) permanecem independentes | Preserva a constraint `eventos_autor_ou_fonte` sem órfãos nem perda da coleta pública |
| D3 | Revisões de terceiros sobre planos e exclusão | Ao excluir a conta dona do plano, `planos_ensino` cascateia sobre `versoes_plano` e `avaliacoes`. Quando uma conta excluída é autora de revisão em plano alheio, `versoes_plano.autor_id` cascateia e a migration `20261118120000` (`planos_ensino.versao_aprovada_id ON DELETE SET NULL` + ajuste em `tg_preserva_texto_autorizado()`) permite concluir sem erro `42501`, inclusive em planos `processando`. Cópias já importadas pelos colegas em `eventos_pessoais` permanecem independentes (`origem_versao_id ON DELETE SET NULL`) | Coberto pelos testes em PostgreSQL (`test_privacy_database.py`) |
| D4 | Retenção de registros técnicos e cópias de segurança | Janelas de consulta operacional nos planos gratuitos: Supabase Free até 1 dia, Render Hobby 7 dias, Vercel Hobby 1 hora; sem backups manuais ou externos | Informado como janela de consulta operacional, não garantia de apagamento interno do fornecedor |
| D5 | Fontes carregadas do Google Fonts | Manter carregamento via Google Fonts (`fonts.googleapis.com` e `fonts.gstatic.com`) com divulgação explícita na Política de Privacidade e no inventário técnico | Self-hosting fica registrado como endurecimento opcional |

## Inventário de dados pessoais

Base legal: referência aos incisos do art. 7º da LGPD. O projeto tem finalidade acadêmica; a LGPD é adotada como referência de boas práticas.

| Dado | Onde fica | Finalidade | Base legal de referência | Retenção | Exclusão |
| --- | --- | --- | --- | --- | --- |
| E-mail, senha (hash), identidade Google, último acesso | Supabase Auth (`auth.users`) | Autenticação | Execução do serviço pedido pelo titular (V) | Enquanto a conta existir | Exclusão da conta (`auth_admin.delete_user`) |
| Nome, e-mail, papel, avatar | `profiles` | Identificação e permissões | Execução do serviço (V) | Enquanto a conta existir | Cascata a partir de `auth.users` |
| Agenda pessoal | `eventos_pessoais` | Agenda do titular | Execução do serviço (V) | Enquanto a conta existir | Cascata (`eventos_pessoais_user_id_fkey ON DELETE CASCADE`) |
| Eventos salvos e notificações | `eventos_salvos`, `notificacoes` | Agenda e avisos da plataforma | Execução do serviço (V) | Enquanto a conta existir | Cascata |
| Lembretes | `lembretes` | Agendamento e entrega de avisos de eventos da própria agenda | Execução do serviço (V) | Enquanto o registro estiver associado à conta | Cascata na exclusão da conta. A remoção do vínculo salvo cancela lembretes futuros pendentes. |
| Eventos sugeridos ou publicados | `eventos` (`autor_id`) | Agenda pública; nome do autor como organizador | Execução do serviço (V) | Enquanto a conta existir | Cascata (ver D2) |
| Turmas seguidas | `vinculos_turma` | Acesso a conteúdo da turma | Execução do serviço (V) | Enquanto a conta existir | Cascata |
| PDF do plano | Não é guardado nos envios novos (extraído em memória no upload). Planos legados: Storage `syllabus_files` | Extração local do texto | Execução do serviço (V) | Envios novos: não armazenado. Legados: até descarte | `scripts/descartar_pdfs.py` e passo 4 do `DELETE /api/v1/me` |
| Texto preparado e texto autorizado do plano | `planos_ensino.texto_preparado`, `texto_aprovado`, `hash_texto_aprovado` | Preparação automática e envio autorizado à IA | Execução do serviço (V) e **consentimento** para envio (I) | Enquanto a conta existir | Cascata; incluído em `/me/data-export` |
| Metadados do plano, versões e candidatos | `planos_ensino`, `versoes_plano`, `avaliacoes` | Sugerir datas | Execução do serviço (V) | Enquanto a conta existir | Cascata (ver D3) |
| Texto enviado ao provedor de IA | Não é guardado pela plataforma além do snapshot revisado | Extração de datas | **Consentimento** específico por plano (I) | Envio com `store: false` na API do Gemini | Revogação operacional: não autorizar novos envios |
| Operações de importação | `operacoes_importacao`, `itens_importacao` | Evitar duplicar eventos em retries | Execução do serviço (V) | Enquanto a conta existir | Cascata |
| Votos de avaliação | `votos_avaliacao` | Sinalizar divergências entre seguidores da turma | Execução do serviço (V) | Enquanto a conta e a avaliação existirem | Cascata |
| Aceites e consentimentos | `aceites_termos`, `consentimentos` | Comprovar leitura de versão e autorização | Cumprimento de obrigação e exercício de direitos (II, VI) | Enquanto a conta existir | Cascata |
| Tokens e estado OAuth do Google Agenda | `google_calendar_connections` (tokens cifrados com Fernet), `google_calendar_oauth_states` (TTL 10 min) | Exportação opcional para agenda `"Agenda UnB"` | **Consentimento** (I) | Até desconexão, revogação ou exclusão da conta (estado OAuth: 10 min) | Desconexão, `DELETE /me/consents/google_agenda`, `DELETE /me` e `ON DELETE CASCADE` em `profiles(id)` |
| Mapeamentos de exportação ao Google Agenda | `google_calendar_event_exports` | Associar os eventos exportados às cópias e evitar duplicação | Execução da exportação solicitada (V) | Enquanto a conta e o mapeamento existirem | Cascata na exclusão da conta |
| Alterações de papel | `auditoria_papeis` | Auditar quem alterou o papel e quando | Legítimo interesse (IX) | Conforme o ciclo de vida das referências à conta | A referência ao ator é limpa quando ele é excluído e os registros da conta afetada são removidos por cascata. |
| Endereço IP e rota acessada | Logs dos provedores; memória do limitador de taxa | Segurança e diagnóstico | Legítimo interesse (IX) | Ver D4 | Expiração |

`cliques_evento` contém apenas o identificador do evento, um UUID aleatório por visualização e a data do registro. A métrica não guarda ID da conta, IP nem agente do navegador.

**Sem dado pessoal:** `coletas_eventos` (contadores operacionais e `erro_codigo` curto de até 60 caracteres), `sincronizacoes_catalogo`, `exclusoes_conta` (somente contagens agregadas, sem `user_id` ou PII), `campus`, `categories`, `disciplinas` e `ofertas_turma`. Eventos coletados podem citar nomes de palestrantes já divulgados pela fonte institucional.

## Operadores, fontes consultadas e minimização

| Operador | Papel | Dados e limites aplicados | Local |
| --- | --- | --- | --- |
| Supabase | Banco, Auth, Storage | Todos os dados da conta (`syllabus_files` apenas para legados pendentes de descarte) | `us-east-1` (EUA) |
| Render | API FastAPI | Dados em trânsito e logs técnicos (sem corpos, conteúdo acadêmico ou tokens) | EUA |
| Vercel | SPA e `@vercel/analytics/react` | Logs de acesso e métricas agregadas do Vercel Web Analytics (sem cookies publicitários) | Rede global |
| Google Identity | Login OAuth | Nome, e-mail e foto | EUA e outros |
| Google Gemini | Extração de datas | Texto sanitizado autorizado em **Plano de Ensino**, até 40.000 bytes UTF-8, com `store: false` em `gemini.py`. A [minimização automática](/arquitetura/minimizacao-planos) cobre padrões detectáveis, incluindo e-mails, telefones, documentos e campos rotulados. | EUA e outros |
| Google Calendar | Exportação | Escopos `openid`, `email` e `https://www.googleapis.com/auth/calendar.app.created` (restrito à agenda secundária `"Agenda UnB"`). `export.py` envia até 20 eventos selecionados (com filtragem opcional por período e inclusão opcional de descrição) com `id` (SHA-256), `summary`, `start` e `end` (`America/Sao_Paulo`, +1h padrão). | EUA e outros |
| Google Fonts | Fontes e ícones | Endereço IP ao baixar fontes (`index.html`) | Rede global (ver D5) |

**Fontes públicas apenas consultadas pelo servidor:**
- **Followw (`FollowwClient`):** realiza exclusivamente requisições `GET https://api.followw.app` para `/public/classrooms/units`, `/public/classrooms` e `/public/subjects` com parâmetros `unit`, `code` e `semester`, com `follow_redirects=False`, `trust_env=False` e cliente `httpx` descartável sem cookies nem dados de conta.
- **Agenda UnB Notícias:** coleta pública de eventos institucionais (`coletas_eventos`), sem envio de dados de titulares.

## Aceite não é consentimento

| | Aceite de termos | Consentimento |
| --- | --- | --- |
| Tabela | `aceites_termos` | `consentimentos` |
| O que registra | Que a conta leu uma **versão** dos Termos ou da Política (`2026-11-20`) | Autorização para uma **finalidade** específica |
| Finalidades | — | `google_agenda` |
| Pode ser revogado | Não se aplica | Sim, a qualquer momento (`revogar_consentimento` e `DELETE /api/v1/me/consents/google_agenda`) |
| Vínculo com o conteúdo | Versão do documento (data de vigência) | `referencia_id` e `conteudo_hash` (SHA-256 do escopo autorizado) |

**Envio ao provedor de IA.** A autorização é registrada no próprio plano: `texto_aprovado` (páginas sanitizadas autorizadas no envio), `hash_texto_aprovado` e `autorizado_em`. O worker confere o hash antes de chamar o provedor, e o trigger `tg_preserva_texto_autorizado` impede alterar o snapshot durante o processamento (`status = 'processando'`). Por isso `consentimentos` não aceita `envio_texto_ia`.

## Direitos do titular na API e na interface

| Direito | Contrato | Observação |
| --- | --- | --- |
| Ver o que está pendente de leitura | `GET /api/v1/me/legal-documents` | Retorna `{"terms": {"currentVersion": "2026-11-20", "acceptedVersion": null, "acceptedAt": null, "pending": true}, "privacy": {...}}` (`Cache-Control: no-store`) |
| Registrar leitura | `PUT /api/v1/me/legal-acceptances/{terms\|privacy}` com `{"version": "2026-11-20"}` → `204` | Só aceita a versão vigente (`409` se o documento mudou) |
| Listar consentimentos | `GET /api/v1/me/consents` | Lista `items` ordenados por `grantedAt` decrescente |
| Revogar consentimento | `DELETE /api/v1/me/consents/google_agenda` → `204` | Desconecta e solicita revogação do token no Google Agenda e revoga o consentimento ativo |
| Acesso e portabilidade | `GET /api/v1/me/data-export` → `200` JSON (`agenda-unb-dados.json`) | `Cache-Control: no-store`, `Pragma: no-cache`. Inclui lembretes em `reminders` e mapeamentos em `googleCalendarExports`. Exclui tokens cifrados, `google_sub`, caminhos do Storage, chaves de idempotência e dados de terceiros. |
| Exclusão | `DELETE /api/v1/me` com `{"confirmation": "EXCLUIR MINHA CONTA"}` → `204` | `409` para o último administrador |
| Correção | Solicitação via `unbagenda@gmail.com` | `/configuracoes` exibe nome e e-mail apenas para leitura; não há edição self-service na interface |
| Retirar compartilhamento | `DELETE /api/v1/syllabus/{id}/versions/{version_id}/sharing` (`retirar_compartilhamento`) | Disponível ao autor da versão ou a um admin em **Plano de Ensino**. **Configurações** orienta sobre o fluxo. |

A versão vigente de cada documento fica em `CURRENT_LEGAL_VERSIONS` (`backend/src/modules/account/repository.py`). Ao publicar um texto novo, atualize a versão nos documentos e em `CURRENT_LEGAL_VERSIONS`: as contas passam a receber `pending: true`.

**Fluxos na interface:**
- Cadastro e login (`AuthDialog.jsx` e `AuthReturnPage.jsx`): links diretos para `/termos.html` e `/privacidade.html`, caixa obrigatória de aceite no cadastro por e-mail (separada dos consentimentos opcionais) e registro limpo no cadastro imediato, confirmação de e-mail ou entrada.
- Gate pós-login (`LegalAcceptanceGate.jsx`): exibe diálogo nativo quando `GET /api/v1/me/legal-documents` indica `pending: true` (entrada com Google, confirmação externa ou mudança de versão), tratando conflito `409` sem travar a navegação por teclado.
- Configurações e privacidade (`/configuracoes`, `SettingsPage.jsx` + link em `NavBar.jsx`): exibe versões vigentes e aceites registrados, permite revogar consentimento `google_agenda`, orienta sobre IA por plano e retirada de compartilhamento, executa **Baixar meus dados** (`agenda-unb-dados.json`) e **Excluir conta** (com resumo do que sai e do que fica, frase `"EXCLUIR MINHA CONTA"`, tratamento de `409` e retorno a `/?conta=excluida`).
- Google Agenda (`GoogleCalendarConnection.jsx`): exibe aviso explícito no diálogo de exportação e após a desconexão informando que cópias já exportadas permanecem na agenda secundária `"Agenda UnB"` no Google Agenda, com passo a passo para removê-las.

## O que acontece na exclusão da conta

Sequência executada por `DELETE /api/v1/me` (`backend/src/modules/account/service.py`):

1. Valida a frase exata `"EXCLUIR MINHA CONTA"` (`422` se divergir).
2. `preparar_exclusao_conta` serializa a verificação do último administrador (`FOR UPDATE`, `409` se for o único `admin`), registra contagens anônimas em `exclusoes_conta` (`status = 'iniciada'`) e lista os arquivos legados da conta.
3. `google_calendar_service.disconnect` apaga estados OAuth, solicita revogação remota do `refresh_token` no Google, limpa tokens/escopo e revoga o consentimento `google_agenda`.
4. `storage.list_prefix(f"{user.id}/")` e `storage.delete_objects_strict(...)` removem todos os PDFs legados do bucket `syllabus_files` (se falhar, aborta antes da exclusão do usuário para permitir nova tentativa).
5. `auth_admin.delete_user(user.id)` (`DELETE /auth/v1/admin/users/{id}`) remove a conta no Supabase Auth; o `ON DELETE CASCADE` apaga perfil e tabelas dependentes no banco, preservando cópias independentes já importadas por colegas (`origem_versao_id ON DELETE SET NULL`).
6. `concluir_exclusao_conta` marca o registro anônimo em `exclusoes_conta` como concluído.

| Apagado | Mantido |
| --- | --- |
| Perfil e credenciais | Eventos que **outras contas** já importaram para a própria agenda (ficam sem vínculo com a origem) |
| Agenda pessoal, eventos salvos, notificações e lembretes | Registro anônimo em `exclusoes_conta`, só com contagens |
| Turmas seguidas, votos, operações de importação | Eventos já exportados à agenda `"Agenda UnB"` no Google Agenda do titular |
| Aceites e consentimentos | Dados em cópias internas do provedor, até expirarem |
| Tokens, estados OAuth e mapeamentos locais do Google Agenda (com solicitação de revogação no Google) | |
| Planos enviados, com todas as versões, candidatos e arquivos legados | |
| Eventos públicos sugeridos ou publicados pela conta | |

## Descarte do PDF original (ADR-003)

- **Novos envios** não armazenam o PDF: o texto é extraído em memória no upload (`MAX_PDF_PAGES=10`, `MAX_FILE_SIZE_BYTES=10MB`), o arquivo temporário é fechado e apenas `texto_preparado` é gravado.
- **Planos antigos** podem ter o PDF no Storage. `arquivos_a_descartar()` lista apenas os encerrados (`concluido` ou `falha`), sem tocar em `pendente` ou `processando`; `registrar_descarte_arquivo(plano)` limpa `caminho_arquivo` / `arquivo_url` e grava `arquivo_descartado_em`.
- As constraints `planos_particular_exige_fonte` e `planos_descarte_remove_caminho` garantem que planos antigos descartados continuem íntegros sem caminho de arquivo.
- **Originais legados:**

```bash
cd backend
venv/bin/python -m scripts.descartar_pdfs             # dry-run: mostra quantos seriam removidos
venv/bin/python -m scripts.descartar_pdfs --executar  # remove do Storage e registra o descarte
```

## Logs

- O SQLAlchemy usa `hide_parameters=True` (`database/connection.py`).
- O handler global `@app.exception_handler(Exception)` em `backend/src/main.py` responde `500` genérico e registra apenas o nome da exceção, método HTTP e caminho, sem corpo de requisição, cabeçalhos, conteúdo acadêmico ou tokens.
- Os loggers `httpx` e `httpcore` são ajustados para `WARNING` em `main.py`, `modules/syllabus/worker.py` e `scripts/descartar_pdfs.py`.
- Falhas de banco (`IntegrityError` e `SQLAlchemyError` em `main.py`) registram apenas método HTTP e caminho; erros de PDF/Storage e chamadas administrativas ao Supabase não gravam `user_id`, caminho de arquivo, corpo de resposta nem chaves.
- `erro_codigo` de `coletas_eventos` e `sincronizacoes_catalogo` aceita apenas código curto.

## Atendimento ao titular e incidente

O atendimento pelo canal `unbagenda@gmail.com` segue confirmação de identidade pela própria conta autenticada ou e-mail cadastrado (sem pedir documentos), atendimento em até 15 dias e registro sem cópia dos dados do titular. Pedidos para apagar cópias já importadas por terceiros não são atendidos automaticamente porque pertencem à agenda de quem importou.

Em incidentes (referência: guia da ANPD para agentes de pequeno porte), a sequência operacional é conter (rotacionar chaves e revogar sessões), registrar data/sistemas afetados, avaliar risco relevante, comunicar titulares e ANPD em até três dias úteis quando aplicável, corrigir com teste de regressão e encerrar.

## Verificação

```bash
cd backend
TEST_SUPABASE_DB_URL="postgresql+psycopg://postgres:postgres@127.0.0.1:14322/postgres" \
  venv/bin/python -m pytest tests/test_privacy_database.py tests/test_account_api.py tests/test_storage.py -q
```

| Critério | Cobertura automatizada e verificações |
| --- | --- |
| Acesso e portabilidade ponta a ponta | `test_account_api.py` (`test_export_contains_the_account_data_and_nobody_elses`, `test_export_is_a_private_download`), `SettingsPage.jsx` e `privacy-account.spec.js` |
| Exclusão completa da conta | `test_account_api.py`, `test_privacy_database.py`, `SettingsPage.jsx` e `privacy-account.spec.js` (incluindo verificação de Auth e Storage) |
| Descarte do PDF após extração e eliminação de legados | Extração em memória (`syllabus/router.py`), `scripts/descartar_pdfs.py`, `test_privacy_database.py` e `test_account_api.py` |
| Tarefas pendentes e cópias independentes | `test_privacy_database.py` (inclusive cascata cruzada com `status = 'processando'`) e `test_account_api.py` |
| Conteúdo acadêmico e tokens fora dos logs | `test_unhandled_exception_returns_500_without_leaking_secrets`, `test_database_errors_are_logged_without_row_content`, `test_supabase_admin_calls_never_log_identifiers` (`test_account_api.py`) |
| Google Calendar: desconexão, revogação, tokens e aviso de cópias | `google_calendar/service.py` (escopos, Fernet, revogação), `GoogleCalendarConnection.jsx` e `privacy-account.spec.js` |
| Política e termos no cadastro, entrada e Configurações | `politica-de-privacidade.md`, `termos-de-uso.md` (`2026-11-20`), `render_legal.py --publish`, `AuthDialog.jsx`, `LegalAcceptanceGate.jsx`, `SettingsPage.jsx` |

## Histórico de versões legais

- **`2026-11-11`:** publicação inicial dos Termos de Uso e Política de Privacidade com definição do canal de atendimento e retenção operacional.
- **`2026-11-18`:** alinhamento a `CURRENT_LEGAL_VERSIONS`, inventário completo de provedores (`@vercel/analytics/react`, limites de minimização do Gemini com `store: false`, payload e escopos do Google Calendar, Followw/coleta pública e Google Fonts), autoatendimento em `/configuracoes` e avisos sobre cópias permanentes no Google Agenda (`scripts/render_legal.py --publish`).
- **`2026-11-20`:** inclusão do registro de sanitização automática e compartilhamento inicial de planos, conforme `CURRENT_LEGAL_VERSIONS`.
