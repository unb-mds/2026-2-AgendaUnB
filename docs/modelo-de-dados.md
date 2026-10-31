# Arquitetura de Dados - Agenda UnB

Este documento apresenta a estrutura visual de dados adotada no banco de dados Supabase do MVP da Agenda UnB. Ele inclui o Diagrama Entidade-Relacionamento (DER) para visualização da arquitetura, descrevendo como as tabelas interagem. O Dicionário de Dados detalhado (DDL) encontra-se no documento `modelo_fisico.md`.

---

## 1. Diagrama Entidade-Relacionamento (DER)

O diagrama abaixo ilustra as relações entre as tabelas centrais do banco de dados. As tabelas `eventos_salvos` e `notificacoes` estão descritas em [Especificação do Banco](especificacao-banco-de-dados.md) e em [Painel administrativo](painel-administrativo.md).

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
  * titulo : TEXT
  * data_avaliacao : TIMESTAMPTZ
  created_at : TIMESTAMPTZ
}

entity "CANDIDATOS_AVALIACAO" {
  * id : UUID <<PK>>
  --
  * plano_id : UUID <<FK>>
  * execucao : SMALLINT
  * ordem : SMALLINT
  * titulo : TEXT
  * tipo : TEXT
  data_sugerida : DATE
  hora_sugerida : TIME
  * campos_ambiguos : TEXT[]
  ambiguo : BOOLEAN (calculado)
  * pagina_origem : SMALLINT
  * trecho_origem : TEXT
  * provedor_ia : TEXT
  * modelo_ia : TEXT
  * versao_processamento : TEXT
  * status : TEXT (pendente | descartado | confirmado)
  revisado_em : TIMESTAMPTZ
  evento_pessoal_id : UUID <<FK, Unique>>
  criado_em : TIMESTAMPTZ
  .. Unique (plano_id, execucao, ordem) ..
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
PLANOS_ENSINO ||--o{ CANDIDATOS_AVALIACAO : "IA sugere"
PLANOS_ENSINO |o--o{ PLANOS_ENSINO : "plano_oficial_id"
CANDIDATOS_AVALIACAO |o--o| EVENTOS_PESSOAIS : "confirmado vira"
@enduml
