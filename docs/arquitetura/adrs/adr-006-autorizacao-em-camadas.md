---
title: "ADR-006 · Aplicar autorização na API, nas RPCs e nas políticas RLS"
description: "Decisão de aplicar controle de acesso em camadas na API, funções SQL e RLS."
---

# ADR-006 · Aplicar autorização na API, nas RPCs e nas políticas RLS

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-04; RF04, RF09, RF11; RNF02, RNF04 |
| Substitui | Nenhuma ADR |

## Contexto

O frontend acessa tanto a API FastAPI quanto o Supabase diretamente pelo SDK JavaScript. Conexões administrativas da API ao PostgreSQL podem ignorar políticas de segurança por linha (RLS), exigindo verificação explícita em cada camada de execução.

## Decisão

Verificar papel, propriedade, confirmação de e-mail e visibilidade no ponto que executa cada operação:

- **API FastAPI:** filtra recursos privados pela conta autenticada, exige e-mail confirmado (`src/middlewares/auth.py`), valida acesso a versões de planos por `ator_pode_ler_versao` e aceita sugestões de estudantes apenas via `POST /api/v1/suggestions` (com autoria extraída da sessão e status forçado como `pendente` no banco).
- **RPCs administrativas e de moderação:**
  - `listar_sugestoes`, `listar_revisoes_coleta` e `moderar_sugestao` verificam papel (`professor` ou `admin`) e confirmação de e-mail no banco, decidem apenas itens `pendente`, exigem justificativa de até 2.000 caracteres na recusa e detectam alterações concorrentes sem sobrescrever decisões anteriores.
  - `admin_buscar_usuarios`, `admin_definir_papel`, `admin_listar_categorias`, `admin_criar_categoria` e `admin_excluir_categoria` restringem-se a `admin`, detectam concorrência e impedem que o administrador remova o próprio acesso.
  - Cadastro e autopromoção para `professor` exigem e-mail `@unb.br` confirmado, mas um administrador pode atribuir o papel `professor` a outra conta confirmada via `admin_definir_papel`. Toda alteração de papel é registrada em `auditoria_papeis`.
- **RLS e Triggers:** limitam leituras e escritas via SDK (incluindo `notificacoes`, visíveis e atualizáveis em `lida_em` apenas pelo destinatário) e protegem autoria e metadados gerenciados pelo servidor. Guards de rotas no frontend atuam apenas como controle de navegação.

## Alternativas para comparação

Centralizar todas as operações na API exigiria migrar os fluxos da [ADR-001](/arquitetura/adrs/adr-001-integracao-fastapi-supabase). Confiar apenas no frontend ou apenas em RLS deixaria caminhos sem proteção quando acessados por conexões privilegiadas.

## Consequências

As regras de acesso permanecem coerentes entre API, RPCs e RLS. Professores e administradores moderam eventos e sugestões; apenas administradores gerenciam papéis, categorias e procedência institucional. O papel administrativo não concede acesso a dados privados da agenda nem a planos privados de outras contas.

## Orientações para contribuição e verificação

Verificar acessos cruzados entre contas, papéis e usuários sem confirmação de e-mail, incluindo chamadas diretas ao banco. A suíte SQLite da API não comprova RLS, triggers ou RPCs; esses cenários exigem PostgreSQL/Supabase local com `TEST_SUPABASE_DB_URL` apontando exclusivamente para `localhost`/`127.0.0.1` (`tests/test_*database.py`).

## Fontes e relações

[ADR-001](/arquitetura/adrs/adr-001-integracao-fastapi-supabase) · [Matriz de regras](/arquitetura/visao-geral#10-matriz-de-regras-e-evidencias) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
