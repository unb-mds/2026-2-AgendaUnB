---
title: "Especificação do banco de dados"
description: "Documento que descreve a estrutura física DDL e as políticas de segurança RLS do banco de dados da Agenda UnB no Supabase."
---

Este documento descreve a estrutura física (DDL) atualizada do banco de dados do projeto **Agenda UnB**, incluindo as tabelas vigentes, seus relacionamentos e as Políticas de Segurança em Nível de Linha (Row Level Security - RLS) adotadas no Supabase para garantir o isolamento e a segurança dos dados.

---

## Tabelas de Domínio e Catálogos Globais

Estas tabelas armazenam informações estruturais transversais, utilizadas tanto em eventos públicos quanto privados.

### Tabela `campus`

Armazena as localizações físicas da Universidade de Brasília.

- **Colunas:**
  - `id` (UUID, Primary Key): Identificador único gerado automaticamente (`gen_random_uuid()`).
  - `nome` (TEXT, Not Null, Unique): Nome oficial do campus (ex: Darcy Ribeiro, FGA).
  - `created_at` (TIMESTAMPTZ): Data e hora de criação.
- **Políticas RLS:** Segurança em Nível de Linha habilitada.
  - **Leitura (SELECT):** Permitida para todos (`USING true`). Política: _"Permitir leitura pública de campus"_.

### Tabela `categories`

Armazena as categorias para classificação e coloração dos eventos na interface.

- **Colunas:**
  - `id` (UUID, Primary Key): Identificador único.
  - `nome` (TEXT, Not Null, Unique): Nome da categoria (ex: Prova, Aula, Lazer).
  - `cor` (TEXT): Código hexadecimal da cor.
  - `created_at` (TIMESTAMPTZ): Data e hora de criação.
- **Políticas RLS:** Segurança em Nível de Linha habilitada.
  - **Leitura (SELECT):** Permitida para todos (`USING true`). Política: _"Permitir leitura pública de categorias"_.

---

## Usuários e Perfis

### Tabela `profiles` (Esquema `public`)

Armazena os metadados dos usuários, sincronizada com a tabela nativa de autenticação (`auth.users`) do Supabase.

- **Colunas:**
  - `id` (UUID, Primary Key): Referência em cascata para `auth.users(id)`.
  - _(Nota: Metadados adicionais como nome, email e papel são gerenciados via triggers de sincronização no banco)._
- **Políticas RLS:**
  - **Leitura (SELECT):** Permitida para todos os visitantes e usuários (`USING true`). Política: _"perfis visiveis para todos"_.

---

## Tabelas Core: Eventos e Agenda

### Tabela `eventos` (Agenda Pública Institucional - RF14)

Eventos globais propostos por professores ou verificados pela IA.

- **Colunas:**
  - `id` (UUID, Primary Key): Identificador único.
  - `autor_id` (UUID, Not Null): Chave estrangeira para `profiles(id)` (`ON DELETE CASCADE`).
  - `titulo` (TEXT, Not Null): Título do evento. Validação: Mínimo de 3 caracteres (`CHECK (char_length(trim(titulo)) >= 3)`).
  - `descricao` (TEXT, Not Null): Detalhamento do evento.
  - `data_evento` (TIMESTAMPTZ, Not Null): Data e hora consolidadas do evento.
  - `localizacao` (TEXT): Local físico específico (ex: Sala S1, Auditório).
  - `link_externo` (TEXT): Link auxiliar ou de inscrição.
  - `campus_id` (UUID): Chave estrangeira para a tabela `campus(id)`.
  - `category_id` (UUID): Chave estrangeira para a tabela `categories(id)`.
  - `status` (TEXT, Not Null): Controle de moderação (`DEFAULT 'pendente'`). Validação: `CHECK (status in ('pendente', 'aprovado', 'rejeitado'))`.
  - `criado_em` (TIMESTAMPTZ, Not Null): Timestamp de criação (`DEFAULT now()`).
- **Políticas RLS:** Segurança em Nível de Linha habilitada.
  - **Leitura (SELECT):** Apenas eventos moderados. Política: _"eventos aprovados sao publicos"_ (`USING (status = 'aprovado')`).
  - **Criação (INSERT):** Apenas o próprio autor autenticado. Política: _"usuarios logados podem criar eventos"_ (`WITH CHECK (autor_id = (select auth.uid()))`).

### Tabela `eventos_pessoais` (Agenda Privada - RF09)

Agenda estritamente privada, gerenciada e visualizada unicamente por cada estudante.

- **Colunas:**
  - `id` (UUID, Primary Key): Identificador único.
  - `user_id` (UUID, Not Null): Chave estrangeira para `auth.users(id)` (`DEFAULT auth.uid()`).
  - `titulo` (TEXT, Not Null): Título do compromisso. Validação: Mínimo de 3 caracteres.
  - `descricao` (TEXT): Notas extras.
  - `data_hora` (TIMESTAMPTZ, Not Null): Data e hora do compromisso.
  - `campus_id` (UUID): Chave estrangeira para a tabela `campus(id)`.
  - `category_id` (UUID): Chave estrangeira para a tabela `categories(id)`.
  - `criado_em` (TIMESTAMPTZ, Not Null): Timestamp de criação.
- **Políticas RLS:** Segurança em Nível de Linha habilitada (Isolamento Total).
  - **Leitura (SELECT):** Política _"utilizadores podem ver os seus proprios eventos"_ (`USING (auth.uid() = user_id)`).
  - **Criação (INSERT):** Política _"utilizadores podem criar eventos"_ (`WITH CHECK (auth.uid() = user_id)`).
  - **Edição (UPDATE):** Política _"utilizadores podem atualizar os seus proprios eventos"_ (`USING (auth.uid() = user_id)` e `WITH CHECK`).
  - **Exclusão (DELETE):** Política _"utilizadores podem deletar os seus proprios eventos"_ (`USING (auth.uid() = user_id)`).

---

## Organizador Acadêmico

### Tabela `planos_ensino`

Documentos enviados pelos professores para o sistema de IA.

- **Colunas:**
  - `id` (UUID, Primary Key).
  - `professor_id` (UUID, Not Null): Chave estrangeira para `profiles(id)` (`ON DELETE CASCADE`).
  - `disciplina` (TEXT, Not Null): Nome da disciplina.
  - `turma` (TEXT, Not Null): Código da turma.
  - `arquivo_url` (TEXT): Caminho do PDF/Documento no Supabase Storage.
  - `criado_em` (TIMESTAMPTZ, Not Null).
- **Políticas RLS:** Segurança em Nível de Linha habilitada.

### Tabela `avaliacoes`

Datas extraídas automaticamente da tabela de planos de ensino.

- **Colunas:**
  - `id` (UUID, Primary Key).
  - `plano_id` (UUID, Not Null): Chave estrangeira apontando para `planos_ensino(id)` (`ON DELETE CASCADE`).
  - `titulo` (TEXT, Not Null): Nome da avaliação/trabalho.
  - `data_avaliacao` (TIMESTAMPTZ, Not Null): Data programada extraída.
  - `criado_em` (TIMESTAMPTZ, Not Null).
- **Políticas RLS:** Segurança em Nível de Linha habilitada.
  - **Leitura (SELECT):** Pública para os alunos. Política: _"avaliacoes sao publicas"_ (`USING true`).
