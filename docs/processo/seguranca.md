---
title: "Verificação de segurança"
description: "Achados, correções, matriz de acesso e configuração segura do Agenda UnB (S8-D02)."
---

Registro da [S8-D02 (#84)](https://github.com/unb-mds/2026-2-AgendaUnB/issues/84). Estado em **20/11/2026** na branch `fix/s8-d02-endurecimento`, após a integração da Release 2 e a auditoria de QA.

## Escopo e método

| Camada | Como foi avaliada |
| --- | --- |
| Banco exposto (PostgREST/supabase-js) | Revisão das migrações da R2 e testes no Supabase local com PostgreSQL 17. Os testes assumem `anon`, `authenticated` e o papel do backend, simulam `auth.uid()` e desfazem suas alterações. |
| API FastAPI | Leitura de `backend/src` e testes com `TestClient` para cabeçalhos, CORS, limites e regras de abuso. |
| Front-end | Busca por pontos que interpretam conteúdo vindo do banco (links, HTML) e pelas chamadas diretas ao Supabase. |
| Dependências e segredos | `pip-audit`, `npm audit` e varredura do histórico Git por padrões de chave. |

O escopo inclui Google Agenda, lembretes, votos, coleta, importação e ciclo de vida dos dados. Auth e Storage foram exercitados no Supabase local. O aceite hospedado de TLS, CORS, SMTP, OAuth e configuração do painel segue na [#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76) e na [#85](https://github.com/unb-mds/2026-2-AgendaUnB/issues/85).

## Achados

Severidade segundo o impacto no produto: **Alta** permite agir como outra conta ou ganhar papel indevido; **Média** amplia a superfície ou permite abuso; **Baixa** tem impacto restrito à própria conta ou depende de outra falha.

| # | Sev. | Achado | Tratamento | Estado |
| --- | --- | --- | --- | --- |
| A1 | Alta | **Script armazenado pelo link do evento.** Qualquer conta logada inseria direto em `eventos` pelo supabase-js, sem a validação de URL da API. Um `link_externo` com `javascript:` chegava ao catálogo (sugestão aprovada ou publicação de professor) e a página do evento o abria com `window.open`, executando código na sessão de quem clicasse. A tela de moderação ocultava o link inválido, o que dificultava perceber o problema ao aprovar. | INSERT direto removido; o banco só aceita `http(s)` no link, em qualquer caminho; a página do evento filtra o esquema e abre com `noopener,noreferrer`. | Corrigido (`20261117130000`, `PaginaDeEvento.jsx`) |
| A2 | Alta | **Papel de professor sem prova de posse do e-mail.** O cadastro com papel `professor` e endereço `@unb.br` criava o perfil de professor antes de qualquer confirmação. Em um projeto com confirmação de e-mail desligada, bastaria informar um `@unb.br` alheio para publicar e moderar eventos. | O papel só é concedido com `email_confirmed_at` preenchido: no cadastro quando já confirmado, ou automaticamente ao confirmar. A autopromoção pelo navegador exige o mesmo. A API recusa conta sem e-mail confirmado (403). A regra entrou na `dev` pela S7-F04 (`20261111150000`); o endurecimento mantém só a correção dos perfis já criados como professor sem confirmação. | Corrigido. **Pendente:** conferir no painel do projeto hospedado que *Confirm email* está ligado. |
| A3 | Alta | **Bloqueio da importação de outra conta.** A unicidade global de `origem_avaliacao_id` deixava o usuário B ocupar o candidato de A com um evento na própria agenda, fazendo a confirmação de A falhar. | Unicidade por `(user_id, origem_avaliacao_id)`. | Corrigido na S7-D01 (`20261109120000`) |
| A4 | Média | Função `SECURITY DEFINER` `confirmar_candidatos_transacional` sem uso, operando sobre tabela removida. | Função removida. | Corrigido na S7-D01 |
| A5 | Média | `registrar_interesse(uuid)` chamável por visitantes, sem limite e sem deduplicação: o contador podia ser inflado à vontade. | EXECUTE revogado de `anon` e `authenticated`. O contador volta pela API com `click_id` (S8-B02). | Fechado; substituto na S8-B02 |
| A6 | Média | **Privilégios padrão amplos.** `anon` e `authenticated` tinham todos os privilégios nas tabelas (inclusive `TRUNCATE`, que ignora RLS) e toda função nova nascia executável por visitantes via `/rpc`. A proteção dependia só de cada política estar correta. | GRANT alinhado às políticas, visitante sem escrita, `TRUNCATE` revogado, EXECUTE fechado por padrão. Três testes estruturais impedem regressão. | Corrigido |
| A7 | Média | API sem cabeçalhos de proteção, documentação interativa sempre exposta, CORS com `allow_headers=*` e credenciais habilitadas. | `SecurityHeadersMiddleware`, `API_DOCS_ENABLED`, CORS com origens exatas, cabeçalhos explícitos e sem credenciais. Curinga em `CORS_ORIGINS` impede a API de iniciar. | Corrigido |
| A8 | Média | Sem limite de taxa nem de tamanho de corpo fora do upload; uma conta podia enviar sugestões sem limite, enchendo a fila de moderação. | Limite por cliente em memória, teto de 256 KiB para JSON e de 10 sugestões pendentes por conta. | Corrigido, com a limitação descrita abaixo |
| A9 | Baixa | `%` e `_` da busca eram interpretados como curingas do `LIKE`. | Termo tratado como texto literal. | Corrigido |
| A10 | Baixa | O próprio usuário alterava colunas não previstas do perfil (por exemplo `criado_em`) e gravava qualquer valor em `avatar_url`. | UPDATE restrito a `nome_completo`, `avatar_url` e `papel` (este protegido por trigger); avatar só `https`. | Corrigido |
| A11 | Baixa | O usuário pode gravar na própria agenda um evento com campos de procedência (`origem_*`) forjados. | Sem efeito sobre outras contas desde A3. A API é o único caminho que preenche procedência legítima. Avaliar fechar a escrita direta em `eventos_pessoais` quando nenhum fluxo depender dela. | Aceito e registrado |
| A12 | Média | Originais legados e caminhos de PDF podiam continuar acessíveis. | O upload descarta o PDF após extração. Upload, listagem e detalhes respondem `filePath: null` por compatibilidade. O script da [#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83) inventaria e descarta legados. | Corrigido no contrato. Conferir o inventário hospedado antes da publicação. |
| A13 | Média | A configuração versionada tinha composição de senha e troca segura desabilitadas. | `supabase/config.toml` exige pelo menos 8 caracteres com letras e dígitos e habilita `secure_password_change`. | Configuração local corrigida. Conferir painel e recuperação no projeto hospedado ([#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74)). |
| A14 | Baixa | A auditoria anterior apontou vulnerabilidades em `vite` e `source-map-js`. | Versões corrigidas no lockfile, com build e testes. | `npm audit` passou em 20/11. |
| A15 | Baixa | Dependências Python sem lock integral permitem resoluções diferentes do mesmo commit. | `requirements.txt` restringe `cryptography` às versões `>=50.0.2,<51`. Os demais pacotes seguem as restrições declaradas e são resolvidos no build. | `pip-audit` passou em 20/11. A reprodução integral da resolução segue na [#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76). |
| A16 | Info | Não havia registro de quem mudou o papel de quem. | Tabela `auditoria_papeis`, alimentada por trigger e legível só por admins. | Corrigido |
| A17 | Média | A tabela paralela `fila_processamento_ia` não tinha consumidor. | A migração de consolidação a remove. A fila ativa, usada pelo worker, permanece em `planos_ensino`. | Corrigido na R2 |

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
| `votos_avaliacao` | Recusado | Não lê votos individuais de outra conta | Lê o próprio voto. Escrita e contagens passam pela API. | Sem acesso adicional por papel |
| `lembretes` | Recusado | Não lê nem altera | Lê os próprios disparados e altera apenas `lido_em`. | Sem acesso adicional por papel |
| `operacoes_importacao`, `itens_importacao` | Recusado | Não lê nem altera | Lê as próprias operações e seus itens. | Sem acesso adicional por papel |
| `aceites_termos`, `consentimentos` | Recusado | Não lê nem altera | Conta confirmada lê os próprios registros. Escritas passam pela API. | Sem acesso adicional por papel |
| `google_calendar_connections`, `google_calendar_oauth_states`, `google_calendar_event_exports` | Recusado | Recusado | Consulta e exportação pelos contratos da API | Nenhum acesso direto pelo navegador |
| `cliques_evento`, `coletas_eventos`, `sincronizacoes_catalogo`, `exclusoes_conta` | Recusado | Recusado | Recusado | Nenhum acesso direto pelo navegador |
| `auditoria_papeis` | Recusado | Recusado | Recusado | Só admin lê |
| RPCs administrativas | Recusado | Recusado | Recusado | Só admin; moderação também para professor |

Travas estruturais, válidas para qualquer migração futura:

- toda tabela de `public` tem RLS habilitado;
- toda função `SECURITY DEFINER` e toda função chamável por conta logada fixa o `search_path`;
- nenhuma função é chamável por visitante;
- visitante não tem privilégio de escrita, e ninguém da API tem `TRUNCATE`;
- todo privilégio de escrita de conta logada corresponde a uma política.

## Regras para novas migrações

A partir de `20261117130000`, tabelas e funções novas nascem fechadas:

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
| `TRUSTED_PROXY_HOPS` | Configuração para hospedagem própria. No Render, o limitador usa o IP inserido pela borda em `CF-Connecting-IP`. |
| `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_WRITE_PER_MINUTE` | Padrões `240` e `60`; ajustar após medir o uso real. |
| `DATABASE_URL` | Com TLS (`sslmode=require` quando o provedor não o impuser). |

Iniciar com `uvicorn src.main:app --host 0.0.0.0 --port $PORT --no-server-header`, sem `--reload`.

### SPA (Vercel)

- [ ] Configure `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` e `VITE_API_URL` no build. `VITE_SUPABASE_ANON_KEY` é a alternativa pública para projetos com chave legada. Credenciais de servidor ficam fora do prefixo `VITE_`.
- [x] Cabeçalhos globais de segurança e fallback de SPA versionados em `frontend/vercel.json`. O retorno OAuth mantém `Referrer-Policy: no-referrer`. A resposta hospedada fica no aceite da [#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76).
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
| Conferir o inventário de PDFs legados com `backend/scripts/descartar_pdfs.py` antes da publicação. As respostas HTTP mantêm `filePath: null` por compatibilidade. | Felipe, com Heitor | [#83](https://github.com/unb-mds/2026-2-AgendaUnB/issues/83), [#51](https://github.com/unb-mds/2026-2-AgendaUnB/issues/51) |
| Política de senha e fluxo de confirmação (A13) | Thomas, com Thomaz | [#74](https://github.com/unb-mds/2026-2-AgendaUnB/issues/74) |
| Manter auditoria de dependências. A consolidação atualizou Vite, `source-map-js` e `cryptography`. `npm audit` e `pip-audit` passaram em 20/11. As demais dependências Python continuam resolvidas no build. | Front-end e Luis | [#76](https://github.com/unb-mds/2026-2-AgendaUnB/issues/76) |
| Isolamento de tokens e mapeamentos do Google Calendar | Luis, com Thomaz | [#82](https://github.com/unb-mds/2026-2-AgendaUnB/issues/82) |
| Repetir a matriz integrada de votos, lembretes, coleta e importação no ambiente publicado. | Felipe | [#75](https://github.com/unb-mds/2026-2-AgendaUnB/issues/75), [#72](https://github.com/unb-mds/2026-2-AgendaUnB/issues/72), [#77](https://github.com/unb-mds/2026-2-AgendaUnB/issues/77), [#81](https://github.com/unb-mds/2026-2-AgendaUnB/issues/81) |

Consulte também [ADR-006](../arquitetura/adrs/adr-006-autorizacao-em-camadas.md), [Banco de dados](../arquitetura/banco-de-dados.md) e [Implantação](../implantacao.md).
