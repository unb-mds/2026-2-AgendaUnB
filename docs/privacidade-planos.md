# Privacidade e revisão de planos — S6-D02

Migração: `20261109130000_privacidade_e_revisao_planos.sql`, depois da modelagem
S6-D01 e da fila S6-B01. A revisão é explícita: upload e worker não chamam a função
de confirmação. Esta entrega não implementa a tela nem a rota HTTP S6-B02.

## Lacunas encontradas e correções

| Antes | Correção S6-D02 |
| --- | --- |
| `avaliacoes sao publicas` expunha datas acadêmicas legadas | SELECT restrito ao dono do plano |
| Candidatos com RLS, sem política de leitura | Dono lê somente os candidatos de seus planos |
| Cliente podia inserir plano com campos de processamento forjados | Escritas em planos/candidatos/avaliações são exclusivas do servidor |
| Sem confirmação transacional | RPC explícita valida dono, seleção, execução atual e estado concluído |
| Sem proteção contra repetição/concorrência | Lock do plano e vínculo único retornam o mesmo evento sem reinserir |
| Storage verificava só a primeira pasta | Exige exatamente `<dono>/<arquivo>.pdf`, sem subpastas ou barras invertidas |

## Matriz de acesso

| Recurso | Anônimo | Dono autenticado | Outro estudante/professor/admin | Servidor |
| --- | --- | --- | --- | --- |
| Planos e avaliações legadas | Sem acesso | SELECT próprio | Sem acesso ao plano alheio | Conexão privilegiada, com validação obrigatória |
| Candidatos e vínculo com evento | Sem acesso | SELECT próprio | Sem acesso ao plano alheio | Worker insere; revisão altera pela RPC |
| Escrita direta nos três recursos | Negada | Negada | Negada | Permitida com credencial de servidor |
| Objetos `syllabus_files` | Nenhuma política permite acesso | INSERT/SELECT na própria pasta | Sem acesso à pasta alheia | Storage service role |
| `revisar_candidatos_plano` | Execução negada | Seleção do próprio plano concluído | Não revisa plano alheio | Conexão SQL precisa de identidade autenticada verificada |

RLS não protege conexões que a ignoram. O backend deve validar o JWT, obter o dono
da sessão e conferir propriedade em todas as consultas. A autoria de um plano é
imutável por trigger, inclusive no backend. Outro trigger impede ligar um candidato
ao evento de um usuário diferente. A alteração/exclusão normal de eventos pessoais
continua regida pelo CRUD e pela RLS existentes.

A política do bucket é substituída sem recriá-lo; PDFs existentes não são apagados.
Novas políticas aceitam PDF na pasta única do dono e mantêm o bucket privado, com
limite de 10 MB. A suíte verifica as políticas reais de `storage.objects` no
PostgreSQL; isso não equivale a testar download/upload binário pela API HTTP do
Storage. Referência: [RLS Supabase](https://supabase.com/docs/guides/database/postgres/row-level-security).

## Contrato transacional para S6-B02

`public.revisar_candidatos_plano(p_plano_id uuid, p_itens jsonb) → jsonb`

`p_itens` é uma lista de 1–100 objetos. Todos exigem `candidato_id` e `acao`.

- `acao: "confirmar"`: `data_hora` ISO com offset explícito é obrigatória; `titulo`
  corrigido é opcional (padrão: título do candidato, válido somente com 3–200
  caracteres); `descricao` opcional aceita até 10.000 caracteres.
- `acao: "descartar"`: somente os dois campos obrigatórios, sem dados de evento.
- IDs repetidos, campos extras, candidato de outro plano/execução, plano ainda
  processando, data inválida ou sem fuso causam erro e rollback de todo o lote.

Exemplo de chamada após revisão humana:

```sql
select public.revisar_candidatos_plano(
  '<id-do-plano>'::uuid,
  '[{"candidato_id":"<id-do-candidato>","acao":"confirmar",
     "titulo":"Prova revisada","data_hora":"2026-11-10T14:00:00-03:00"}]'::jsonb
);
```

Resposta: `{"plano_id": "...", "itens": [{"candidato_id": "...", "status":
"confirmado", "evento_pessoal_id": "..."}]}`. Descartados têm evento nulo.
O retorno inclui somente os itens solicitados; candidatos não selecionados ficam
pendentes. Erros: `42501` para falta de autenticação/permissão, `P0002` para plano
ou candidato indisponível e `22023` para seleção/dados/estado inválidos.

Chamadas repetidas/concorrentes retornam o vínculo já criado, sem modificar um
evento que o dono editou posteriormente. Excluir o evento deixa o candidato
confirmado com vínculo nulo; nova confirmação não o recria. Não se confirma um
candidato descartado nem se descarta um candidato já confirmado.

A função usa `security definer`, `search_path` vazio, tabelas qualificadas e
permissão de execução somente para `authenticated` (além do dono da função).
`service_role` não recebe execução dessa RPC: o worker não precisa dela. O futuro
endpoint pode usar o JWT do usuário ou a conexão SQL privilegiada, mas nesse último
caso deve definir `request.jwt.claim.sub` com `set_config(..., true)` dentro da
mesma transação, **a partir da sessão verificada**, e nunca de `user_id` do payload.
Não aceitar SQL/GUCs fornecidos pelo cliente. Referência:
[funções Supabase](https://supabase.com/docs/guides/database/functions).

## Teste local executado em 09/11/2026

Uma instância PostgreSQL/Supabase separada, `agendaunb-s6d02-tests`, foi criada na
porta 15322, sem modificar/resetar o banco do projeto na porta 14322. As migrações
foram aplicadas do zero com `supabase db start` em um diretório temporário que
continha cópias das migrações e configuração local sem segredos/OAuth.

Na pasta `backend`, com `TEST_SUPABASE_DB_URL` apontando exclusivamente ao banco
local migrado:

```bash
python -m pytest tests/test_syllabus_database.py tests/test_moderation_database.py -q
```

Resultado inicial: **26 testes passaram**, nenhum ignorado. Incluem dono/outro
estudante/professor/admin/anon, leitura privada de avaliações legadas, negação de
escritas diretas, política do Storage, alteração de autoria, vínculo cruzado,
confirmação parcial, rollback, idempotência, exclusão/edição posterior e duas
confirmações simultâneas usando conexões PostgreSQL diferentes.

Validação final após a checagem do worker e testes de recuperação: **118 testes
passaram na suíte completa, nenhum ignorado**, incluindo 28 testes no PostgreSQL.
Foram testados `SKIP LOCKED`, lease expirado, fencing e regressões de privilégios,
políticas de leitura, função de revisão e papel da política de Storage.

Os testes comuns usam transações com rollback. O teste concorrente cria somente
usuário/plano sintéticos confirmados entre conexões e remove esses registros no
final. Nenhum teste envia PDF real ao Gemini nem altera as flags do worker.

### Verificação de pré-requisitos sem ativar processamento

Na pasta `backend`, usando somente a variável de teste local:

```powershell
$env:TEST_SUPABASE_DB_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:15322/postgres"
.\venv\Scripts\python.exe scripts/check_syllabus_privacy.py
.\venv\Scripts\python.exe -m pytest tests -q
```

A senha acima é o padrão do ambiente local descartável, não uma credencial de
produção. A checagem não mostra credenciais, não chama Gemini e não habilita flags.
O script rejeita hosts remotos. No banco isolado, retornou `ready: true` para:
migração, RLS, privilégios do cliente, políticas do dono, privilégios da revisão,
triggers de autoria/vínculo, bucket privado e políticas do Storage.

O worker executa a mesma verificação de metadados no banco configurado antes de
iniciar. As flags sozinhas não liberam banco sem migração/permissões corretas.
Ela detecta pré-requisitos e regressões comuns; não substitui os testes de acesso
nem prova equivalência de expressões arbitrárias de políticas. A checagem é
estrita para o conjunto atual de políticas: políticas novas legítimas exigem
revisar os testes e esse contrato, em vez de presumir liberação automática.

Uma consulta somente de leitura em 09/11/2026 encontrou **duas migrações pendentes
no banco da aplicação, porta 14322**: `20261109120000_fila_processamento_planos.sql`
e `20261109130000_privacidade_e_revisao_planos.sql`. Elas foram aplicadas somente
no banco isolado 15322 nesta entrega; o banco da aplicação não foi migrado/resetado.

## O que ainda falta para habilitar dados reais

1. Aplicar a migração S6-D02 no **ambiente de destino**, além de #40/S6-D01/S6-B01;
   a aprovação do banco isolado não aplica mudanças ao Supabase usado pela API.
2. Repetir testes de privacidade no ambiente local/homologação correspondente e
   verificar Auth/Storage HTTP, credenciais e caminho privado ponta a ponta.
3. Conferir termos/tier de tratamento de dados do provedor de IA e separar os
   segredos por ambiente. `store=false` não substitui essa avaliação.
4. Só então configurar `SYLLABUS_WORKER_ENABLED=true` e
   `SYLLABUS_PRIVACY_READY=true` no servidor de destino. Nenhuma flag de `.env`
   foi habilitada automaticamente nesta entrega.

A tela e a rota de revisão/consulta de candidatos da S6-B02 são uma entrega
separada; a função de banco já fornece o contrato e as garantias de persistência.
