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
    *   `nome_completo` (até 200 caracteres), `email` (imutável), `papel` (`student`, `professor`, `admin`), `avatar_url` (somente `https`), `criado_em`, `atualizado_em`.
*   **Criação:** o trigger `on_auth_user_created` cria o perfil no cadastro. O papel `professor` exige e-mail `@unb.br` **confirmado**: cadastro ainda não confirmado nasce `student` e é promovido pelo trigger `on_auth_user_email_confirmed` quando o endereço é confirmado. `admin` nunca vem do cadastro.
*   **Políticas RLS:**
    *   **Leitura (SELECT):** o próprio usuário lê o seu perfil; admins leem todos. Visitantes não têm acesso.
    *   **Atualização (UPDATE):** o próprio usuário, apenas em `nome_completo`, `avatar_url` e `papel`. A mudança de papel pelo navegador só aceita `student → professor` com e-mail institucional confirmado; as demais passam pelas RPCs administrativas.

### 2.2. Tabela `auditoria_papeis`
Registra toda mudança de papel, por qualquer caminho (RPC do painel, autopromoção, confirmação de e-mail, back-end ou SQL): `usuario_id`, `ator_id` (nulo quando não havia sessão de usuário), `papel_anterior`, `papel_novo` e `criado_em`. Somente admins leem; ninguém altera pela API.

### 2.3. Privilégios e funções
Desde `20261111130000`, o `GRANT` acompanha as políticas: visitantes só leem o catálogo público (`eventos` aprovados, `campus`, `categories`, `disciplinas`, `ofertas_turma`), `TRUNCATE` não é concedido à API e funções novas não são executáveis via `/rpc` sem `GRANT EXECUTE` explícito. As regras para novas migrações estão em [Verificação de segurança](../processo/seguranca.md#regras-para-novas-migracoes).

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

Migrações de referência: `20261026120000_upload_planos_ensino.sql` (#40), `20261027120000_planos_particulares_e_candidatos.sql` (S6-D01, #53), `20261029160000_syllabus_review_confirmation.sql` (S6-B02), `20261107000000_planos_escrita_via_backend.sql` e `20261109120000_turmas_vinculos_versoes.sql` (S7-D01, #69).

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
*   **Turma:** `oferta_id` (UUID, opcional) liga o plano a uma oferta de `ofertas_turma` (`ON DELETE SET NULL`). Planos antigos e envios sem turma continuam válidos.
*   **Políticas RLS:** A migração `20261107000000` restringe a leitura ao dono e reserva alterações de estado à API, ao worker e à RPC autorizada. O registro do plano e o caminho do arquivo continuam visíveis só ao dono, mesmo quando uma versão é compartilhada.

### 4.2. Tabela `avaliacoes` (candidatos)
Tabela física única dos candidatos extraídos dos planos, decidida na S7-D01 com a equipe: é a que a API já usa na consulta e na confirmação. A tabela `candidatos_avaliacao` (#53), que nenhum código usava, foi removida em `20261109120000`, junto com a função `confirmar_candidatos_transacional` (S6-D02), que só operava sobre ela. A confirmação é feita pela API.
*   **Colunas:**
    *   `id` (UUID, Primary Key) e `plano_id` (UUID, Not Null, FK para `planos_ensino`, `ON DELETE CASCADE`).
    *   `versao_id` (UUID, Not Null): versão do plano a que o candidato pertence. A FK composta `(plano_id, versao_id)` → `versoes_plano(plano_id, id)` impede apontar para a versão de outro plano. Quando omitido no INSERT, um trigger usa a versão mais recente do plano.
    *   `ordem` (SMALLINT ≥ 0, opcional): posição do candidato na versão. `(versao_id, ordem)` é único, para reprocessar sem duplicar.
    *   `titulo` (TEXT, Not Null), `data_avaliacao` (TIMESTAMPTZ, opcional), `tipo`, `ambiguo`, `pagina_origem`, `trecho_origem`, `status`, `versao_processamento` e `provedor` (acrescentados em `20261029160000`).
*   **Políticas RLS:** leitura pelo dono do plano e, quando a versão estiver compartilhada, por quem segue a oferta do plano (*"leitura de candidatos de versoes compartilhadas"*). Sem política de escrita.

### 4.3. Tabela `versoes_plano`
Versões de um plano (ADR-010). Toda versão nasce **privada**; uma nova revisão cria nova versão e não sobrescreve calendários pessoais.
*   **Colunas:**
    *   `id` (UUID, Primary Key) e `plano_id` (UUID, Not Null, FK, `ON DELETE CASCADE`). `numero` (SMALLINT ≥ 1) é único por plano.
    *   `autor_id` (UUID, Not Null, FK para `profiles`) e `autor_papel` (`student`, `professor` ou `admin`): papel do autor no momento da criação. Não é evidência institucional.
    *   `versao_origem_id` (UUID, opcional): versão revisada que originou esta (`ON DELETE SET NULL`); nunca a própria versão.
    *   `procedencia_institucional` (BOOLEAN, padrão falso): herdada da versão de origem. O papel professor/admin não a cria sozinho.
    *   `visibilidade` (padrão `privada`): `privada` ou `compartilhada`. `compartilhada_em` é preenchido se, e somente se, a versão estiver compartilhada.
*   **Criação:** todo plano recebe a versão 1 automaticamente (trigger após INSERT em `planos_ensino`), com o papel atual do dono. Os planos existentes ganharam a versão 1 na migração.
*   **Políticas RLS:** leitura pelo dono do plano ou, se compartilhada, por usuários que seguem a oferta do plano (função `pode_ler_versao`). Sem política de escrita: compartilhar, revisar e retirar passam pelo back-end (S8-B01).
*   **Arquivo:** compartilhar uma versão não expõe o registro do plano nem o arquivo. A retenção do PDF segue a ADR-003.

### 4.4. Tabelas `disciplinas`, `ofertas_turma` e `vinculos_turma`
Catálogo de turmas (ADR-009) e turmas que o usuário segue. A disciplina abstrata (`disciplinas`) é separada da sua oferta em um semestre (`ofertas_turma`), e cada uma tem UUID local imutável.
*   **`disciplinas`:** `origem` (`followw` | `manual`), `origem_id` (opcional), `codigo`, `nome`, `unidade` e `nivel` (opcionais), `atualizado_na_origem_em`.
    *   **Identidade:** com `origem_id`, `(origem, origem_id)` é único. Sem ele, `(origem, código sem diferenciar maiúsculas, unidade, nível)` é único.
*   **`ofertas_turma`:** `disciplina_id` (FK, `ON DELETE RESTRICT`), `origem`, `origem_id` (opcional), `turma` (texto, preservando zeros), `ano` (2000–2100), `semestre` (1 ou 2), `professor` e `horarios` (atributos atualizáveis, fora da identidade), `atualizado_na_origem_em` e `sincronizado_em` (última sincronização bem-sucedida, para responder com `stale`).
    *   **Identidade:** `(disciplina_id, turma, ano, semestre)` é único; ofertas de semestres diferentes são registros distintos. Com `origem_id`, `(origem, origem_id)` também é único.
*   **`vinculos_turma`:** chave primária `(user_id, oferta_id)`, `origem` (`autodeclarado`), `criado_em`. Seguir a mesma oferta de novo não duplica. O vínculo é autodeclarado e não prova matrícula.
*   **Políticas RLS:** catálogo com leitura pública; vínculos com leitura só do próprio usuário. Sem políticas de escrita: a sincronização (S7-B03) e seguir/deixar de seguir (S7-F02) passam pelo back-end.

### 4.5. Importação para a agenda
`eventos_pessoais` registra a procedência em `origem_plano_id`, `origem_avaliacao_id` e `origem_versao_id` (FK para `versoes_plano`, `ON DELETE SET NULL`).
*   **Unicidade por usuário:** `(user_id, origem_avaliacao_id)` é único (índice parcial). Como cada candidato pertence a uma única versão, isso equivale à unicidade `(user_id, version_id, candidate_id)` da ADR-010. Até a S7-D01, a unicidade era global, e um usuário podia bloquear a confirmação de outro.
*   **Índice:** `(user_id, origem_versao_id)`.

## 5. Eventos salvos e notificações

Eventos públicos são gravados somente pela API e pelas RPCs de moderação: o `INSERT` direto pelo navegador foi removido em `20261111130000`. O banco valida, em qualquer caminho, que `link_externo` usa `http(s)` e que título, descrição e local respeitam os limites da API.

`eventos_salvos` vincula um perfil a um evento público com chave composta `(user_id, event_id)`. `notificacoes` referencia o perfil destinatário e pode referenciar o evento que originou o aviso. Consulte as políticas, a implantação e os cenários de verificação nos guias de [eventos salvos](../eventos-salvos.md) e [painel administrativo](../painel-administrativo.md).

## Evolução de candidatos na R2

Toda data extraída começa como candidata. Somente a confirmação explícita do usuário a transforma em avaliação efetiva na sua agenda; em versões compartilhadas, essa decisão pertence a cada conta. A revisão deve ser breve: mostrar candidatos em uma lista, permitir selecionar vários e confirmar o lote em uma única ação, destacar apenas campos ambíguos que exigem correção e preservar as escolhas durante ajustes. Não exigir uma sequência de confirmações por item nem importar automaticamente. Avaliar a fluidez na homologação com o tempo e as dificuldades observadas, sem inventar um limite numérico ainda não acordado.

O estado de domínio “candidata” não determina o nome de uma tabela. Desde a S7-D01 (`20261109120000`), a estrutura física unificada é `avaliacoes`, ligada à versão do plano; `candidatos_avaliacao` foi removida. O worker deve gravar candidatos em `avaliacoes`, informando `versao_id` e `ordem`.

Na R2, exigir `Idempotency-Key` por ação de confirmação, vinculada à conta, à operação e ao conteúdo do lote. Repetições da mesma ação usam a mesma chave; payload diferente com a mesma chave retorna 409. Persistir a operação e seus itens na mesma transação da confirmação e serializar requisições concorrentes. A exclusão do evento preserva o registro da importação e da operação: repetir a chave antiga não recria o evento nem reativa o vínculo. Reimportar exige o comando explícito “Adicionar novamente”, uma nova chave e nova verificação de acesso, versão e datas. Manter no máximo um evento ativo por `(user_id, version_id, candidate_id)`, mesmo com chaves diferentes; novas ações após exclusão não apagam o histórico das anteriores. O resultado de retry informa quando o evento anteriormente criado já foi removido. A transição dos clientes legados deve ser documentada antes de tornar a chave obrigatória; não inventar uma chave nova a cada retry.


## Worker e autorização do texto

Preparação local, autorização específica, fila recuperável e candidatos privados estão descritos no [protocolo S7](../processamento-planos-s7.md) e no [registro de validação](../s7-b01-validacao.md). O worker foi alinhado à tabela oficial `avaliacoes` e às versões de S7-D01; nenhuma migração foi aplicada na nuvem.
