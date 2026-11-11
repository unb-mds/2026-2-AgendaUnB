---
title: "Verificação de segurança"
description: "Achados, correções, matriz de acesso e configuração segura do Agenda UnB (S8-D02)."
---

# Verificação de segurança

Registro da [S8-D02 (#84)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/84). Estado em **09/11/2026**, na fase de testes preventivos da Sprint 07. Este documento descreve o que foi avaliado, o que foi corrigido e o que continua pendente. Ele não é um laudo de teste de invasão.

## Escopo e método

| Camada | Como foi avaliada |
| --- | --- |
| Banco exposto (PostgREST/supabase-js) | Leitura das 23 migrações e testes em PostgreSQL 16 assumindo os papéis `anon`, `authenticated` e o back-end, com `auth.uid()` simulado. Cada teste desfaz as próprias alterações. |
| API FastAPI | Leitura de `backend/src` e testes com `TestClient` para cabeçalhos, CORS, limites e regras de abuso. |
| Front-end | Busca por pontos que interpretam conteúdo vindo do banco (links, HTML) e pelas chamadas diretas ao Supabase. |
| Dependências e segredos | `pip-audit`, `npm audit` e varredura do histórico Git por padrões de chave. |

**Limites da avaliação.** Os testes de banco rodam em PostgreSQL local com um substituto mínimo do Supabase (papéis, `auth.users`, `storage.objects`). Auth, Storage, TLS, CORS no domínio publicado e a configuração do painel do Supabase **não foram exercitados em ambiente hospedado**; ficam para a homologação da [#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76) e da [#85](https://github.com/unb-mds/2026-2-AgendaUnB/issues/85). Google Calendar, lembretes, votos e coleta ainda não existem na API e entram nesta verificação quando forem integrados.

## Achados

Severidade segundo o impacto no produto: **Alta** permite agir como outra conta ou ganhar papel indevido; **Média** amplia a superfície ou permite abuso; **Baixa** tem impacto restrito à própria conta ou depende de outra falha.

| # | Sev. | Achado | Tratamento | Estado |
| --- | --- | --- | --- | --- |
| A1 | Alta | **Script armazenado pelo link do evento.** Qualquer conta logada inseria direto em `eventos` pelo supabase-js, sem a validação de URL da API. Um `link_externo` com `javascript:` chegava ao catálogo (sugestão aprovada ou publicação de professor) e a página do evento o abria com `window.open`, executando código na sessão de quem clicasse. A tela de moderação ocultava o link inválido, o que dificultava perceber o problema ao aprovar. | INSERT direto removido; o banco só aceita `http(s)` no link, em qualquer caminho; a página do evento filtra o esquema e abre com `noopener,noreferrer`. | Corrigido (`20261111130000`, `PaginaDeEvento.jsx`) |
| A2 | Alta | **Papel de professor sem prova de posse do e-mail.** O cadastro com papel `professor` e endereço `@unb.br` criava o perfil de professor antes de qualquer confirmação. Em um projeto com confirmação de e-mail desligada, bastaria informar um `@unb.br` alheio para publicar e moderar eventos. | O papel só é concedido com `email_confirmed_at` preenchido: no cadastro quando já confirmado, ou automaticamente ao confirmar. A autopromoção pelo navegador exige o mesmo. A API recusa conta sem e-mail confirmado (403). | Corrigido. **Pendente:** conferir no painel do projeto hospedado que *Confirm email* está ligado. |
| A3 | Alta | **Bloqueio da importação de outra conta.** A unicidade global de `origem_avaliacao_id` deixava o usuário B ocupar o candidato de A com um evento na própria agenda, fazendo a confirmação de A falhar. | Unicidade por `(user_id, origem_avaliacao_id)`. | Corrigido na S7-D01 (`20261109120000`) |
| A4 | Média | Função `SECURITY DEFINER` `confirmar_candidatos_transacional` sem uso, operando sobre tabela removida. | Função removida. | Corrigido na S7-D01 |
| A5 | Média | `registrar_interesse(uuid)` chamável por visitantes, sem limite e sem deduplicação: o contador podia ser inflado à vontade. | EXECUTE revogado de `anon` e `authenticated`. O contador volta pela API com `click_id` (S8-B02). | Fechado; substituto na S8-B02 |
| A6 | Média | **Privilégios padrão amplos.** `anon` e `authenticated` tinham todos os privilégios nas tabelas (inclusive `TRUNCATE`, que ignora RLS) e toda função nova nascia executável por visitantes via `/rpc`. A proteção dependia só de cada política estar correta. | GRANT alinhado às políticas, visitante sem escrita, `TRUNCATE` revogado, EXECUTE fechado por padrão. Três testes estruturais impedem regressão. | Corrigido |
| A7 | Média | API sem cabeçalhos de proteção, documentação interativa sempre exposta, CORS com `allow_headers=*` e credenciais habilitadas. | `SecurityHeadersMiddleware`, `API_DOCS_ENABLED`, CORS com origens exatas, cabeçalhos explícitos e sem credenciais. Curinga em `CORS_ORIGINS` impede a API de iniciar. | Corrigido |
| A8 | Média | Sem limite de taxa nem de tamanho de corpo fora do upload; uma conta podia enviar sugestões sem limite, enchendo a fila de moderação. | Limite por cliente em memória, teto de 256 KiB para JSON e de 10 sugestões pendentes por conta. | Corrigido, com a limitação descrita abaixo |
| A9 | Baixa | `%` e `_` da busca eram interpretados como curingas do `LIKE`. | Termo tratado como texto literal. | Corrigido |
| A10 | Baixa | O próprio usuário alterava colunas não previstas do perfil (por exemplo `criado_em`) e gravava qualquer valor em `avatar_url`. | UPDATE restrito a `nome_completo`, `avatar_url` e `papel` (este protegido por trigger); avatar só `https`. | Corrigido |
| A11 | Baixa | O usuário pode gravar na própria agenda um evento com campos de procedência (`origem_*`) forjados. | Sem efeito sobre outras contas desde A3. A API é o único caminho que preenche procedência legítima. Avaliar fechar a escrita direta em `eventos_pessoais` quando nenhum fluxo depender dela. | Aceito e registrado |
| A12 | Média | PDFs originais continuam no Storage e `filePath` é devolvido ao dono, em desacordo com o [ADR-003](../arquitetura/adrs/adr-003-minimizar-dados-de-planos.md). | Descarte após extração local na [#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51); remoção dos originais legados na [#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83). | Envios novos já não guardam o PDF (S7-B01, na `dev`). **Pendente:** remover os PDFs antigos com o script da [#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83) e parar de devolver `filePath` |
| A13 | Média | Política de senha fraca na configuração versionada: mínimo de 6 caracteres, sem exigência de composição, `secure_password_change` desligado. | Ajustar no painel do projeto hospedado (ver checklist) e alinhar `supabase/config.toml` na [#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74). | **Pendente** |
| A14 | Baixa | `npm audit` aponta 2 vulnerabilidades altas em dependências de desenvolvimento (`vite`, `source-map-js`), com correção disponível. Não entram no bundle publicado. | `npm audit fix` no front-end, com build e testes. | **Pendente** (front-end) |
| A15 | Baixa | Dependências Python sem versão fixada: o mesmo commit pode instalar versões diferentes. `pip-audit` não encontrou vulnerabilidade conhecida em 09/11/2026. | Fixar versões ao definir o runtime do Render. | **Pendente** ([#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)) |
| A16 | Info | Não havia registro de quem mudou o papel de quem. | Tabela `auditoria_papeis`, alimentada por trigger e legível só por admins. | Corrigido |
| A17 | Média | `fila_processamento_ia` (#92, já na `dev`) dava INSERT, UPDATE e DELETE a contas logadas sem política, e a leitura usava `professor_id`, nulo em plano particular: o dono não via o próprio job. A tabela também não é usada pelo worker, que controla a fila em `planos_ensino`. | Escrita só pelo servidor, leitura pelo dono via `user_id`, `erro_tecnico` limitado a um código curto. | Corrigido. **Decisão pendente:** manter ou remover a tabela, para não haver duas filas |

A varredura de todo o histórico Git, incluindo as branches remotas, por chaves do Google, do Supabase, JWT de serviço, URLs de banco com senha e chaves privadas **não encontrou segredos versionados**. Credenciais que tenham circulado fora do repositório devem ser trocadas antes da produção.

### Limitação do limite de taxa

O `RateLimitMiddleware` conta requisições na memória do processo. Com uma instância (plano gratuito do Render) ele cumpre o papel; com várias instâncias o limite efetivo é multiplicado, e reiniciar a API zera as contagens. Ele reduz rajadas e varredura, mas não substitui a proteção da hospedagem. Login, cadastro e reenvio de e-mail são limitados pelo Supabase Auth.

## Matriz de acesso verificada

Cenários automatizados em `backend/tests/test_security_database.py`, `test_classes_database.py` e `test_moderation_database.py`. "Recusado" significa erro de permissão ou nenhuma linha afetada.

| Recurso | Visitante | Outra conta | Dono | Professor / admin |
| --- | --- | --- | --- | --- |
| `eventos_pessoais` | Recusado | Não lê, não altera, não insere em nome do dono | Lê e altera os próprios | Sem acesso por papel |
| `eventos` (catálogo) | Só aprovados; sem escrita | Só aprovados e os próprios; sem escrita direta | Lê os próprios pendentes | Leem pendentes; decidem só pelas RPCs |
| `eventos_salvos` | Recusado | Não lê nem remove | Salva só evento aprovado, para si | — |
| `notificacoes` | Recusado | Não lê nem marca | Lê e marca como lida | — |
| `profiles` | Recusado | Não lê nem altera | Altera nome e avatar; e-mail imutável; não vira admin | Admin lê todos e altera papéis pelas RPCs |
| `planos_ensino`, `versoes_plano`, `avaliacoes` | Recusado | Não lê plano privado | Lê; escrita só pela API | Sem acesso a privados por papel |
| Storage `syllabus_files` | Recusado | Não lê arquivo alheio | Lê os próprios; sem envio ou exclusão direta | Sem acesso por papel |
| `vinculos_turma` | Recusado | Não lê | Lê os próprios; escrita só pela API | — |
| `auditoria_papeis` | Recusado | Recusado | Recusado | Só admin lê |
| RPCs administrativas | Recusado | Recusado | Recusado | Só admin; moderação também para professor |

Travas estruturais, válidas para qualquer migração futura:

- toda tabela de `public` tem RLS habilitado;
- toda função `SECURITY DEFINER` e toda função chamável por conta logada fixa o `search_path`;
- nenhuma função é chamável por visitante;
- visitante não tem privilégio de escrita, e ninguém da API tem `TRUNCATE`;
- todo privilégio de escrita de conta logada corresponde a uma política.

## Regras para novas migrações

A partir de `20261111130000`, tabelas e funções novas nascem fechadas:

- tabela nova não é legível por visitante. Para leitura pública, além da política, declare `grant select on public.<tabela> to anon;`
- função nova não é executável pela API. Para expor uma RPC, declare `grant execute on function public.<f>(<tipos>) to authenticated;` e use `set search_path = ''`;
- só conceda `insert`, `update` ou `delete` a `authenticated` junto com a política correspondente. Na dúvida, a escrita passa pelo back-end.

Os testes estruturais falham se uma dessas regras for esquecida.

## Configuração por ambiente

### Projeto Supabase hospedado

- [ ] **Authentication → Sign In / Providers → Email → Confirm email: ligado.** Sem isso, A2 volta a depender só do banco.
- [ ] Senha mínima de 8 caracteres ou mais, com letras e dígitos; *Secure password change* ligado.
- [ ] *Site URL* e *Redirect URLs* apenas com as URLs da SPA daquele ambiente.
- [ ] SMTP próprio configurado ([#68](https://github.com/unb-mds/2026-2-AgendaUnB/issues/68)); limites de envio revisados.
- [ ] **Database → Settings → Enforce SSL on incoming connections: ligado** (RNF03).
- [ ] Chave `service_role`/secreta e senha do banco apenas nas variáveis do servidor. Nunca em variável `VITE_*`, no repositório ou em conversa de grupo.
- [ ] *Security Advisor* do painel sem alerta de RLS após cada `db push`.
- [ ] Projetos, bancos e chaves distintos para homologação e produção.

### API (Render)

| Variável | Valor em homologação/produção |
| --- | --- |
| `CORS_ORIGINS` | Somente a URL HTTPS da SPA do ambiente. Curinga impede a API de iniciar. |
| `API_DOCS_ENABLED` | `false` |
| `TRUSTED_PROXY_HOPS` | Número de proxies da hospedagem à frente da API. Começar com `1` e conferir nos logs que o endereço registrado é o do cliente, não o do proxy. |
| `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_WRITE_PER_MINUTE` | Padrões `240` e `60`; ajustar após medir o uso real. |
| `DATABASE_URL` | Com TLS (`sslmode=require` quando o provedor não o impuser). |

Iniciar com `uvicorn src.main:app --host 0.0.0.0 --port $PORT --no-server-header`, sem `--reload`.

### SPA (Vercel)

- [ ] Apenas `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` e `VITE_API_URL` no build.
- [ ] Cabeçalhos de segurança e fallback de SPA no `vercel.json` ([#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76)).
- [ ] Previews sem credenciais de produção.

## Como repetir a verificação

```bash
# banco: Supabase local em execução e TEST_SUPABASE_DB_URL apontando para ele
cd backend
python -m pytest tests/test_security_database.py tests/test_security_api.py -q

# dependências
pip install pip-audit && pip-audit -r requirements.txt
cd ../frontend && npm audit
```

## Pendências para o aceite

| Pendência | Responsável | Issue |
| --- | --- | --- |
| Repetir a matriz no ambiente publicado (JWT real, Storage real, TLS, CORS) | Luis, com Felipe | [#84](https://github.com/unb-mds/2026-2-AgendaUnB/issues/84), [#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76) |
| Conferir o checklist do painel Supabase no projeto de homologação | Felipe | [#84](https://github.com/unb-mds/2026-2-AgendaUnB/issues/84) |
| Remover os PDFs antigos (`scripts/descartar_pdfs.py`) e parar de devolver `filePath` (A12) | Felipe, com Heitor | [#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83), [#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51) |
| Política de senha e fluxo de confirmação (A13) | Thomas, com Thomaz | [#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74) |
| `npm audit fix` e versões Python fixadas (A14, A15) | Front-end e Luis | [#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76) |
| Isolamento de tokens e mapeamentos do Google Calendar | Luis, com Thomaz | [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82) |
| Matriz de votos, lembretes, coleta e importação: testes de isolamento nos PRs de cada issue; repetir no ambiente publicado quando integrados | Felipe | [#75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75), [#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72), [#77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77), [#81](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81) |

Consulte também [ADR-006](../arquitetura/adrs/adr-006-autorizacao-em-camadas.md), [Banco de dados](../arquitetura/banco-de-dados.md) e [Implantação](../implantacao.md).
