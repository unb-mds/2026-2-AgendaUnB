# Arquitetura de Dados - Agenda UnB

Este documento apresenta a estrutura visual de dados adotada no banco de dados Supabase do MVP da Agenda UnB. Ele inclui o Diagrama Entidade-Relacionamento (DER) para visualização da arquitetura, descrevendo como as tabelas interagem. O Dicionário de Dados detalhado (DDL) encontra-se no documento `modelo_fisico.md`.

---

## 1. Diagrama Entidade-Relacionamento (DER)

O diagrama abaixo ilustra as relações entre as tabelas centrais do banco de dados. As tabelas `eventos_salvos` e `notificacoes` estão descritas em [Especificação do Banco](especificacao-banco-de-dados.md) e em [Painel administrativo](painel-administrativo.md).

---

```plantuml
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
  origem_plano_id : UUID
  origem_avaliacao_id : UUID
  origem_versao_id : UUID <<FK>>
  created_at : TIMESTAMPTZ
  .. Unique (user_id, origem_avaliacao_id) ..
}

entity "PLANOS_ENSINO" {
  * id : UUID <<PK>>
  --
  * user_id : UUID <<FK>> (dono)
  * tipo : TEXT (particular | oficial)
  professor_id : UUID <<FK>> (só oficial)
  disciplina : TEXT
  turma : TEXT (só oficial)
  ano : SMALLINT
  semestre : SMALLINT (1 | 2)
  nome_arquivo : TEXT
  caminho_arquivo : TEXT <<Unique>>
  tamanho_bytes : BIGINT
  * tipo_arquivo : TEXT (pdf)
  paginas : SMALLINT
  * status : TEXT (pendente | processando | concluido | falha)
  * quantidade_eventos : INT
  * execucao_atual : SMALLINT
  provedor_ia : TEXT
  modelo_ia : TEXT
  versao_processamento : TEXT
  erro_codigo : TEXT
  erro : TEXT
  processamento_iniciado_em : TIMESTAMPTZ
  processado_em : TIMESTAMPTZ
  plano_oficial_id : UUID <<FK>>
  arquivo_url : TEXT (legado)
  criado_em : TIMESTAMPTZ
  atualizado_em : TIMESTAMPTZ
}

entity "AVALIACOES" {
  * id : UUID <<PK>>
  --
  * plano_id : UUID <<FK>>
  * versao_id : UUID <<FK>>
  ordem : SMALLINT
  * titulo : TEXT
  data_avaliacao : TIMESTAMPTZ
  tipo : TEXT
  * ambiguo : BOOLEAN
  pagina_origem : INT
  trecho_origem : TEXT
  * status : TEXT
  versao_processamento : TEXT
  provedor : TEXT
  created_at : TIMESTAMPTZ
  .. Unique (versao_id, ordem) ..
}

entity "VERSOES_PLANO" {
  * id : UUID <<PK>>
  --
  * plano_id : UUID <<FK>>
  * numero : SMALLINT
  * autor_id : UUID <<FK>>
  * visibilidade : TEXT (privada | compartilhada)
  compartilhada_em : TIMESTAMPTZ
  criado_em : TIMESTAMPTZ
  .. Unique (plano_id, numero) ..
}

entity "DISCIPLINAS" {
  * id : UUID <<PK>>
  --
  * origem : TEXT (followw | manual)
  origem_id : TEXT
  * codigo : TEXT
  * nome : TEXT
  unidade : TEXT
  nivel : TEXT
  atualizado_na_origem_em : TIMESTAMPTZ
}

entity "OFERTAS_TURMA" {
  * id : UUID <<PK>>
  --
  * disciplina_id : UUID <<FK>>
  * origem : TEXT
  origem_id : TEXT
  * turma : TEXT
  * ano : SMALLINT
  * semestre : SMALLINT (1 | 2)
  atualizado_na_origem_em : TIMESTAMPTZ
  sincronizado_em : TIMESTAMPTZ
  .. Unique (disciplina_id, turma, ano, semestre) ..
}

entity "VINCULOS_TURMA" {
  * user_id : UUID <<PK, FK>>
  * oferta_id : UUID <<PK, FK>>
  --
  * origem : TEXT (autodeclarado)
  criado_em : TIMESTAMPTZ
}

PROFILES ||--o{ EVENTOS : "cria"
PROFILES ||--o{ EVENTOS_PESSOAIS : "possui"
PROFILES ||--o{ PLANOS_ENSINO : "envia (user_id)"
PROFILES |o--o{ PLANOS_ENSINO : "responde pela turma (professor_id)"

CAMPUS ||--o{ EVENTOS : "localiza"
CAMPUS ||--o{ EVENTOS_PESSOAIS : "localiza"

CATEGORIES ||--o{ EVENTOS : "classifica"
CATEGORIES ||--o{ EVENTOS_PESSOAIS : "classifica"

PLANOS_ENSINO ||--o{ AVALIACOES : "gera"
PLANOS_ENSINO |o--o{ PLANOS_ENSINO : "plano_oficial_id"
PLANOS_ENSINO ||--|{ VERSOES_PLANO : "versiona"
VERSOES_PLANO ||--o{ AVALIACOES : "contém"
AVALIACOES |o--o{ EVENTOS_PESSOAIS : "importada por usuário"
VERSOES_PLANO |o--o{ EVENTOS_PESSOAIS : "origem"
PROFILES ||--o{ VERSOES_PLANO : "autor"
DISCIPLINAS ||--o{ OFERTAS_TURMA : "ofertada em"
OFERTAS_TURMA |o--o{ PLANOS_ENSINO : "oferta_id"
PROFILES ||--o{ VINCULOS_TURMA : "segue"
OFERTAS_TURMA ||--o{ VINCULOS_TURMA : "seguida por"
@enduml
```
