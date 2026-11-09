---
title: "Modelo de dados"
description: "Diagrama das entidades e dos relacionamentos do banco de dados da Agenda UnB."
---

O diagrama mostra as entidades do catálogo, da agenda, da moderação e dos planos de ensino. Consulte colunas, restrições e políticas de acesso na [especificação física](banco-de-dados.md). As tabelas e políticas vigentes são definidas pelas migrações em `supabase/migrations/`. As mudanças planejadas de turmas e versões estão nos [contratos da Release 2](../atualizacoes.md#contratos-da-release-2).

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
        TEXT status
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
        TIMESTAMPTZ data_avaliacao
        TEXT status
    }

    CANDIDATOS_AVALIACAO {
        UUID id PK
        UUID plano_id FK
        UUID evento_pessoal_id FK,UK
        SMALLINT execucao
        SMALLINT ordem
        DATE data_sugerida
        TIME hora_sugerida
        TEXT status
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
    EVENTOS o|--o{ NOTIFICACOES : "origina"
    PLANOS_ENSINO ||--o{ AVALIACOES : "tem"
    PLANOS_ENSINO ||--o{ CANDIDATOS_AVALIACAO : "tem"
    PLANOS_ENSINO o|--o{ PLANOS_ENSINO : "referencia plano oficial"
    CANDIDATOS_AVALIACAO o|--o| EVENTOS_PESSOAIS : "gera quando confirmado"
```

O dono de `eventos_pessoais` referencia `auth.users.id`. O fluxo de confirmação da API registra a procedência de `avaliacoes` em `eventos_pessoais.origem_avaliacao_id`. Esse campo tem índice único parcial e não é uma chave estrangeira. As tabelas `avaliacoes` e `candidatos_avaliacao` têm contratos diferentes, descritos na [especificação física](banco-de-dados.md).
