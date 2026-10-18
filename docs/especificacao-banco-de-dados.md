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

### 4.1. Tabela `planos_ensino`
Documentos enviados pelos professores para o sistema de IA.
*   **Colunas:**
    *   `id` (UUID, Primary Key).
    *   `professor_id` (UUID, Not Null): Chave estrangeira para `profiles(id)` (`ON DELETE CASCADE`).
    *   `disciplina` (TEXT, Not Null): Nome da disciplina.
    *   `turma` (TEXT, Not Null): Código da turma.
    *   `arquivo_url` (TEXT): Caminho do PDF/Documento no Supabase Storage.
    *   `criado_em` (TIMESTAMPTZ, Not Null).
*   **Políticas RLS:** Segurança em Nível de Linha habilitada.

### 4.2. Tabela `avaliacoes`
Datas extraídas automaticamente da tabela de planos de ensino.
*   **Colunas:**
    *   `id` (UUID, Primary Key).
    *   `plano_id` (UUID, Not Null): Chave estrangeira apontando para `planos_ensino(id)` (`ON DELETE CASCADE`).
    *   `titulo` (TEXT, Not Null): Nome da avaliação/trabalho.
    *   `data_avaliacao` (TIMESTAMPTZ, Not Null): Data programada extraída.
    *   `criado_em` (TIMESTAMPTZ, Not Null).
*   **Políticas RLS:** Segurança em Nível de Linha habilitada.
    *   **Leitura (SELECT):** Pública para os alunos. Política: *"avaliacoes sao publicas"* (`USING true`).
