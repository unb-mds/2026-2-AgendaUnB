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

### 4.1. Tabela `ofertas_turma`
Identifica uma oferta canônica de disciplina, turma e período. A importação deve usar `origem` + `id_origem` + `periodo` quando a fonte pública fornecer um identificador estável. Sem esse identificador, a chave composta usa origem, código/nome da disciplina, turma, período, unidade e nível. Assim, a mesma turma em semestres diferentes permanece distinta.

* **Colunas:** `id` (UUID, PK), `origem`, `id_origem`, `codigo_disciplina`, `nome_disciplina`, `numero_turma`, `periodo`, `unidade`, `nivel`, `atualizado_em` e `criado_em`.
* **RLS:** leitura permitida a usuários autenticados; importação e manutenção do catálogo ficam reservadas ao backend/serviço.

### 4.2. Tabela `vinculos_turma`
Registra que um usuário acompanha uma oferta. A chave primária composta `(user_id, oferta_id)` impede duplicar o vínculo e o índice inverso permite consultar rapidamente colegas de uma oferta.

* **Colunas:** `user_id` e `oferta_id` (PK/FK), `criado_em`.
* **RLS:** usuário autenticado consulta, cria e remove apenas os próprios vínculos.

### 4.3. Tabela `planos_ensino`
Cada documento representa uma versão de plano, com dono dos dados separado de autoria. `oferta_id` pode ficar nulo enquanto turma/período não forem conhecidos pelo fluxo atual de upload.

* **Campos existentes:** `id`, `user_id`, arquivo, tamanho, estado do processamento e metadados atuais.
* **Novos campos:** `autor_id` (responsável pela autoria), `oferta_id` (FK para a oferta), `versao` (inteiro positivo) e `visibilidade` (`privado` ou `compartilhado`).
* **Restrições e índices:** unicidade de `(oferta_id, autor_id, versao)` e índice `(user_id, oferta_id, versao)` para consultas/importação.
* **RLS:** o dono sempre pode consultar o próprio plano. Um colega só consulta quando o documento está compartilhado e possui vínculo com a mesma oferta. Inserção, edição e exclusão continuam limitadas ao dono.
* **Storage:** mantém-se o bucket privado e a leitura pelo dono. A leitura por colega segue a mesma condição de plano compartilhado e vínculo com a oferta.

### 4.4. Tabela `avaliacoes`
Cada candidata continua subordinada ao plano (`plano_id`) e mantém página/trecho de origem para evidência. A leitura segue as permissões do plano pai: dono, ou colega vinculado se e somente se o plano foi compartilhado.

### 4.5. Compatibilidade de dados antigos
A migração `20261110000000` cria uma oferta legada isolada por plano antigo, porque os registros anteriores não informam período ou identificador externo. Ela não combina ofertas por nome/turma nem apaga PDFs ou registros. Essa escolha preserva os dados sem afirmar um semestre que não está registrado. A limpeza de arquivos após extração depende do processador, ainda não implementado.
