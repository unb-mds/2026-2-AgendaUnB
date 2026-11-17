---
title: "ADR-006 · Aplicar autorização na API, nas RPCs e nas políticas RLS"
description: "Decisão, consequências e critérios de verificação: aplicar autorização na api, nas rpcs e nas políticas rls."
---

# ADR-006 · Aplicar autorização na API, nas RPCs e nas políticas RLS

| Campo | Valor |
| --- | --- |
| Estado | Implementada |
| Data do registro | 2026-11-08 |
| Rastreabilidade | DA-04; RF04, RF09, RF11; RNF02, RNF04 |
| Substitui | Nenhuma ADR |

Registro retrospectivo; a motivação histórica e as alternativas avaliadas na época não estão documentadas.

## Contexto

O frontend acessa tanto a API quanto o Supabase. Conexões administrativas da API podem ignorar as políticas de segurança por linha (RLS).

## Decisão

Verificar papel, propriedade e visibilidade no ponto que executa cada operação:

- **API FastAPI:** filtra os recursos privados pela conta autenticada, valida e-mail confirmado (`src/middlewares/auth.py`) e aceita sugestões de estudantes apenas via `POST /api/v1/suggestions` (com autoria extraída da sessão e status forçado como `pendente` no banco).
- **RPCs administrativas (`supabase/migrations/20261018000000_moderacao_e_notificacoes.sql` e `20261018000100_admin_professor_email_livre.sql`):**
  - `listar_sugestoes` e `moderar_sugestao` verificam o papel (`professor` ou `admin`) no banco, decidem apenas itens `pendente`, exigem justificativa de até 2.000 caracteres na recusa e detectam alterações concorrentes sem sobrescrever decisões anteriores.
  - `admin_buscar_usuarios` e `admin_definir_papel` restringem-se a `admin`, detectam concorrência e impedem que o administrador remova o próprio acesso.
  - Cadastro e autopromoção para `professor` exigem e-mail `@unb.br`, mas um administrador pode atribuir o papel `professor` a qualquer endereço via `admin_definir_papel`.
- **RLS e Triggers:** limitam leituras via SDK (incluindo `notificacoes`, visíveis e atualizáveis apenas pelo destinatário) e protegem autoria e metadados gerenciados pelo servidor. Guards de páginas no frontend são apenas controle de navegação.

## Alternativas para comparação

As opções abaixo explicitam os trade-offs; não afirmam uma avaliação histórica da equipe.

Centralizar tudo na API exigiria migrar os fluxos da ADR-001. Confiar apenas no frontend ou apenas em RLS deixaria caminhos sem proteção.

## Consequências

A equipe mantém regras coerentes em mais de uma camada. Professor/admin moderam eventos; apenas admin gerencia papéis e categorias. Na R2, o papel administrativo não dá acesso ao conteúdo acadêmico privado de outras contas.

## Orientações para contribuição e verificação

Verificar acessos cruzados entre contas e papéis, incluindo chamadas diretas. A suíte SQLite da API não comprova RLS, triggers ou RPCs; esses cenários exigem PostgreSQL/Supabase local com `TEST_SUPABASE_DB_URL` apontando exclusivamente para `localhost`/`127.0.0.1` (`tests/test_*database.py`).

## Fontes e relações

[ADR-001](/arquitetura/adrs/adr-001-integracao-fastapi-supabase) · [Matriz de regras](/arquitetura/visao-geral#11-matriz-de-regras-e-evidencias) · [Permissões da R2](/atualizacoes#permissoes-e-erros) · [Requisitos](/produto/requisitos) · [Índice de ADRs](/arquitetura/adrs/index)
