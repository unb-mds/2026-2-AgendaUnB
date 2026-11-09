# Modelo Físico de Banco de Dados e Políticas de Segurança (RLS)

Este documento descreve a estrutura física (DDL) atualizada do banco de dados do projeto **Agenda UnB**, incluindo as tabelas vigentes, seus relacionamentos e as Políticas de Segurança em Nível de Linha (Row Level Security - RLS) adotadas no Supabase para garantir o isolamento e a segurança dos dados.

---

## 1. Tabelas de Domínio e Catálogos Globais

Estas tabelas armazenam informações estruturais transversais, utilizadas tanto em eventos públicos quanto privados.

### 1.1. Tabela `campus`
Armazena as localizações físicas da Universidade de Brasília.
*   **Colunas:**
    *   `id` (UUID, Primary Key): Identificador único gerado automaticamente (`gen_random_uuid()`).
    *   `nome` (TEXT, Not Null, Unique): Nome oficial do campus (ex: Darcy Ribeiro, FGA).
    *   `created_at` (TIMESTAMPTZ): Data e hora de criação.
*   **Políticas RLS:** Segurança em Nível de Linha habilitada.
    *   **Leitura (SELECT):** Permitida para todos (`USING true`). Política: *"Permitir leitura pública de campus"*.

### 1.2. Tabela `categories`
Armazena as categorias para classificação e coloração dos eventos na interface.
*   **Colunas:**
    *   `id` (UUID, Primary Key): Identificador único.
    *   `nome` (TEXT, Not Null, Unique): Nome da categoria (ex: Prova, Aula, Lazer).
    *   `cor` (TEXT): Código hexadecimal da cor.
    *   `created_at` (TIMESTAMPTZ): Data e hora de criação.
*   **Políticas RLS:** Segurança em Nível de Linha habilitada.
    *   **Leitura (SELECT):** Permitida para todos (`USING true`). Política: *"Permitir leitura pública de categorias"*.

---

## 2. Usuários e Perfis

### 2.1. Tabela `profiles` (Esquema `public`)
Armazena os metadados dos usuários, sincronizada com a tabela nativa de autenticação (`auth.users`) do Supabase.
*   **Colunas:**
    *   `id` (UUID, Primary Key): Referência em cascata para `auth.users(id)`.
    *   *(Nota: Metadados adicionais como nome, email e papel são gerenciados via triggers de sincronização no banco).*
*   **Políticas RLS:**
    *   **Leitura (SELECT):** Permitida para todos os visitantes e usuários (`USING true`). Política: *"perfis visiveis para todos"*.

---

## 3. Tabelas Core: Eventos e Agenda

### 3.1. Tabela `eventos` (Agenda Pública Institucional - RF14)
Eventos globais propostos por professores ou verificados pela IA.
*   **Colunas:**
    *   `id` (UUID, Primary Key): Identificador único.
    *   `autor_id` (UUID, Not Null): Chave estrangeira para `profiles(id)` (`ON DELETE CASCADE`).
    *   `titulo` (TEXT, Not Null): Título do evento. Validação: Mínimo de 3 caracteres (`CHECK (char_length(trim(titulo)) >= 3)`).
    *   `descricao` (TEXT, Not Null): Detalhamento do evento.
    *   `data_evento` (TIMESTAMPTZ, Not Null): Data e hora consolidadas do evento.
    *   `localizacao` (TEXT): Local físico específico (ex: Sala S1, Auditório).
    *   `link_externo` (TEXT): Link auxiliar ou de inscrição.
    *   `campus_id` (UUID): Chave estrangeira para a tabela `campus(id)`.
    *   `category_id` (UUID): Chave estrangeira para a tabela `categories(id)`.
    *   `status` (TEXT, Not Null): Controle de moderação (`DEFAULT 'pendente'`). Validação: `CHECK (status in ('pendente', 'aprovado', 'rejeitado'))`.
    *   `criado_em` (TIMESTAMPTZ, Not Null): Timestamp de criação (`DEFAULT now()`).
*   **Políticas RLS:** Segurança em Nível de Linha habilitada.
    *   **Leitura (SELECT):** Apenas eventos moderados. Política: *"eventos aprovados sao publicos"* (`USING (status = 'aprovado')`).
    *   **Criação (INSERT):** Apenas o próprio autor autenticado. Política: *"usuarios logados podem criar eventos"* (`WITH CHECK (autor_id = (select auth.uid()))`).

### 3.2. Tabela `eventos_pessoais` (Agenda Privada - RF09)
Agenda estritamente privada, gerenciada e visualizada unicamente por cada estudante.
*   **Colunas:**
    *   `id` (UUID, Primary Key): Identificador único.
    *   `user_id` (UUID, Not Null): Chave estrangeira para `auth.users(id)` (`DEFAULT auth.uid()`).
    *   `titulo` (TEXT, Not Null): Título do compromisso. Validação: Mínimo de 3 caracteres.
    *   `descricao` (TEXT): Notas extras.
    *   `data_hora` (TIMESTAMPTZ, Not Null): Data e hora do compromisso.
    *   `campus_id` (UUID): Chave estrangeira para a tabela `campus(id)`.
    *   `category_id` (UUID): Chave estrangeira para a tabela `categories(id)`.
    *   `criado_em` (TIMESTAMPTZ, Not Null): Timestamp de criação.
*   **Políticas RLS:** Segurança em Nível de Linha habilitada (Isolamento Total).
    *   **Leitura (SELECT):** Política *"utilizadores podem ver os seus proprios eventos"* (`USING (auth.uid() = user_id)`).
    *   **Criação (INSERT):** Política *"utilizadores podem criar eventos"* (`WITH CHECK (auth.uid() = user_id)`).
    *   **Edição (UPDATE):** Política *"utilizadores podem atualizar os seus proprios eventos"* (`USING (auth.uid() = user_id)` e `WITH CHECK`).
    *   **Exclusão (DELETE):** Política *"utilizadores podem deletar os seus proprios eventos"* (`USING (auth.uid() = user_id)`).

---

## 4. Organizador Acadêmico

Migrações de referência: `20261026120000_upload_planos_ensino.sql` (#40), `20261027120000_planos_particulares_e_candidatos.sql` (S6-D01, #53), `20261029160000_syllabus_review_confirmation.sql` (S6-B02), `20261107000000_planos_escrita_via_backend.sql` e `20261109120000_turmas_vinculos_versoes.sql` (S7-D01, #69).

Fluxo: o upload (#40) cria o plano como `pendente`; o processamento (S6-B01) passa para `processando`, grava candidatos e termina em `concluido` ou `falha`; a revisão (S6-B02) marca cada candidato como `confirmado` ou `descartado`. Nenhum evento pessoal é criado sem confirmação do estudante.

### 4.1. Tabela `planos_ensino`
PDFs de plano de ensino. Um plano é `particular` (enviado por um usuário para a própria agenda) ou `oficial` (plano de uma turma, enviado pelo professor; reservado para o Modelo Dual). As colunas de arquivo e rastreamento vêm da #40 (`20261026120000`); tipo, estados, erro sanitizado, período e dados da IA vêm da S6-D01 (`20261027120000`).
*   **Dono e tipo:**
    *   `id` (UUID, Primary Key).
    *   `user_id` (UUID, Not Null): dono, quem enviou. FK para `profiles(id)` (`ON DELETE CASCADE`).
    *   `tipo` (TEXT, Not Null, padrão `particular`): `particular` ou `oficial`.
    *   `professor_id` (UUID): somente em plano oficial, professor responsável pela turma. Em plano particular é sempre nulo.
    *   `disciplina` (TEXT) e `turma` (TEXT): turma obrigatória somente em plano oficial.
    *   `ano` (SMALLINT, 2000–2100) e `semestre` (SMALLINT, 1 ou 2): opcionais por enquanto; o upload (#40) ainda não os recebe.
    *   `plano_oficial_id` (UUID): referência opcional ao plano oficial correspondente (`ON DELETE SET NULL`). Só em plano particular e nunca para si mesmo.
*   **Arquivo** (bucket `syllabus_files`, #43):
    *   `caminho_arquivo` (TEXT, Unique): `syllabus_files/<user_id>/<arquivo>.pdf`. A pasta precisa ser a do dono, a mesma exigida pelas políticas do bucket. Obrigatório em plano particular.
    *   `nome_arquivo` (TEXT, até 255), `tamanho_bytes` (BIGINT, 1 B a 10 MB), `tipo_arquivo` (somente `pdf`), `paginas` (SMALLINT ≥ 1). O limite de 10 páginas da Sprint 06 é validado no back-end (#40).
    *   `arquivo_url` (TEXT): legado. Use `caminho_arquivo`.
*   **Processamento:**
    *   `status` (TEXT, Not Null, padrão `pendente`): `pendente`, `processando`, `concluido` ou `falha`. Os valores em inglês aceitos pela #40 (`processing`, `failed`, `completed`) foram convertidos e não são mais aceitos.
    *   `quantidade_eventos` (INT ≥ 0): quantidade de candidatos extraídos.
    *   `execucao_atual` (SMALLINT, Not Null, padrão 0): número da execução mais recente. Cada novo processamento incrementa; os candidatos válidos são os desta execução.
    *   `provedor_ia`, `modelo_ia`, `versao_processamento` (TEXT): da execução mais recente.
    *   `erro_codigo` (TEXT): obrigatório se, e somente se, `status = 'falha'`. Valores: `pdf_invalido`, `pdf_protegido`, `pdf_sem_texto`, `limite_paginas`, `falha_ia`, `tempo_esgotado`, `erro_interno`.
    *   `erro` (TEXT, até 500): mensagem curta e segura para o usuário, só em `falha`. Nunca guarda stack trace, texto do PDF ou resposta bruta da IA.
    *   `processamento_iniciado_em` (obrigatório em `processando`), `processado_em` (obrigatório se, e somente se, `concluido` ou `falha`), `criado_em`, `atualizado_em` (mantido por trigger).
    *   **Resultado vazio** é `concluido` sem candidatos, e não `falha`.
*   **Dados anteriores:** linhas sem `caminho_arquivo` (anteriores à #40) viraram `oficial`, com o professor como dono e `status = 'concluido'`. Linhas criadas pela #40 continuam `particular`; `professor_id` foi limpo e `processing` virou `pendente`. Nada foi apagado.
*   **Índices:** histórico do usuário `(user_id, criado_em desc, id)`; fila do worker `(status, processamento_iniciado_em)` parcial em `pendente`/`processando`, usada para retomar tarefas interrompidas; `plano_oficial_id` parcial; e os índices da #40 em `user_id` e `status`.
*   **Turma:** `oferta_id` (UUID, opcional) liga o plano a uma oferta de `ofertas_turma` (`ON DELETE SET NULL`). Planos antigos e envios sem turma continuam válidos.
*   **Políticas RLS:** RLS habilitado. Desde `20261107000000`, o navegador só lê os próprios planos (`user_id = auth.uid()`); toda escrita passa pelo back-end. O registro do plano e o caminho do PDF continuam visíveis só ao dono, mesmo quando uma versão é compartilhada.

### 4.2. Tabela `avaliacoes` (candidatos)
Tabela oficial de candidatos extraídos dos planos (decisão da equipe na S7-D01). São sugestões: só viram compromisso após confirmação do estudante. A tabela `candidatos_avaliacao` (#53), que nenhum código usava, foi removida em `20261109120000`.
*   **Colunas:**
    *   `id` (UUID, Primary Key) e `plano_id` (UUID, Not Null, FK para `planos_ensino`, `ON DELETE CASCADE`).
    *   `versao_id` (UUID, Not Null): versão do plano a que o candidato pertence. A FK composta `(plano_id, versao_id)` → `versoes_plano(plano_id, id)` impede apontar para a versão de outro plano. Quando omitido no INSERT, um trigger usa a versão mais recente do plano.
    *   `ordem` (SMALLINT ≥ 0, opcional): posição do candidato na versão. `(versao_id, ordem)` é único, para reprocessar sem duplicar.
    *   `titulo` (TEXT, Not Null), `data_avaliacao` (TIMESTAMPTZ, opcional), `tipo` (TEXT), `ambiguo` (BOOLEAN, padrão falso).
    *   `pagina_origem` (INTEGER) e `trecho_origem` (TEXT): evidência no plano.
    *   `status` (TEXT, padrão `pendente`), `versao_processamento` e `provedor` (TEXT).
*   **Políticas RLS:** leitura pelo dono do plano (*"dono do plano consulta candidatos"*) e, quando a versão estiver compartilhada, por quem segue a oferta do plano (*"leitura de candidatos de versoes compartilhadas"*). Sem política de escrita.

### 4.3. Tabela `versoes_plano`
Versões de um plano. Toda versão nasce **privada**; uma nova revisão cria nova versão e não sobrescreve calendários pessoais.
*   **Colunas:**
    *   `id` (UUID, Primary Key) e `plano_id` (UUID, Not Null, FK, `ON DELETE CASCADE`).
    *   `numero` (SMALLINT ≥ 1): único por plano.
    *   `autor_id` (UUID, Not Null, FK para `profiles`).
    *   `visibilidade` (TEXT, padrão `privada`): `privada` ou `compartilhada`. `compartilhada_em` (TIMESTAMPTZ) é preenchido se, e somente se, a versão estiver compartilhada.
    *   `criado_em` (TIMESTAMPTZ, Not Null).
*   **Criação:** todo plano recebe a versão 1 automaticamente (trigger após INSERT em `planos_ensino`). Os planos existentes ganharam a versão 1 na migração.
*   **Políticas RLS:** leitura pelo dono do plano ou, se compartilhada, por usuários que seguem a oferta do plano (função `pode_ler_versao`). Sem política de escrita: compartilhar e retirar passam pelo back-end (S8-B01).
*   **PDF:** compartilhar uma versão **não** expõe o PDF nem o registro do plano. Compartilhar o arquivo original exige autorização específica, a definir na S8-B01.

### 4.4. Tabelas `disciplinas`, `ofertas_turma` e `vinculos_turma`
Catálogo de turmas e turmas que o usuário segue. A disciplina abstrata (`disciplinas`) é separada da sua oferta em um semestre (`ofertas_turma`).
*   **`disciplinas`:** `origem` (`followw` | `manual`), `origem_id` (identificador na origem, opcional), `codigo`, `nome`, `unidade` e `nivel` (opcionais), `atualizado_na_origem_em`, `criado_em`, `atualizado_em`.
    *   **Identidade:** com `origem_id`, `(origem, origem_id)` é único. Sem ele, `(origem, código sem diferenciar maiúsculas, unidade, nível)` é único.
*   **`ofertas_turma`:** `disciplina_id` (FK, `ON DELETE RESTRICT`), `origem`, `origem_id` (opcional), `turma`, `ano` (2000–2100), `semestre` (1 ou 2, como no contrato da API), `atualizado_na_origem_em`, `sincronizado_em` (última sincronização bem-sucedida, para avisar catálogo desatualizado), `criado_em`, `atualizado_em`.
    *   **Identidade:** `(disciplina_id, turma, ano, semestre)` é único; ofertas de semestres diferentes são registros distintos. Com `origem_id`, `(origem, origem_id)` também é único.
*   **`vinculos_turma`:** chave primária `(user_id, oferta_id)`, `origem` (`autodeclarado`), `criado_em`. Seguir a mesma oferta de novo não duplica o vínculo. O vínculo é autodeclarado, sem comprovação de matrícula.
*   **Políticas RLS:** catálogo (`disciplinas`, `ofertas_turma`) com leitura pública; `vinculos_turma` com leitura só do próprio usuário. Sem políticas de escrita: a sincronização com o Followw (S7-B03) e seguir/deixar de seguir (S7-F02) passam pelo back-end.

### 4.5. Importação para a agenda
`eventos_pessoais` registra a procedência em `origem_plano_id`, `origem_avaliacao_id` e `origem_versao_id`.
*   **Unicidade por usuário:** `(user_id, origem_avaliacao_id)` é único. Cada usuário importa um candidato no máximo uma vez, e dois colegas podem importar o mesmo candidato de uma versão compartilhada para agendas independentes. Até a S7-D01, a unicidade era global (`origem_avaliacao_id`).
*   **Índice:** `(user_id, origem_versao_id)`, para consultar o que o usuário importou de cada versão.
