# Arquitetura de Dados - Agenda UnB

Este documento apresenta a estrutura visual de dados adotada no banco de dados Supabase do MVP da Agenda UnB. Ele inclui o Diagrama Entidade-Relacionamento (DER) para visualização da arquitetura, descrevendo como as tabelas interagem. O Dicionário de Dados detalhado (DDL) encontra-se no documento `modelo_fisico.md`.

---

## 1. Diagrama Entidade-Relacionamento (DER)

O diagrama abaixo ilustra as relações entre as 7 tabelas que compõem o banco de dados.

---

@startuml
skinparam handwritten false
skinparam linetype ortho

entity "PROFILES" {
  * id : UUID <<PK>> (auth.users.id)
  --
  * nome_completo : TEXT
  * email : TEXT <<Unique, Imutável>>
  papel : TEXT
}

entity "CAMPUS" {
  * id : UUID <<PK>>
  --
  * nome : TEXT <<Unique>>
  created_at : TIMESTAMPTZ
}

entity "CATEGORIES" {
  * id : UUID <<PK>>
  --
  * nome : TEXT <<Unique>>
  cor : TEXT
  created_at : TIMESTAMPTZ
}

entity "EVENTOS" {
  * id : UUID <<PK>>
  --
  * autor_id : UUID <<FK>>
  * titulo : TEXT
  * descricao : TEXT
  * data_evento : TIMESTAMPTZ
  localizacao : TEXT
  link_externo : TEXT
  campus_id : UUID <<FK>>
  category_id : UUID <<FK>>
  * status : TEXT
  created_at : TIMESTAMPTZ
}

entity "EVENTOS_PESSOAIS" {
  * id : UUID <<PK>>
  --
  * user_id : UUID <<FK>>
  * titulo : TEXT
  descricao : TEXT
  * data_hora : TIMESTAMPTZ
  campus_id : UUID <<FK>>
  category_id : UUID <<FK>>
  created_at : TIMESTAMPTZ
}

entity "PLANOS_ENSINO" {
  * id : UUID <<PK>>
  --
  * user_id : UUID <<FK>>
  autor_id : UUID <<FK>>
  oferta_id : UUID <<FK>>
  * versao : INTEGER
  * visibilidade : TEXT
  arquivo_url : TEXT
  created_at : TIMESTAMPTZ
}

entity "OFERTAS_TURMA" {
  * id : UUID <<PK>>
  --
  * origem : TEXT
  id_origem : TEXT
  codigo_disciplina : TEXT
  * nome_disciplina : TEXT
  * numero_turma : TEXT
  * periodo : TEXT
  unidade : TEXT
  nivel : TEXT
  * atualizado_em : TIMESTAMPTZ
}

entity "VINCULOS_TURMA" {
  * user_id : UUID <<PK, FK>>
  * oferta_id : UUID <<PK, FK>>
  * criado_em : TIMESTAMPTZ
}

entity "AVALIACOES" {
  * id : UUID <<PK>>
  --
  * plano_id : UUID <<FK>>
  * titulo : TEXT
  * data_avaliacao : TIMESTAMPTZ
  created_at : TIMESTAMPTZ
}

PROFILES ||--o{ EVENTOS : "cria"
PROFILES ||--o{ EVENTOS_PESSOAIS : "possui"
PROFILES ||--o{ PLANOS_ENSINO : "dono"
PROFILES ||--o{ PLANOS_ENSINO : "autor"
PROFILES ||--o{ VINCULOS_TURMA : "acompanha"
OFERTAS_TURMA ||--o{ VINCULOS_TURMA : "tem alunos"
OFERTAS_TURMA ||--o{ PLANOS_ENSINO : "tem versões"

CAMPUS ||--o{ EVENTOS : "localiza"
CAMPUS ||--o{ EVENTOS_PESSOAIS : "localiza"

CATEGORIES ||--o{ EVENTOS : "classifica"
CATEGORIES ||--o{ EVENTOS_PESSOAIS : "classifica"

PLANOS_ENSINO ||--o{ AVALIACOES : "gera"
@enduml

Planos antigos sem período ou identificador de origem recebem ofertas legadas isoladas pela migração S7-D01. Isso evita fundir turmas de semestres potencialmente diferentes.
