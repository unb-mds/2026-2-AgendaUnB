---
title: "Especificação do banco de dados"
description: "Documento que descreve a estrutura física DDL e as políticas de segurança RLS do banco de dados da Agenda UnB no Supabase."
---

Este documento descreve a estrutura física (DDL), funções, triggers e políticas de segurança em nível de linha (RLS) do banco de dados PostgreSQL do **Agenda UnB** no Supabase. Consulte o [diagrama de relacionamentos](/arquitetura/modelo-de-dados) e os arquivos versionados em `supabase/migrations/`.

---

## 1. Tabelas de Domínio e Catálogos Globais

### 1.1. Tabela `campus`
Armazena as localizações físicas da Universidade de Brasília (`Darcy Ribeiro (Plano Piloto)`, `FCTE (Gama)`, `FCTS (Ceilândia)`, `FUP (Planaltina)` e `FAL`).

* **Colunas:** `id` (UUID, PK, `gen_random_uuid()`), `nome` (TEXT, Not Null, Unique), `created_at` (TIMESTAMPTZ).
* **Políticas RLS:** leitura pública para todos (`USING true`).

### 1.2. Tabela `categories`
Armazena as categorias para classificação e coloração dos eventos na interface.

* **Colunas:** `id` (UUID, PK), `nome` (TEXT, Not Null, Unique), `cor` (TEXT, hexadecimal), `created_at` (TIMESTAMPTZ).
* **Políticas RLS e gestão:** leitura pública para todos (`USING true`). A escrita direta pelo navegador foi revogada; a gestão administrativa usa `admin_listar_categorias`, `admin_criar_categoria` e `admin_excluir_categoria` (restritas a `admin`, impedindo exclusão quando há eventos vinculados) ou as rotas administrativas da API FastAPI.

---

## 2. Usuários, Perfis e Auditoria

### 2.1. Tabela `profiles` (Esquema `public`)
Armazena os metadados das contas, sincronizada com `auth.users` do Supabase.

* **Colunas:** `id` (UUID, PK, FK em cascata para `auth.users(id)`), `nome_completo` (até 200 caracteres), `email` (imutável), `papel` (`student`, `professor`, `admin`), `avatar_url` (somente `https`), `criado_em`, `atualizado_em`.
* **Criação e promoção:** o trigger `on_auth_user_created` (`tg_cria_perfil`) cria o perfil no cadastro. O papel `professor` exige e-mail `@unb.br` **confirmado**: cadastros ainda não confirmados nascem `student` e são promovidos pelo trigger `on_auth_user_confirmed_professor_request` (`tg_promove_professor_confirmado`) após a confirmação do e-mail. `admin` nunca é atribuído no cadastro.
* **Políticas RLS:** o próprio usuário lê seu perfil (exigindo e-mail confirmado via política restritiva `confirmed_account`); administradores leem todos. Visitantes não têm acesso. A atualização direta pelo navegador aceita apenas `nome_completo`, `avatar_url` e autopromoção `student → professor` com e-mail `@unb.br` confirmado; alterações de terceiros passam por `admin_definir_papel`.

### 2.2. Tabela `auditoria_papeis`
Registra toda alteração de papel, por qualquer caminho (RPC administrativa, autopromoção, confirmação de e-mail, backend ou SQL).

* **Colunas:** `id` (BIGINT identity, PK), `usuario_id` (UUID, FK `profiles`, `ON DELETE CASCADE`), `ator_id` (UUID, FK `profiles`, `ON DELETE SET NULL`, nulo quando não há sessão de usuário), `papel_anterior` (TEXT), `papel_novo` (TEXT), `criado_em` (TIMESTAMPTZ).
* **Políticas RLS:** leitura restrita a administradores (`is_admin()`); nenhuma escrita direta pela API ou navegador (preenchida pelo trigger `tg_audita_papel`).

### 2.3. Privilégios, e-mail confirmado e funções
Visitantes acessam apenas o catálogo público (`eventos` aprovados, `campus`, `categories`, `disciplinas`, `ofertas_turma`). `TRUNCATE` não é concedido à API e funções novas exigem `GRANT EXECUTE` explícito. Políticas restritivas `confirmed_account` garantem via `current_account_has_confirmed_email()` que contas não confirmadas não operem recursos privados autenticados. As regras para novas migrações constam em [Verificação de segurança](/processo/seguranca#regras-para-novas-migracoes).

---

## 3. Tabelas Core: Eventos, Coleta, Cliques e Lembretes

### 3.1. Tabela `eventos` (Agenda Pública Institucional — RF14)
Eventos publicados por professor ou administrador, sugestões da comunidade e itens coletados da Agenda UnB Notícias.

* **Colunas principais:**
  * `id` (UUID, PK), `autor_id` (UUID, FK `profiles(id)` `ON DELETE CASCADE`, nulo apenas em eventos coletados: `CHECK (autor_id is not null or fonte is not null)`).
  * `titulo` (TEXT, Not Null, mínimo 3 caracteres), `descricao` (TEXT, Not Null).
  * `data_evento` (TIMESTAMPTZ, obrigatório quando `status = 'aprovado'`), `data_fim` (TIMESTAMPTZ), `dia_inteiro` (BOOLEAN), `data_inicio_civil` (DATE), `data_fim_civil` (DATE).
  * `localizacao` (TEXT), `link_externo` (TEXT, validado `http(s)`), `campus_id` (UUID, FK `campus`), `category_id` (UUID, FK `categories`).
  * `status` (TEXT, Not Null, `DEFAULT 'pendente'`, `CHECK (status in ('pendente', 'aprovado', 'rejeitado'))`), `justificativa_recusa` (TEXT), `sugestao_estudante` (BOOLEAN), `criado_em` (TIMESTAMPTZ).
  * `fonte`, `fonte_id`, `fonte_url`, `fonte_tipo`, `fonte_hash`, `coletado_em`, `campos_editados`, `motivo_revisao`, `possivel_duplicata_de`: metadados de coleta.
  * `moderado_por`, `moderado_em`: registro da decisão de moderação.
  * `interessados_count` (INTEGER): contador agregado de redirecionamentos em **Conferir evento**, atualizado exclusivamente por `registrar_redirecionamento_evento`.
* **Políticas RLS:** leitura pública apenas quando `status = 'aprovado'`; autores veem suas próprias sugestões e moderadores leem todos os itens. Escrita direta de criação pelo navegador foi removida; criação, edição e moderação passam pela API ou pelas RPCs autorizadas.

### 3.2. Tabela `cliques_evento` (RF12)
Registra a deduplicação anônima de acionamentos em **Conferir evento**.

* **Colunas:** `evento_id` (UUID, PK, FK `eventos(id)` `ON DELETE CASCADE`), `click_id` (UUID, PK), `criado_em` (TIMESTAMPTZ). Não armazena `user_id`, IP ou `User-Agent`.
* **Políticas RLS e função:** acesso bloqueado para `anon` e `authenticated`. A função `registrar_redirecionamento_evento(p_evento_id, p_click_id)` (restrita a `service_role`) valida que o evento está aprovado e possui `link_externo` `http(s)`, insere `(evento_id, click_id)` com `ON CONFLICT DO NOTHING` e incrementa `eventos.interessados_count` na mesma transação.

### 3.3. Tabela `eventos_pessoais` (Agenda Privada — RF09)
Agenda privada gerenciada exclusivamente por cada conta autenticada.

* **Colunas:**
  * `id` (UUID, PK), `user_id` (UUID, Not Null, FK `auth.users(id)` `ON DELETE CASCADE`).
  * `titulo` (TEXT, Not Null, mínimo 3 caracteres), `descricao` (TEXT), `localizacao` (TEXT, até 250 caracteres).
  * `data_hora` (TIMESTAMPTZ, Not Null), `data_fim` (TIMESTAMPTZ), `dia_inteiro` (BOOLEAN), `data_inicio_civil` (DATE), `data_fim_civil` (DATE).
  * `campus_id` (UUID, FK `campus`), `category_id` (UUID, FK `categories`).
  * `origem_plano_id` (UUID), `origem_avaliacao_id` (UUID), `origem_versao_id` (UUID, FK `versoes_plano(id)` `ON DELETE SET NULL`), `origem_pagina` (INTEGER), `origem_trecho` (TEXT), `criado_em` (TIMESTAMPTZ).
* **Políticas RLS:** isolamento total por `auth.uid() = user_id` em SELECT, INSERT, UPDATE e DELETE, combinado com a política restritiva `confirmed_account`.

### 3.4. Datas e intervalos (ADR-011) {#34-datas-e-intervalos-adr-011}
Instantes ficam em `data_evento`/`data_hora` e `data_fim` (`TIMESTAMPTZ`). Eventos de dia inteiro usam `dia_inteiro = true` com datas civis em `data_inicio_civil` e `data_fim_civil` (`DATE`). O fim é sempre **exclusivo** (um evento de 18 a 20/11 inclusive usa início 18 e fim 21).

* **Triggers** `eventos_normaliza_datas` e `eventos_pessoais_normaliza_datas`: em eventos de dia inteiro, preenchem `data_evento`/`data_hora` e `data_fim` como a meia-noite de `America/Sao_Paulo` das datas civis correspondentes para uniformizar ordenação, filtros e lembretes.
* **Validações:** dia inteiro exige ambas as datas civis e fim posterior ao início; eventos com horário não aceitam datas civis; `data_fim`, quando presente, é posterior ao início.
* **Índices:** `idx_eventos_aprovados_data` (parcial, `status = 'aprovado'`) e `idx_eventos_pessoais_usuario_data (user_id, data_hora)`.
* Registros antigos com horário `00:00` não são convertidos automaticamente para dia inteiro.

### 3.5. Coleta de eventos e tabela `coletas_eventos` {#35-coleta-de-eventos}
Eventos coletados da Agenda UnB Notícias são armazenados na tabela `eventos`, identificados pela procedência.

* **Chave da origem:** índice único parcial `uq_eventos_fonte (fonte, fonte_id)`. Coletas sucessivas ou concorrentes atualizam o mesmo registro sem duplicação.
* **Função** `registrar_evento_coletado(jsonb)` (restrita a `service_role`): execução atômica por item que publica itens completos e inequívocos, encaminha à revisão (`motivo_revisao` em `incompleto`, `ambiguo`, `possivel_duplicata`, `informe`), concilia URL idêntica à de evento cadastrado manualmente e preserva edições locais (`campos_editados`) e decisões de moderação (`moderado_em`).
* **Triggers de proteção:** `eventos_registra_edicao_local` anota campos alterados fora da coleta; `eventos_protege_procedencia` impede gravação de procedência ou moderação pelo navegador.
* **Tabela `coletas_eventos`:** registra uma linha por execução do coletor (`id`, `fonte`, `status`, `iniciada_em`, `concluida_em`, `itens_lidos`, `criados`, `atualizados`, `inalterados`, `conciliados`, `para_revisao`, `erro_codigo` curto). RLS ativo com acesso revogado para `anon` e `authenticated`.
* **Revisão:** `listar_revisoes_coleta(p_status, p_offset)` lista itens para professor e admin; a decisão usa `moderar_sugestao`, que registra `moderado_por` e `moderado_em` e recusa publicar item sem data.

### 3.6. Tabela `lembretes` (ADR-013)
Avisos persistentes na plataforma agendados 24 horas antes do início de cada evento da agenda da conta.

* **Colunas:** `id` (UUID, PK), `user_id` (UUID, FK `profiles` `ON DELETE CASCADE`), `tipo_evento` (`pessoal` ou `publico_salvo`), `evento_pessoal_id` ou `evento_id` (FK com `ON DELETE CASCADE`), `inicio_referencia`, `agendado_para`, `status` (`pendente` ou `disparado`), `disparado_em`, `lido_em`, `criado_em`.
* **Idempotência:** índices únicos parciais `(user_id, evento_pessoal_id, inicio_referencia)` e `(user_id, evento_id, inicio_referencia)`.
* **Triggers:** em `eventos_pessoais`, `eventos_salvos` e `eventos`, agendam ao entrar na agenda faltando mais de 24 h, recalculam quando o início muda e cancelam na exclusão, remoção do vínculo ou retirada do catálogo.
* **Função** `disparar_lembretes(limite)`: executada via Supabase Cron (`pg_cron`), torna visíveis os avisos vencidos uma única vez (`FOR UPDATE SKIP LOCKED`) após revalidar elegibilidade.
* **Políticas RLS:** a conta lê apenas os próprios avisos já disparados e atualiza somente `lido_em` preservando a primeira leitura.

Consulte o uso operacional dessas estruturas em [Dados de eventos](/arquitetura/dados-de-eventos).

---

## 4. Organizador Acadêmico: Planos, Turmas e Versões

### 4.1. Tabela `planos_ensino`
Armazena envios de planos de ensino, fila persistida de processamento e snapshot de texto sanitizado.

* **Dono, turma e tipo:** `id` (UUID, PK), `user_id` (UUID, FK `profiles(id)` `ON DELETE CASCADE`), `tipo` (`particular` ou `oficial`), `professor_id` (UUID, nulo em planos particulares), `oferta_id` (UUID, FK `ofertas_turma(id)` `ON DELETE SET NULL`), `disciplina`, `turma`, `ano` (2000–2100), `semestre` (1 ou 2), `plano_oficial_id` (UUID, `ON DELETE SET NULL`), `versao_aprovada_id` (UUID, FK `versoes_plano(id)` `ON DELETE SET NULL`).
* **Arquivo e descarte:** `nome_arquivo`, `tamanho_bytes`, `tipo_arquivo` (`pdf` ou `text`), `paginas`, `caminho_arquivo` e `arquivo_url` (mantidos apenas para registros legados até descarte), `arquivo_descartado_em` (TIMESTAMPTZ). Novos envios processam o PDF em memória e descartam o arquivo imediatamente sem gravá-lo no Storage (`filePath: null`). O bucket privado `syllabus_files` tem escrita direta pelo navegador revogada.
* **Minimização e autorização:** `texto_preparado` (JSONB), `texto_aprovado` (JSONB), `hash_texto_aprovado` (CHAR/TEXT 64), `versao_texto` (INT), `ocorrencias_mascaradas` (INT ≥ 0), `duracao_preparacao_ms` (INT), `autorizado_em` (TIMESTAMPTZ), `enfileirado_em` (TIMESTAMPTZ). O trigger `tg_preserva_texto_autorizado` impede alteração do snapshot enquanto `status = 'processando'`.
* **Fila, lease e orçamento:** `status` (`pendente`, `processando`, `concluido`, `falha`), `execucao_atual` (SMALLINT), `token_processamento` (UUID para fencing), `proxima_tentativa_em` (TIMESTAMPTZ), `custo_reservado_usd` (NUMERIC(12,6)), `duracao_processamento_ms` (INT), `quantidade_eventos` (INT ≥ 0), `provedor_ia`, `modelo_ia`, `versao_processamento`, `erro_codigo` (`pdf_invalido`, `pdf_protegido`, `pdf_sem_texto`, `limite_paginas`, `falha_ia`, `tempo_esgotado`, `erro_interno`, `texto_com_dados_pessoais`), `erro` (até 500 caracteres, sanitizado), `processamento_iniciado_em`, `processado_em`, `criado_em`, `atualizado_em`.
* **Políticas RLS:** leitura restrita ao dono (`user_id = auth.uid()`), com política restritiva `confirmed_account`. Alterações de estado são reservadas à API, ao worker e às funções autorizadas.

### 4.2. Tabela `avaliacoes`
Tabela física única das avaliações candidatas extraídas dos planos de ensino.

* **Colunas:** `id` (UUID, PK), `plano_id` (UUID, Not Null, FK `planos_ensino` `ON DELETE CASCADE`), `versao_id` (UUID, Not Null), `ordem` (SMALLINT ≥ 0, único com `versao_id`), `titulo` (TEXT, Not Null), `data_avaliacao` (TIMESTAMPTZ, opcional), `data_sugerida` (DATE), `hora_sugerida` (TIME), `campos_ambiguos` (TEXT[]), `tipo` (TEXT), `ambiguo` (BOOLEAN), `pagina_origem` (INTEGER), `trecho_origem` (TEXT), `status` (`pendente`, `confirmado`, `descartado`), `execucao` (INTEGER), `versao_processamento`, `provedor`, `modelo_ia`, `revisado_em`, `criado_em`.
* **Integridade:** a FK composta `(plano_id, versao_id) → versoes_plano(plano_id, id)` impede vínculo cruzado entre planos distintos.
* **Políticas RLS e imutabilidade:** leitura por quem pode ler a versão (`pode_ler_versao`). Triggers `avaliacoes_compartilhada_imutavel` e `avaliacoes_zz_nao_entra_em_compartilhada` impedem alterar título/datas ou inserir novos candidatos em versão compartilhada (permitindo apenas alteração lógica de `status`).

### 4.3. Tabela `versoes_plano`
Versionamento de planos de ensino ([ADR-010](/arquitetura/adrs/adr-010-versoes-e-confirmacao-de-planos)).

* **Colunas:** `id` (UUID, PK), `plano_id` (UUID, Not Null, FK `planos_ensino` `ON DELETE CASCADE`), `numero` (SMALLINT ≥ 1, único por plano), `autor_id` (UUID, Not Null, FK `profiles`), `autor_papel` (`student`, `professor`, `admin`), `versao_origem_id` (UUID, opcional, `ON DELETE SET NULL`), `procedencia_institucional` (BOOLEAN, padrão `false`), `fonte_institucional_url` (TEXT), `procedencia_validada_por` (UUID), `procedencia_validada_em` (TIMESTAMPTZ), `visibilidade` (`privada` ou `compartilhada`, padrão `privada`), `compartilhada_em`, `retirada_em`, `retirada_por`, `criado_em`.
* **Regras e funções:** todo plano recebe `v1` automaticamente via trigger. `v1` vinculada a oferta e concluída com candidatos é compartilhada automaticamente ao ser consultada ou confirmada pelo autor, salvo quando retirada (`retirada_em`). Funções `compartilhar_versao`, `retirar_compartilhamento`, `criar_revisao` e `validar_procedencia_institucional` recebem `p_ator` e aplicam as permissões no banco.
* **Políticas RLS:** leitura restrita ao autor da versão ou a seguidores da oferta quando `visibilidade = 'compartilhada'`. Compartilhar versão não expõe o registro de `planos_ensino` nem o texto preparado privado.

### 4.4. Tabelas `disciplinas`, `ofertas_turma`, `vinculos_turma` e `sincronizacoes_catalogo`
Catálogo público de turmas ([ADR-009](/arquitetura/adrs/adr-009-catalogo-publico-de-turmas)) e vínculos autodeclarados dos usuários.

* **`disciplinas`:** `id` (UUID, PK), `origem` (`followw` | `manual`), `origem_id` (opcional), `codigo`, `nome`, `unidade`, `nivel`, `atualizado_na_origem_em`, `criado_em`, `atualizado_em`.
* **`ofertas_turma`:** `id` (UUID, PK), `disciplina_id` (FK `disciplinas`, `ON DELETE RESTRICT`), `publicacao_id` (FK `sincronizacoes_catalogo`), `origem`, `origem_id` (opcional), `turma` (texto, preservando zeros à esquerda), `ano` (2000–2100), `semestre` (1 ou 2), `professor`, `horarios`, `atualizado_na_origem_em`, `sincronizado_em`, `criado_em`, `atualizado_em`. Identidade única `(disciplina_id, turma, ano, semestre)`.
* **`sincronizacoes_catalogo`:** `id` (UUID, PK), `origem` (`followw`), `status` (`executando`, `concluida`, `falha`), `iniciada_em`, `concluida_em`, `ofertas_lidas`, `criadas`, `atualizadas`, `erro_codigo` (até 60 caracteres, sem respostas brutas), `unidades`, `periodos`, `cobertura`, `rejeitadas` (JSONB). RLS ativo com acesso restrito a `service_role`. A função `estado_catalogo` calcula `source_updated_at` e `stale` (após falha ou 24 horas).
* **`vinculos_turma`:** chave primária `(user_id, oferta_id)`, `origem` (`autodeclarado`), `criado_em`. Escrita direta bloqueada para navegador; gerenciada pelo backend.
* **Políticas RLS:** `disciplinas` e `ofertas_turma` têm leitura pública; `vinculos_turma` restringe leitura ao próprio usuário autenticado.

### 4.5. Importação idempotente: `operacoes_importacao` e `itens_importacao`
* **Unicidade em `eventos_pessoais`:** índice parcial único `(user_id, origem_avaliacao_id)`.
* **`operacoes_importacao`:** `id` (UUID, PK), `user_id` (FK `profiles` `ON DELETE CASCADE`), `chave` (única com `user_id`), `versao_id` (FK `versoes_plano` `ON DELETE SET NULL`), `conteudo_hash`, `criado_em`.
* **`itens_importacao`:** chave primária `(operacao_id, avaliacao_id)`, `evento_pessoal_id` (FK `eventos_pessoais` `ON DELETE SET NULL`), `resultado` (`criado` | `ja_importado`), `tipo_revisado`.
* **Função `confirmar_importacao(ator, chave, versao, itens)`:** grava operação, itens e eventos na mesma transação. Repetir a chave retorna o resultado anterior sem recriar eventos apagados; reutilizar a chave com conteúdo divergente retorna SQLSTATE `AG409`.

### 4.6. Tabela `votos_avaliacao`
* **Colunas:** chave primária `(user_id, avaliacao_id)`, `valor` (`confirma` | `contesta`), `criado_em`, `atualizado_em`.
* **Funções e RLS:** `votar_avaliacao` exige versão compartilhada e vínculo com a oferta; `resumo_votos_versao` retorna contagens agregadas omitindo avaliações descartadas. Cada conta lê apenas os próprios votos via RLS; votos nunca alteram datas automaticamente.

Consulte o uso dessas funções pela API em [Dados de planos](/arquitetura/dados-de-planos).

---

## 5. Eventos Salvos e Notificações

* **`eventos_salvos`:** chave primária composta `(user_id, event_id)`, FKs para `profiles(id)` e `eventos(id)` com `ON DELETE CASCADE`, `criado_em`. RLS restringe leitura, inserção e exclusão ao próprio usuário autenticado (sem política de UPDATE).
* **`notificacoes`:** `id` (UUID, PK), `usuario_id` (FK `profiles`), `evento_id` (FK `eventos`), `tipo` (`submissao`, `aprovacao`, `recusa`), `titulo_evento`, `justificativa`, `criado_em`, `lida_em`. Gerada por triggers na transação do evento; RLS e permissões de coluna permitem ao destinatário apenas ler e atualizar `lida_em`.

---

## 6. Integração com Google Agenda

As credenciais e mapeamentos de exportação são isolados exclusivamente no backend (RLS ativo sem políticas para `anon` ou `authenticated`; acesso revogado para clientes de navegador).

* **`google_calendar_oauth_states`:** desafios OAuth temporários de uso único (expiração de 10 minutos): `state_hash` (PK, SHA-256 hex), `user_id` (FK `profiles` `ON DELETE CASCADE`), `agenda_email`, `encrypted_code_verifier` (PKCE S256 cifrado), `expires_at`, `criado_em`.
* **`google_calendar_connections`:** vínculo OAuth da conta: `user_id` (PK, FK `profiles` `ON DELETE CASCADE`), `google_sub` (Unique), `google_email`, `calendar_id` (ID da agenda secundária **"Agenda UnB"**), `encrypted_access_token`, `encrypted_refresh_token` (cifrados com Fernet), `access_token_expires_at`, `granted_scope`, `criado_em`, `atualizado_em`.
* **`google_calendar_event_exports`:** mapeamento idempotente por evento exportado: chave primária `(user_id, event_kind, local_event_id)` (`event_kind` em `personal` | `saved`), `calendar_id`, `google_event_id` (formato `base32hex`), `exported_version` (SHA-256 canônico), `status` (`pending`, `exported`, `updated`, `already_exported`, `failed`), `last_idempotency_key`, `criado_em`, `atualizado_em`.

---

## 7. Privacidade, Aceites Legais e Ciclo de Vida da Conta

* **`aceites_termos`:** registro de ciência por versão dos documentos legais: chave primária `(user_id, documento, versao)` (`documento` em `terms` | `privacy`), `aceito_em`. RLS permite leitura apenas ao próprio usuário autenticado; escrita via backend.
* **`consentimentos`:** consentimentos opcionais e revogáveis separados do aceite dos termos: `id` (UUID, PK), `user_id` (FK `profiles` `ON DELETE CASCADE`), `finalidade` (`google_agenda`), `referencia_id`, `conteudo_hash`, `concedido_em`, `revogado_em`. Índice único parcial garante no máximo um consentimento ativo (`revogado_em IS NULL`) por `(user_id, finalidade)`. RLS permite leitura apenas ao próprio usuário.
* **`exclusoes_conta`:** registro anônimo agregado de exclusões de conta, sem `user_id` ou PII: `id` (UUID, PK), `status` (`iniciada`, `concluida`), `iniciada_em`, `concluida_em`, `planos_removidos`, `eventos_pessoais_removidos`, `eventos_publicos_removidos`, `arquivos_storage_removidos`. Acesso exclusivo de `service_role`; alimentada por `preparar_exclusao_conta` (que impede exclusão do último administrador) e `concluir_exclusao_conta`.
