---
title: "Modelo de dados"
description: "Diagrama das entidades e dos relacionamentos do banco de dados da Agenda UnB."
---

O diagrama mostra as entidades do catálogo, da agenda, da moderação e dos planos de ensino. Consulte colunas, restrições e políticas de acesso na [especificação física](banco-de-dados.md). As tabelas e políticas vigentes são definidas pelas migrações em `supabase/migrations/`. Turmas, vínculos e versões foram modelados na S7-D01 (`20261109120000`), conforme as ADR-009 e ADR-010 e os [contratos da Release 2](../atualizacoes.md#contratos-da-release-2).

## Diagrama Entidade-Relacionamento (DER)

```mermaid
erDiagram
    PROFILES {
        UUID id PK "auth.users.id"
        TEXT nome_completo
        TEXT email UK
        TEXT papel
    }

    CAMPUS {
        UUID id PK
        TEXT nome UK
    }

    CATEGORIES {
        UUID id PK
        TEXT nome UK
        TEXT cor
    }

    EVENTOS {
        UUID id PK
        UUID autor_id FK
        UUID campus_id FK
        UUID category_id FK
        TIMESTAMPTZ data_evento
        TIMESTAMPTZ data_fim "fim exclusivo"
        BOOLEAN dia_inteiro
        TEXT status
        TEXT fonte "nulo se criado na plataforma"
        TEXT fonte_id "UK com fonte"
    }

    COLETAS_EVENTOS {
        UUID id PK
        TEXT fonte
        TEXT status
        TIMESTAMPTZ iniciada_em
    }

    CLIQUES_EVENTO {
        UUID evento_id PK,FK
        UUID click_id PK
        TIMESTAMPTZ criado_em
    }

    LEMBRETES {
        UUID id PK
        UUID user_id FK
        UUID evento_pessoal_id FK
        UUID evento_id FK
        TIMESTAMPTZ agendado_para
        TEXT status
        TIMESTAMPTZ lido_em
    }

    EVENTOS_PESSOAIS {
        UUID id PK
        UUID user_id FK "auth.users.id"
        UUID campus_id FK
        UUID category_id FK
        TIMESTAMPTZ data_hora
        UUID origem_avaliacao_id UK "procedencia sem FK"
    }

    EVENTOS_SALVOS {
        UUID user_id PK,FK
        UUID event_id PK,FK
        TIMESTAMPTZ criado_em
    }

    NOTIFICACOES {
        UUID id PK
        UUID usuario_id FK
        UUID evento_id FK
        TEXT tipo
        TIMESTAMPTZ lida_em
    }

    PLANOS_ENSINO {
        UUID id PK
        UUID user_id FK
        UUID professor_id FK
        UUID plano_oficial_id FK
        TEXT tipo
        TEXT status
        SMALLINT ano
        SMALLINT semestre
    }

    AVALIACOES {
        UUID id PK
        UUID plano_id FK
        UUID versao_id FK
        SMALLINT ordem
        TIMESTAMPTZ data_avaliacao
        TEXT status
    }

    VERSOES_PLANO {
        UUID id PK
        UUID plano_id FK
        SMALLINT numero
        UUID autor_id FK
        TEXT autor_papel
        UUID versao_origem_id FK
        BOOLEAN procedencia_institucional
        TEXT visibilidade
    }

    DISCIPLINAS {
        UUID id PK
        TEXT origem_id
        TEXT codigo
        TEXT nome
    }

    OFERTAS_TURMA {
        UUID id PK
        UUID disciplina_id FK
        TEXT turma
        SMALLINT ano
        SMALLINT semestre
        TEXT professor
        TEXT horarios
    }

    VINCULOS_TURMA {
        UUID user_id PK,FK
        UUID oferta_id PK,FK
    }

    PROFILES ||--o{ EVENTOS : "cria"
    PROFILES ||--o{ EVENTOS_SALVOS : "salva"
    PROFILES ||--o{ NOTIFICACOES : "recebe"
    PROFILES ||--o{ PLANOS_ENSINO : "envia"
    PROFILES o|--o{ PLANOS_ENSINO : "responde pela turma"
    CAMPUS o|--o{ EVENTOS : "localiza"
    CAMPUS o|--o{ EVENTOS_PESSOAIS : "localiza"
    CATEGORIES o|--o{ EVENTOS : "classifica"
    CATEGORIES o|--o{ EVENTOS_PESSOAIS : "classifica"
    EVENTOS ||--o{ EVENTOS_SALVOS : "tem vinculos"
    EVENTOS ||--o{ CLIQUES_EVENTO : "conta redirecionamentos"
    EVENTOS o|--o{ LEMBRETES : "avisa quem salvou"
    EVENTOS_PESSOAIS o|--o{ LEMBRETES : "avisa o dono"
    PROFILES ||--o{ LEMBRETES : "recebe"
    EVENTOS o|--o{ NOTIFICACOES : "origina"
    PLANOS_ENSINO ||--o{ AVALIACOES : "tem"
    PLANOS_ENSINO ||--|{ VERSOES_PLANO : "versiona"
    VERSOES_PLANO ||--o{ AVALIACOES : "contem"
    VERSOES_PLANO o|--o{ VERSOES_PLANO : "revisa"
    PROFILES ||--o{ VERSOES_PLANO : "autor"
    DISCIPLINAS ||--o{ OFERTAS_TURMA : "ofertada em"
    OFERTAS_TURMA o|--o{ PLANOS_ENSINO : "turma do plano"
    PROFILES ||--o{ VINCULOS_TURMA : "segue"
    OFERTAS_TURMA ||--o{ VINCULOS_TURMA : "seguida por"
    PLANOS_ENSINO o|--o{ PLANOS_ENSINO : "referencia plano oficial"
    VERSOES_PLANO o|--o{ EVENTOS_PESSOAIS : "origem da importacao"
```

O dono de `eventos_pessoais` referencia `auth.users.id`. O fluxo de confirmação da API registra a procedência em `eventos_pessoais.origem_avaliacao_id` (sem FK) e `origem_versao_id` (FK para `versoes_plano`). A unicidade é por usuário, `(user_id, origem_avaliacao_id)`. `avaliacoes` é a tabela única de candidatos desde a S7-D01; detalhes na [especificação física](banco-de-dados.md).
