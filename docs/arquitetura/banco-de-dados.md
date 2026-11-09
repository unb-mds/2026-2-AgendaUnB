---
title: "Especificação do banco de dados"
description: "Documento que descreve a estrutura física DDL e as políticas de segurança RLS do banco de dados da Agenda UnB no Supabase."
---

Este documento descreve a estrutura física (DDL) atualizada do banco de dados do projeto **Agenda UnB**, com as tabelas e as regras de acesso no Supabase. Consulte o [diagrama de relacionamentos](modelo-de-dados.md) e as migrações em `supabase/migrations/`.

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
Eventos publicados por professor/admin e sugestões da comunidade sujeitas à moderação. As regras posteriores à R1 estão no [guia de moderação](../painel-administrativo.md).
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

Migrações de referência: `20261026120000_upload_planos_ensino.sql` (#40) e `20261027120000_planos_particulares_e_candidatos.sql` (S6-D01, #53).

Fluxo: o upload (#40) cria o plano como `pendente`; o processamento (S6-B01) passa para `processando`, grava candidatos e termina em `concluido` ou `falha`; a revisão (S6-B02) marca cada candidato como `confirmado` ou `descartado`. Nenhum evento pessoal é criado sem confirmação do estudante.

### 4.1. Tabela `planos_ensino`
Esquema atual de uploads de plano de ensino. O campo `tipo` admite os valores legados `particular` e `oficial`. As colunas de arquivo e rastreamento vêm da #40 (`20261026120000`). Tipo, estados, erro sanitizado, período e dados da IA vêm da S6-D01 (`20261027120000`). A Release 2 separa autoria, procedência e visibilidade e prevê descarte do PDF. [Plano de migração](../atualizacoes.md#contratos-da-release-2)
*   **Dono e tipo:**
    *   `id` (UUID, Primary Key).
    *   `user_id` (UUID, Not Null): dono, quem enviou. FK para `profiles(id)` (`ON DELETE CASCADE`).
    *   `tipo` (TEXT, Not Null, padrão `particular`): `particular` ou `oficial`.
    *   `professor_id` (UUID): somente em plano oficial, professor responsável pela turma. Em plano particular é sempre nulo.
    *   `disciplina` (TEXT) e `turma` (TEXT): turma obrigatória somente em plano oficial.
    *   `ano` (SMALLINT, 2000–2100) e `semestre` (SMALLINT, 1 ou 2): opcionais no upload atual.
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
*   **Políticas RLS:** A migração `20261107000000` restringe a leitura ao dono e reserva alterações de estado à API, ao worker e à RPC autorizada.

### 4.2. Tabela `candidatos_avaliacao`
Avaliações sugeridas pela IA. São sugestões: só viram compromisso após confirmação do estudante.
*   **Colunas:**
    *   `id` (UUID, Primary Key).
    *   `plano_id` (UUID, Not Null): FK para `planos_ensino(id)` (`ON DELETE CASCADE`).
    *   `execucao` (SMALLINT ≥ 1) e `ordem` (SMALLINT ≥ 0): execução que gerou o candidato e posição na saída.
    *   `titulo` (TEXT, 1–300), `tipo` (`prova`, `trabalho`, `projeto`, `seminario`, `lista`, `entrega`, `outro`).
    *   `data_sugerida` (DATE) e `hora_sugerida` (TIME): opcionais; hora exige data. A hora é a hora local escrita no plano, sem fuso; o fuso é definido na confirmação.
    *   `campos_ambiguos` (TEXT[], padrão vazio): subconjunto de `titulo`, `tipo`, `data`, `hora`. `ambiguo` (BOOLEAN) é calculado a partir dele.
    *   `pagina_origem` (SMALLINT ≥ 1) e `trecho_origem` (TEXT, 1–1000): evidência obrigatória.
    *   `provedor_ia`, `modelo_ia`, `versao_processamento` (TEXT, Not Null).
    *   `status` (TEXT, padrão `pendente`): `pendente`, `descartado` ou `confirmado`. `revisado_em` é preenchido se, e somente se, o status não for `pendente`.
    *   `evento_pessoal_id` (UUID, Unique): FK para `eventos_pessoais(id)` (`ON DELETE SET NULL`). Só em candidato `confirmado`.
    *   `criado_em` (TIMESTAMPTZ, Not Null).
*   **Sem duplicação:** `(plano_id, execucao, ordem)` é único. O worker grava com `ON CONFLICT (plano_id, execucao, ordem) DO NOTHING`, então repetir a mesma execução não duplica. Reprocessar gera nova execução e mantém as anteriores como histórico.
*   **Vínculo com a agenda:**
    *   Um candidato gera no máximo um evento, e um evento vem de no máximo um candidato (unicidade de `evento_pessoal_id`).
    *   Editar o evento pessoal não altera o candidato: o candidato guarda o que a IA extraiu, e o evento guarda o que o estudante decidiu.
    *   Excluir o evento pessoal deixa `evento_pessoal_id` nulo; o candidato continua `confirmado` e não é recriado em nova confirmação.
    *   Procedência de um evento: `eventos_pessoais` → `candidatos_avaliacao.evento_pessoal_id` → `planos_ensino`.
*   **Políticas RLS:** Leitura restrita ao dono do plano pela migração `20261107000000`.

### 4.3. Tabela `avaliacoes`
Tabela legada de avaliações, estendida pela migração `20261029160000` para a consulta e confirmação de candidatos na API de planos. O desenho de processamento por execução usa a tabela `candidatos_avaliacao` descrita acima.
*   **Colunas:**
    *   `id` (UUID, Primary Key).
    *   `plano_id` (UUID, Not Null): Chave estrangeira apontando para `planos_ensino(id)` (`ON DELETE CASCADE`).
    *   `titulo` (TEXT, Not Null): Nome da avaliação/trabalho.
    *   `data_avaliacao` (TIMESTAMPTZ, opcional): Data sugerida.
    *   `criado_em` (TIMESTAMPTZ, Not Null).
*   **Políticas RLS:** Segurança em Nível de Linha habilitada.
    *   **Leitura (SELECT):** Restrita ao dono do plano. A migração `20261029160000` removeu a política pública e acrescentou tipo, ambiguidade, página e trecho de origem, estado e metadados de processamento. Na confirmação, a API grava procedência em `eventos_pessoais`. O índice único parcial de `origem_avaliacao_id` impede duplicação.

## 5. Eventos salvos e notificações

`eventos_salvos` vincula um perfil a um evento público com chave composta `(user_id, event_id)`. `notificacoes` referencia o perfil destinatário e pode referenciar o evento que originou o aviso. Consulte as políticas, a implantação e os cenários de verificação nos guias de [eventos salvos](../eventos-salvos.md) e [painel administrativo](../painel-administrativo.md).

## Evolução de candidatos na R2

Toda data extraída começa como candidata. Somente a confirmação explícita do usuário a transforma em avaliação efetiva na sua agenda; em versões compartilhadas, essa decisão pertence a cada conta. A revisão deve ser breve: mostrar candidatos em uma lista, permitir selecionar vários e confirmar o lote em uma única ação, destacar apenas campos ambíguos que exigem correção e preservar as escolhas durante ajustes. Não exigir uma sequência de confirmações por item nem importar automaticamente. Avaliar a fluidez na homologação com o tempo e as dificuldades observadas, sem inventar um limite numérico ainda não acordado.

O estado de domínio “candidata” não determina o nome de uma tabela. A API atual usa `avaliacoes`, enquanto o desenho por execução usa `candidatos_avaliacao`. A escolha da estrutura física unificada e sua migração permanece pendente; não presumir que o worker e a API já compartilham o mesmo armazenamento. A implementação da R2 precisa alinhar escrita, consulta, confirmação e procedência antes da homologação.

Na R2, exigir `Idempotency-Key` por ação de confirmação, vinculada à conta, à operação e ao conteúdo do lote. Repetições da mesma ação usam a mesma chave; payload diferente com a mesma chave retorna 409. Persistir a operação e seus itens na mesma transação da confirmação e serializar requisições concorrentes. A exclusão do evento preserva o registro da importação e da operação: repetir a chave antiga não recria o evento nem reativa o vínculo. Reimportar exige o comando explícito “Adicionar novamente”, uma nova chave e nova verificação de acesso, versão e datas. Manter no máximo um evento ativo por `(user_id, version_id, candidate_id)`, mesmo com chaves diferentes; novas ações após exclusão não apagam o histórico das anteriores. O resultado de retry informa quando o evento anteriormente criado já foi removido. A transição dos clientes legados deve ser documentada antes de tornar a chave obrigatória; não inventar uma chave nova a cada retry.
