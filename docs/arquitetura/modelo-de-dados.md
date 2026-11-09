---
title: "Modelo de dados"
description: "Diagrama Entidade-Relacionamento e estrutura visual das tabelas do banco de dados Supabase da Agenda UnB."
---

Este documento apresenta a estrutura visual de dados adotada no banco de dados Supabase do MVP da Agenda UnB. Ele inclui o Diagrama Entidade-Relacionamento (DER) para visualização da arquitetura, descrevendo como as tabelas interagem. O Dicionário de Dados detalhado (DDL) encontra-se no documento `/docs/arquitetura/banco-de-dados`.

---

## Diagrama Entidade-Relacionamento (DER)

O diagrama abaixo ilustra as relações entre as 7 tabelas que compõem o banco de dados.

---

```mermaid
erDiagram
    PROFILES {
        UUID id PK "auth.users.id"
        TEXT nome_completo "obrigatório"
        TEXT email UK "obrigatório, imutável"
        TEXT papel
    }

    CAMPUS {
        UUID id PK
        TEXT nome UK "obrigatório"
        TIMESTAMPTZ created_at
    }

    CATEGORIES {
        UUID id PK
        TEXT nome UK "obrigatório"
        TEXT cor
        TIMESTAMPTZ created_at
    }

    EVENTOS {
        UUID id PK
        UUID autor_id FK "obrigatório"
        TEXT titulo "obrigatório"
        TEXT descricao "obrigatório"
        TIMESTAMPTZ data_evento "obrigatório"
        TEXT localizacao
        TEXT link_externo
        UUID campus_id FK
        UUID category_id FK
        TEXT status "obrigatório"
        TIMESTAMPTZ created_at
    }

    EVENTOS_PESSOAIS {
        UUID id PK
        UUID user_id FK "obrigatório"
        TEXT titulo "obrigatório"
        TEXT descricao
        TIMESTAMPTZ data_hora "obrigatório"
        UUID campus_id FK
        UUID category_id FK
        TIMESTAMPTZ created_at
    }

    PLANOS_ENSINO {
        UUID id PK
        UUID professor_id FK "obrigatório"
        TEXT disciplina "obrigatório"
        TEXT turma "obrigatório"
        TEXT arquivo_url
        TIMESTAMPTZ created_at
    }

    AVALIACOES {
        UUID id PK
        UUID plano_id FK "obrigatório"
        TEXT titulo "obrigatório"
        TIMESTAMPTZ data_avaliacao "obrigatório"
        TIMESTAMPTZ created_at
    }

    PROFILES ||--o{ EVENTOS : "cria"
    PROFILES ||--o{ EVENTOS_PESSOAIS : "possui"
    PROFILES ||--o{ PLANOS_ENSINO : "envia"

    CAMPUS ||--o{ EVENTOS : "localiza"
    CAMPUS ||--o{ EVENTOS_PESSOAIS : "localiza"

    CATEGORIES ||--o{ EVENTOS : "classifica"
    CATEGORIES ||--o{ EVENTOS_PESSOAIS : "classifica"

    PLANOS_ENSINO ||--o{ AVALIACOES : "gera"
```
