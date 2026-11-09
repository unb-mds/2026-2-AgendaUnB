---
title: "Arquitetura"
description: "Documento que registra a arquitetura de software do Agenda UnB, detalhando stack, componentes, fluxos e decisões de design."
---

## 1. Objetivo e escopo

O Agenda UnB reúne eventos públicos dos campi e compromissos privados em uma aplicação web responsiva. A Release 2 prevê seleção manual de ofertas no catálogo público do Followw e vínculo autodeclarado. A plataforma organiza compromissos e eventos da comunidade. Matrícula oficial, notas e frequência seguem no sistema acadêmico.

Referência da consolidação: **24/10/2026**, commit `e0ecf46`; histórico de operações comparado à tag `R1` (`4a3a07d`). Implementação observada e testes existentes não equivalem a aprovação formal do time. Propostas futuras são identificadas separadamente.

## 2. Visão geral

```mermaid
flowchart LR
    U[Visitante, estudante, professor ou administrador] --> WEB[SPA React + Vite]
    WEB -->|Eventos, sugestões e vínculos salvos| API[FastAPI /api/v1]
    WEB -->|Sessão| AUTH[Supabase Auth]
    WEB -->|RPCs e notificações| DATA[Supabase Data API]
    API -->|Validação da sessão| AUTH
    API -->|SQLAlchemy| DB[(PostgreSQL)]
    DATA -->|RPCs, RLS e triggers| DB
    API -->|Upload de planos| STORAGE[Supabase Storage privado]
```

A comunicação tem dois caminhos: eventos, sugestões e agenda usam a API FastAPI; autenticação, RPCs de moderação/administração e notificações usam o SDK Supabase no navegador. As RPCs conferem o papel real no banco. A proteção das páginas React não substitui essa autorização.

## 3. Stack e organização

| Camada | Tecnologia e localização |
| --- | --- |
| Frontend | React 19, Vite 6, React Router 7; `frontend/src/` |
| API | Python, FastAPI, SQLAlchemy 2, Pydantic 2 e httpx; `backend/src/` |
| Dados e sessão | PostgreSQL via Supabase, Supabase Auth e SDK JavaScript |
| Migrações | SQL versionado em `supabase/migrations/` e aplicado em ordem de timestamp |
| Ambiente local | Supabase CLI e Docker; serviços coordenados pelo Makefile |
| Documentação | Markdown compartilhado entre o MkDocs, publicado no GitHub Pages, e o Mintlify |
| Testes | pytest em `backend/tests/`; testes de calendário via `node --test` |

A API é uma aplicação única, sem microsserviços. O módulo de eventos concentra rotas, schemas e regras dos eventos públicos, privados, salvos e sugestões. `database/models.py` mapeia as tabelas usadas pela API; as migrações SQL são a referência para o esquema completo, triggers, funções e políticas.

## 4. Frontend e navegação

| Rota | Comportamento |
| --- | --- |
| `/` | Apresentação, cadastro e login |
| `/eventos` | Catálogo público e Meus Eventos; lista de cards ou calendário mensal/semanal |
| `/evento/:id` | Detalhes de evento público aprovado ou compromisso privado do proprietário |
| `/plano-de-ensino` | Envio e histórico de planos. A jornada integrada de extração e revisão está planejada para a Release 2 |
| `/sugestoes` | Fila e histórico de sugestões; professores e administradores |
| `/admin` | Busca e filtros de usuários, confirmação de e-mail, último acesso e cargos; somente admins |
| `/segunda-pagina` | Redirecionamento legado para `/eventos`, preservando query e fragmento; `#plano-de-ensino` leva à página de planos |

O calendário usa os mesmos eventos filtrados da lista, com navegação por mês/semana, botão Hoje e horários ordenados por dia. As datas civis seguem o fuso local do navegador. Em telas pequenas, a grade permite rolagem horizontal.

Meus Eventos combina compromissos privados com vínculos a eventos públicos salvos. Os dados do público são lidos do original; remover o vínculo não altera o evento. Somente os compromissos privados podem ser editados nessa agenda.

## 5. API REST implementada

As rotas de negócio usam `/api/v1`; a sessão é enviada em `Authorization: Bearer <token>`. O backend valida o token com Supabase Auth e consulta o perfil no banco.

O [inventário da API](../api-specs.md) detalha as rotas disponíveis de catálogo público, compromissos privados, sugestões, vínculos salvos, planos de ensino e saúde. As ações administrativas usam RPCs do Supabase.

PUT e DELETE dos vínculos salvos são idempotentes. O frontend percorre as páginas do catálogo em lotes de 100. Filtros de turno são aplicados na interface.

### Fluxo interno do backend

```mermaid
flowchart TB
    HTTP[Requisição HTTP] --> APP[FastAPI: CORS e roteamento]
    APP --> VALID[Validação Pydantic de entrada]
    APP --> DEP[Dependências de sessão nas rotas protegidas]
    DEP --> AUTH[Supabase Auth: validação do Bearer]
    DEP --> PROFILE[Consulta do papel em profiles]
    VALID --> ROUTE[Rotas do módulo events]
    DEP --> ROUTE
    ROUTE --> RULE[Regras de papel, propriedade e visibilidade]
    RULE --> ORM[SQLAlchemy e sessão por requisição]
    PROFILE --> ORM
    ORM --> DB[(PostgreSQL)]
    DB --> OUT[Schemas de resposta]
    OUT --> JSON[Resposta JSON ou 204 sem corpo]
    APP -. exceções .-> ERR[Handlers: validação, conflito e indisponibilidade]
```

O diagrama representa responsabilidades, não uma ordem estrita de execução das dependências FastAPI. Rotas públicas dispensam a validação de sessão. `get_db` abre e fecha a sessão; as rotas controlam commits. Não existe camada separada de serviços/repositórios: regras e consultas estão concentradas no router. A consulta de papel e as regras de propriedade continuam necessárias mesmo quando a conexão PostgreSQL ignora RLS.

## 6. Sugestões, moderação e administração

O estudante escolhe **Sugerir evento** no formulário Criar Evento. `POST /api/v1/suggestions` persiste a proposta pendente. O banco força o status para autoria estudantil e registra `sugestao_estudante`, preservando essa origem mesmo após mudança de cargo.

O frontend chama as seguintes RPCs pelo SDK Supabase, sem endpoints FastAPI `/admin`:

| RPC | Responsabilidade e acesso |
| --- | --- |
| `listar_sugestoes` | Pendentes e histórico aprovado/rejeitado, busca e paginação de 20; professor/admin |
| `moderar_sugestao` | Decide somente sugestões pendentes; professor/admin; recusa exige justificativa de até 2.000 caracteres |
| `admin_buscar_usuarios` | Busca por nome/e-mail, filtros de papel e confirmação, último acesso e paginação de 20; admin |
| `admin_definir_papel` | Verifica cargo anterior e chama `admin_alterar_papel`; somente admin |

Decisões concorrentes de moderação não sobrescrevem uma decisão anterior. Mudanças de cargo detectam divergência do papel esperado, e um administrador não pode remover o próprio cargo de admin.

Triggers registram notificações de submissão, aprovação e recusa na mesma transação do evento. A tabela `notificacoes` guarda título e justificativa; o sino dos estudantes consulta ao enviar sugestão, ao voltar à janela e a cada 30 segundos. A leitura e a marcação como lida são limitadas ao destinatário por RLS e permissões de coluna. Esses avisos não são lembretes de proximidade.

## 7. Persistência, privacidade e migrações

As tabelas da base R1 são `profiles`, `campus`, `categories`, `eventos`, `eventos_pessoais`, `planos_ensino` e `avaliacoes`. As novas migrações adicionam `eventos_salvos`, `notificacoes`, campos de sugestões/recusa e contador de interessados, funções administrativas e políticas de Storage. A migração `20261029160000` acrescenta procedência aos candidatos e eventos pessoais, restringe a leitura de avaliações e impede confirmar o mesmo candidato mais de uma vez. A criação das estruturas não comprova a existência do parser.

- Eventos privados e vínculos salvos são limitados ao dono. A API também verifica propriedade, pois conexões administrativas podem ignorar RLS.
- Apenas eventos aprovados aparecem no catálogo e nas consultas de públicos salvos. A exclusão de um público remove seus vínculos em cascata.
- Cadastro e autopromoção para professor exigem `@unb.br`. A migração `20261018000100` removeu a constraint global de domínio: administradores podem atribuir professor a outro endereço pela RPC protegida. E-mail do perfil continua imutável.
- A alteração de papéis pelo navegador é protegida por trigger; não há cadastro livre como admin.
- O bucket privado `syllabus_files` aceita PDF até 10 MB. A migração `20261107000000` remove permissões de escrita direta que contornavam a API. O navegador lê apenas os próprios arquivos e planos. O backend valida o PDF, aplica a cota de 10 uploads por usuário em 5 dias e grava o arquivo com `SUPABASE_SERVICE_ROLE_KEY`, exclusiva do servidor.
- HTTPS é requisito de produção; `.env` guarda configurações locais fora do versionamento.

As migrações devem ser aplicadas antes de disponibilizar API/frontend dependentes delas. No Supabase local iniciado, use `npx supabase migration up`. Se a migração `20261029160000` entrou no repositório após o banco já ter versões posteriores, use `npx supabase migration up --include-all` para incluir a versão pendente. `make db-reset` recria o banco com migrações e seed. Veja o [diagrama de dados](modelo-de-dados.md), a [especificação física](banco-de-dados.md) e os guias de [eventos salvos](../eventos-salvos.md) e [painel](../painel-administrativo.md).

## 8. Funcionalidades futuras e implantação

O backend atual recebe uploads de planos, oferece histórico paginado, detalhe com candidatos e confirmação de avaliações na agenda privada. A seleção de ofertas, o worker de extração e o compartilhamento de versões fazem parte do fluxo planejado para a Release 2.

O fluxo previsto descarta o PDF após a extração local. O usuário revisa o texto minimizado e autoriza o processamento externo. Os candidatos só viram eventos após confirmação. O autor pode compartilhar uma versão revisada para que seguidores da oferta votem e importem avaliações para a própria agenda.

A entrega também prevê coleta da Agenda UnB Notícias, métricas de redirecionamento independentes da agenda, lembretes e exportação Google/ICS. A coleta deve operar separadamente das consultas à agenda para que falhas da fonte preservem os dados já armazenados. [Contratos da Release 2](../atualizacoes.md#contratos-da-release-2) · [Matriz de aceite](../matriz-release-2.md)

O GitHub Pages hospeda a documentação. Isso não define hospedagem da SPA ou da API. O arquivo `backend/Dockerfile` está vazio; não constitui uma imagem executável. O desenvolvimento usa Supabase CLI/Docker, FastAPI e Vite. O [plano de implantação](../implantacao.md) propõe Vercel, Render com runtime Python e Supabase separado por ambiente; não há pipeline da aplicação implementado.

## 9. Verificação

Execute pytest no backend, `npm run build` no frontend e `node --test src/lib/calendar.test.js` na pasta frontend. Os testes de API de eventos salvos usam SQLite e não validam políticas RLS reais. Os testes de moderação no PostgreSQL exigem `TEST_SUPABASE_DB_URL` apontando ao Supabase local; sem essa variável são ignorados. Consulte [Contribuição](../processo/contribuindo.md) para os comandos.

### Registro de validação — 24/10/2026

| Verificação executada | Resultado e limite |
| --- | --- |
| `python -m pytest tests -q` no backend | 15 passaram, 7 ignorados por ausência de Supabase local configurado; aviso de depreciação Starlette/httpx |
| `node --test src/lib/calendar.test.js` no frontend | 3 passaram |
| `npm run build` no frontend | Passou; aviso de chunk acima de 500 kB |
| OpenAPI × inventário documental | 15 operações encontradas; nenhuma ausente na especificação |
| Requisição pessoal com `starts_at` sem fuso, via TestClient | Reproduzido 500 no handler de validação; dívida registrada, código não alterado |
| `python -m mkdocs build --strict` | Passou; saída temporária fora do repositório |
| Inspeção visual do site local | Diagramas geral e interno renderizados; páginas de contratos e implantação revisadas |

Não foram executados testes RLS/RPCs em banco remoto, deploy nem homologação hospedada. Os sete testes ignorados permanecem pendentes de Supabase local descartável. O teste isolado do erro de validação usa entrada fictícia e não grava dados.

## 10. Registro de decisões arquiteturais

O [índice de ADRs](adrs/index.md) reúne as decisões implementadas, as aceitas para a Release 2 e as propostas, com fontes, consequências e orientações de verificação. Consulte-o antes de alterar a arquitetura. Os IDs DA preservam o histórico da consolidação anterior.

| Registro anterior | ADR correspondente |
| --- | --- |
| DA-01 — aplicação única | [ADR-004](adrs/adr-004-api-monolitica.md) |
| DA-02 — integração FastAPI/Supabase | [ADR-001](adrs/adr-001-integracao-fastapi-supabase.md) |
| DA-03 — sessão e papel | [ADR-005](adrs/adr-005-validacao-de-sessao.md) |
| DA-04 — autorização | [ADR-006](adrs/adr-006-autorizacao-em-camadas.md) |
| DA-05 — migrações | [ADR-007](adrs/adr-007-migracoes-sql.md) |
| DA-06 — eventos salvos | [ADR-008](adrs/adr-008-vinculos-de-eventos-publicos.md) |
| DA-07 — hospedagem proposta | [ADR-002](adrs/adr-002-separar-hospedagem-e-ambientes.md) |

As decisões da R2 estão nas ADRs 003 e 009–013. Seu estado não comprova implementação nem homologação.

## 11. Matriz de regras e evidências

“Cobertura existente” significa cenário presente na suíte, não certificação de execução, homologação hospedada ou aprovação de negócio. A execução desta consolidação é registrada na seção 9. Arquivos de testes abaixo são relativos a `backend/tests/`.

| Regra implementada | Onde é aplicada | Cobertura existente / limite |
| --- | --- | --- |
| Catálogo e salvos exibem somente aprovados | Consultas do router | `test_events_api.py::test_list_public_events_filters_and_hides_pending`; `test_saved_events_api.py::test_unapproved_missing_and_deleted_events` |
| Privados são acessíveis somente pelo dono | Filtro `user_id` na API e RLS SQL | `test_events_api.py::test_personal_event_crud_is_limited_to_its_owner`; SQLite não comprova RLS |
| Só professor/admin publicam e excluem públicos | `require_event_manager` | `test_events_api.py::test_public_create_and_delete_require_event_manager`; sessão substituída no teste |
| Sugestão estudantil nasce pendente sem autoria/status forjados | Router e triggers SQL | `test_suggestions_api.py`; `test_moderation_database.py::test_student_rls_submission_and_notifications` |
| Moderação somente pendente; recusa justificada; avisos atômicos | `moderar_sugestao` e triggers | `test_moderation_database.py::test_moderation_and_atomic_notification`; execução PostgreSQL necessária |
| Notificações limitadas ao destinatário, atualização só de leitura | RLS e permissões de coluna | `test_moderation_database.py::test_student_rls_submission_and_notifications` |
| Admin altera terceiros, sem autorrebaixamento; detecta cargo divergente | `admin_definir_papel`, `admin_alterar_papel` | `test_moderation_database.py::test_admin_role_guards_and_professor_isolation`; concorrência simultânea não inferida desse teste |
| Cadastro/autopromoção professor exige domínio institucional; admin pode atribuir fora dele | Triggers e migração `20261018000100` | `test_moderation_database.py::test_admin_can_promote_personal_email_but_user_cannot` cobre promoção por admin; apesar do nome, não testa explicitamente todas as negativas de cadastro/autopromoção |
| Salvar/remover vínculo é idempotente e isolado por usuário | Router, chave composta e cascata | `test_saved_events_api.py`, incluindo duplicata e remoção própria; SQLite não comprova RLS |

Limites conhecidos: `location` pessoal não é persistido; o handler de validação pode falhar ao serializar certos contextos Pydantic; `/health` não verifica dependências. Os detalhes estão nos [contratos](../api-specs.md). Corrigir essas limitações requer tarefas de código separadas desta consolidação.

## 12. Manutenção documental

Atualize no mesmo PR os documentos afetados por mudanças em rotas, schemas, autorização, regras de negócio, migrações ou implantação. Consulte a [referência da API](../api-specs.md), o [índice de decisões](#10-registro-de-decisoes-arquiteturais), os [padrões](../produto/padroes.md) e o [plano de implantação](../implantacao.md). Registre evidências de testes e identifique o que ainda está planejado.
