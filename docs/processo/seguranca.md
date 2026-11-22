---
title: "Verificação de segurança"
description: "Controles de segurança, matriz de acesso, regras de migração e configuração segura do Agenda UnB."
---

Este documento reúne os controles de segurança implementados, a matriz de acesso por papel, as travas estruturais para migrações e os requisitos de configuração por ambiente.

## Escopo e método de verificação

| Camada | Como é avaliada |
| --- | --- |
| Banco exposto (PostgREST/supabase-js) | Revisão das migrações e testes automatizados no Supabase local com PostgreSQL. Os testes assumem `anon`, `authenticated` e o papel do backend, simulam `auth.uid()` e desfazem suas alterações. |
| API FastAPI | Inspeção de `backend/src` e testes com `TestClient` para cabeçalhos, CORS, limites e regras de abuso. |
| Front-end | Verificação dos pontos que interpretam conteúdo vindo do banco (links, HTML) e das chamadas diretas ao Supabase. |
| Dependências e segredos | `pip-audit`, `npm audit` e varredura do histórico Git por padrões de chave. |

O escopo cobre Google Agenda, lembretes, votos, coleta de eventos, importação de planos, Auth, Storage e ciclo de vida dos dados.

## Controles e salvaguardas implementados

Severidade segundo o impacto no produto: **Alta** permite agir como outra conta ou ganhar papel indevido; **Média** amplia a superfície ou permite abuso; **Baixa** tem impacto restrito à própria conta ou depende de outra falha.

| # | Sev. | Risco mitigado | Controle aplicado |
| --- | --- | --- | --- |
| A1 | Alta | **Script armazenado pelo link do evento.** Inserção direta em `eventos` via `supabase-js` sem validação de URL podia gravar `link_externo` com esquema `javascript:` e executá-lo via `window.open`. | Escrita direta removida; o banco aceita apenas `http(s)` em `link_externo` e `PaginaDeEvento.jsx` filtra o esquema e abre com `noopener,noreferrer`. |
| A2 | Alta | **Papel de professor sem posse de e-mail confirmada.** Cadastro ou promoção com `@unb.br` antes da confirmação de e-mail permitiria acesso indevido a moderação e publicação. | O papel `professor` só é concedido com `email_confirmed_at` preenchido (no cadastro já confirmado ou após confirmação); autopromoção exige a mesma condição e a API bloqueia contas não confirmadas (`403`). Exige *Confirm email* ligado no projeto Supabase hospedado. |
| A3 | Alta | **Bloqueio de importação entre contas.** Unicidade global de `origem_avaliacao_id` permitia que uma conta bloqueasse a importação do mesmo candidato por outra. | Unicidade escopada por `(user_id, origem_avaliacao_id)` (`20261109120000`). |
| A4 | Média | Função `SECURITY DEFINER` obsoleta (`confirmar_candidatos_transacional`) operando sobre tabela removida. | Função removida do esquema. |
| A5 | Média | Contagem de cliques via RPC pública (`registrar_interesse(uuid)`) sem limite nem deduplicação. | Função legada removida; o registro de cliques externos opera via API (`POST /api/v1/events/{id}/outbound-clicks`) com deduplicação por `click_id`. |
| A6 | Média | **Privilégios padrão amplos.** `anon` e `authenticated` herdavam privilégios excessivos (incluindo `TRUNCATE`) e novas funções nasciam executáveis via `/rpc`. | `GRANT`s alinhados às políticas RLS, visitante sem escrita, `TRUNCATE` revogado e `EXECUTE` fechado por padrão, com três testes estruturais contra regressão. |
| A7 | Média | API sem cabeçalhos de proteção, documentação interativa sempre exposta e CORS permissivo. | `SecurityHeadersMiddleware`, `API_DOCS_ENABLED` configurável, CORS com origens exatas, cabeçalhos explícitos e sem credenciais. Curinga em `CORS_ORIGINS` impede a API de iniciar. |
| A8 | Média | Ausência de limite de taxa, teto de payload JSON ou limite na fila de sugestões por conta. | Limitador de taxa por cliente em memória, teto de 256 KiB para JSON e máximo de 10 sugestões pendentes por conta. |
| A9 | Baixa | Curingas `%` e `_` na busca tratados como padrões do `LIKE`. | Termo de busca escapado e tratado como texto literal. |
| A10 | Baixa | Alteração de colunas não previstas em `profiles` ou gravação arbitrária em `avatar_url`. | `UPDATE` restrito a `nome_completo`, `avatar_url` (apenas `https`) e `papel` (protegido por trigger). |
| A11 | Baixa | Gravação direta de campos de procedência (`origem_*`) na própria agenda em `eventos_pessoais`. | Risco residual aceito: restrito à própria conta, sem efeito sobre terceiros; a API é o caminho legítimo que preenche procedência. |
| A12 | Média | Retenção prolongada de PDFs originais e exposição de caminhos no Storage. | Upload descarta o PDF após extração em memória e retorna `filePath: null` por compatibilidade; `scripts/descartar_pdfs.py` inventaria e descarta objetos legados. |
| A13 | Média | Política fraca de composição de senha e troca sem confirmação. | `supabase/config.toml` exige ao menos 8 caracteres com letras e dígitos e habilita `secure_password_change` (configuração equivalente deve ser conferida no painel hospedado). |
| A14 | Baixa | Vulnerabilidades conhecidas em pacotes de build do frontend (`vite`, `source-map-js`). | Lockfile atualizado para versões corrigidas, verificado com `npm audit`. |
| A15 | Baixa | Dependências Python sem trava integral podem variar entre builds. | `requirements.txt` restringe `cryptography` a `>=50.0.2,<51`; demais pacotes seguem as restrições declaradas e são auditados via `pip-audit`. |
| A16 | Info | Ausência de trilha de auditoria para alterações de papel. | Tabela `auditoria_papeis`, alimentada por trigger e legível apenas por administradores. |
| A17 | Média | Tabela paralela `fila_processamento_ia` sem consumidor ativo. | Tabela removida; a fila ativa do worker permanece exclusivamente em `planos_ensino`. |

A varredura do histórico Git por chaves do Google, do Supabase, JWTs de serviço, URLs de banco com senha e chaves privadas não encontrou segredos versionados. Qualquer credencial que tenha circulado fora do repositório deve ser rotacionada antes da publicação.

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

- **Authentication → Sign In / Providers → Email → Confirm email: ligado.** Sem isso, a proteção contra promoção indevida de papel volta a depender exclusivamente do banco.
- Senha mínima de 8 caracteres ou mais, com letras e dígitos; *Secure password change* ligado.
- *Site URL* e *Redirect URLs* restritos às URLs da SPA daquele ambiente.
- SMTP próprio configurado e limites de envio revisados.
- **Database → Settings → Enforce SSL on incoming connections: ligado** (RNF03).
- Chave `service_role`/secreta e senha do banco apenas nas variáveis do servidor — nunca em variável `VITE_*`, no repositório ou em comunicações externas.
- *Security Advisor* do painel sem alerta de RLS após cada `db push`.
- Projetos, bancos e chaves distintos para homologação e produção.

### API (Render)

| Variável | Valor em homologação/produção |
| --- | --- |
| `CORS_ORIGINS` | Somente a URL HTTPS da SPA do ambiente. Curinga impede a API de iniciar. |
| `API_DOCS_ENABLED` | `false` |
| `TRUSTED_PROXY_HOPS` | Configuração para hospedagem própria. No Render, o limitador usa o IP inserido pela borda em `CF-Connecting-IP`. |
| `RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_WRITE_PER_MINUTE` | Padrões `240` e `60`; ajustar conforme o tráfego observado. |
| `DATABASE_URL` | Com TLS (`sslmode=require` quando o provedor não o impuser). |

Iniciar com `uvicorn src.main:app --host 0.0.0.0 --port $PORT --no-server-header`, sem `--reload`.

### SPA (Vercel)

- Configure `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` e `VITE_API_URL` no build. `VITE_SUPABASE_ANON_KEY` é a alternativa pública para projetos com chave legada. Credenciais de servidor ficam fora do prefixo `VITE_`.
- Cabeçalhos globais de segurança e fallback de SPA versionados em `frontend/vercel.json`. O retorno OAuth mantém `Referrer-Policy: no-referrer`.
- Previews sem credenciais de produção.

## Como repetir a verificação

```bash
# banco: Supabase local em execução e TEST_SUPABASE_DB_URL apontando para ele
cd backend
python -m pytest tests/test_security_database.py tests/test_security_api.py -q

# dependências
pip install pip-audit && pip-audit -r requirements.txt
cd ../frontend && npm audit
```

Consulte também [ADR-006](/arquitetura/adrs/adr-006-autorizacao-em-camadas), [Banco de dados](/arquitetura/banco-de-dados) e [Implantação](/implantacao).
