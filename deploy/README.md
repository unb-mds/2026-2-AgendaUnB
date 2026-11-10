# Supabase Cloud + Render + Vercel

O banco `pzniltzdhyuzzdqbppjw` recebeu as cinco migrações pendentes em
10/11/2026. O [registro da operação](../docs/supabase-nuvem-2026-11-10.md)
descreve backup, testes, preservação dos dados e limitações.

## Render

| Configuração | API | Worker de extração |
| --- | --- | --- |
| Tipo de serviço | Web Service / Python | Background Worker / Python |
| Repositório | `unb-mds/2026-2-AgendaUnB` | Mesmo repositório |
| Branch com a implementação atual | `dev` | `dev` |
| Root Directory | `backend` | `backend` |
| Build Command | `pip install -r requirements.txt` | Mesmo comando |
| Start Command | `uvicorn src.main:app --host 0.0.0.0 --port $PORT` | `python -m src.modules.syllabus.worker` |
| Health Check Path | `/health` | Não recebe HTTP |
| Variáveis | `render.env.example`, preenchido | Mesmo conjunto de servidor |

A API pode usar uma instância Free para homologação, sujeita a suspensão por
inatividade. Background Worker não oferece instância Free. A definição de
hospedagem/custo do worker permanece pendente na #68; nenhum serviço pago foi
provisionado. Não ativar deploy do worker com as flags em `false`, pois ele encerra
com uma mensagem de configuração pendente. Após a aprovação de S7-B02 e a
homologação, ativar as três flags e publicar o worker. A API precisa das mesmas
flags para disponibilizar o fluxo de autorização/extração.

Usar a conexão Session Pooler oferecida pelo projeto e manter `sslmode=require`.
A senha na URL precisa estar codificada como componente de URL. O arquivo privado
preparado durante esta operação já contém a conexão funcional e a chave Gemini
encontrada no ambiente, sem divulgar valores no repositório.

## Vercel

| Configuração | Valor |
| --- | --- |
| Framework Preset | Vite |
| Root Directory | `frontend` |
| Branch com a implementação atual | `dev` |
| Install Command | `npm ci --include=dev` |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Variáveis | As três de `vercel.env.example`, preenchidas |

O `frontend/vercel.json` já contém o fallback SPA. O `envDir: '..'` atende o
desenvolvimento local; variáveis definidas no painel Vercel são fornecidas ao
processo de build. Configurar `VITE_API_URL` com a URL HTTPS da API Render,
**incluindo `/api/v1`**, e fazer novo build após alterar `VITE_*`.
Senha do banco, service_role e Gemini pertencem exclusivamente ao Render.
Previews devem usar ambiente e credenciais de homologação próprios; não copiar
automaticamente as credenciais do banco compartilhado para todos os previews.

## Chaves e retornos de autenticação

1. No painel Supabase do projeto, copiar a chave publishable/anon existente para
   `SUPABASE_ANON_KEY` no Render e `VITE_SUPABASE_ANON_KEY` na Vercel. As duas
   representam o mesmo projeto. A chave pública local testada retornou HTTP 401
   no endpoint `/auth/v1/settings` remoto.
2. Para o cliente Storage atual, preencher `SUPABASE_SERVICE_ROLE_KEY` no Render
   com a chave JWT legada `service_role`. `sb_secret_*` não é JWT e exige adaptar
   os cabeçalhos do cliente antes de usá-la nessa implementação.
3. No Supabase Auth, configurar Site URL e Redirect URLs com a origem HTTPS da
   Vercel usada pela aplicação. Não inserir `/api/v1` nessas origens.
4. Configurar `CORS_ORIGINS` no Render com a mesma origem da SPA, sem caminho ou
   barra final. Incluir somente os domínios aprovados para o ambiente.
5. Se usar Google OAuth, configurar o provedor no painel Supabase e o callback
   `https://pzniltzdhyuzzdqbppjw.supabase.co/auth/v1/callback` no Google.
   As variáveis `SUPABASE_AUTH_EXTERNAL_GOOGLE_*` do Supabase CLI local não
   configuram automaticamente o provedor hospedado.

## Publicação e verificações restantes

Aplicar as variáveis e publicar a API; conferir `/health` e
`/api/v1/events`, além de campus/categorias usados pela interface.
Publicar o frontend após definir a URL da API e conferir rotas profundas após
refresh. Com contas sintéticas autorizadas para homologação, testar cadastro,
confirmação, recuperação, OAuth, sessão na API e isolamento entre usuários.
Depois validar envio de PDF/texto, edição e autorização do texto exato, worker,
consulta dos candidatos e confirmação particular.

O esquema passou nos testes de banco. A jornada HTTP hospedada e a aprovação de
termos/elegibilidade não foram comprovadas nesta operação; as três flags ficaram
em `false`. O worker atual utiliza lease em `planos_ensino`, não consome a tabela
paralela `fila_processamento_ia`. Não iniciar um segundo consumidor para o mesmo
plano. A política dessa fila paralela ainda usa `professor_id`; revisar seu uso
antes de conectá-la ao acompanhamento de planos particulares por `user_id`.

Fontes oficiais consultadas em 10/11/2026:
[FastAPI no Render](https://render.com/docs/deploy-fastapi),
[versão Python](https://render.com/docs/python-version),
[Background Workers](https://render.com/docs/background-workers),
[instâncias gratuitas](https://render.com/docs/free),
[Vite na Vercel](https://vercel.com/docs/frameworks/frontend/vite) e
[chaves Supabase](https://supabase.com/docs/guides/getting-started/api-keys).
