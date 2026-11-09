# Plano de hospedagem e CI/CD

## Estado e proposta

Documento criado em **24/10/2026**, com referência no commit `e0ecf46`. **Este é um plano, não um registro de infraestrutura implantada.** O repositório comprova somente o workflow `Deploy Docs`, que publica MkDocs no GitHub Pages quando há mudanças pertinentes em `main` ou acionamento manual. Não existe pipeline da aplicação; `backend/Dockerfile` está vazio. A existência de `main` não comprova produção ativa.

| Componente | Proposta | Configuração prevista |
| --- | --- | --- |
| Frontend | Vercel (multi-service ou projeto por ambiente) | Raiz `frontend`, framework `vite`, build `npm run build`, saída `dist`; fallback SPA via `rewrites` |
| Backend | Vercel Services (FastAPI Serverless) ou Render Web Service | Raiz `backend`, framework `fastapi` (`src/main.py`), rotas em `/api/(.*)` e `/health`; ou Render Python 3.11 com `uvicorn src.main:app` |
| Dados, Auth e Storage | Supabase gerenciado | Um projeto de homologação e outro de produção, com migrações SQL versionadas |
| Documentação | GitHub Pages | Manter o workflow MkDocs existente, independente da aplicação |

A proposta utiliza serviços gerenciados para reduzir manutenção operacional. O runtime Python dispensa o Dockerfile vazio; não executar servidor Vite de desenvolvimento nem Uvicorn com `--reload` em hospedagem. Não houve contratação, criação de contas ou deploy nesta entrega.

Fontes oficiais consultadas para a proposta: [Vite na Vercel](https://vercel.com/docs/frameworks/frontend/vite), [FastAPI no Render](https://render.com/docs/deploy-fastapi), [ambientes Supabase](https://supabase.com/docs/guides/deployment/managing-environments) e [limitações gratuitas do Render](https://render.com/docs/free). O Render gratuito suspende serviço após 15 minutos de inatividade e o retorno pode levar cerca de um minuto. Não pressupor disponibilidade contínua gratuita; confirmar limites e orçamento antes da implantação.

## Ambientes e configuração

| Ambiente | Aplicação e dados | Uso e publicação |
| --- | --- | --- |
| Local | Vite/FastAPI + Supabase CLI/Docker | Desenvolvimento e testes; dados descartáveis |
| Homologação | Vercel + Render + projeto Supabase exclusivo | Dados fictícios e contas de teste; recebe `main` após validações |
| Produção | Projetos/serviços separados dos de homologação | Promoção manual do commit homologado, após aprovação do responsável pela release |

URLs, IDs dos projetos, região e responsáveis nominais serão preenchidos quando os recursos forem provisionados. Usar HTTPS público e regiões compatíveis entre API e banco. Não compartilhar banco, usuários, buckets ou segredos entre homologação e produção. Previews de PR não devem receber credenciais de produção.

### Variáveis

| Variável/configuração | Destino | Tratamento |
| --- | --- | --- |
| `VITE_API_URL` | Build Vercel | Pública; URL HTTPS da API **incluindo `/api/v1`**; ausente de `.env.example` atualmente |
| `VITE_SUPABASE_URL` | Build Vercel | Pública; URL do projeto do ambiente |
| `VITE_SUPABASE_ANON_KEY` | Build Vercel | Chave pública anon do ambiente; segurança depende de Auth/RLS |
| `DATABASE_URL` | Runtime Render | Segredo; conexão SQLAlchemy `postgresql+psycopg://...`, credenciais próprias do ambiente e TLS |
| `SUPABASE_URL` | Runtime Render | URL do mesmo projeto usado pelo frontend |
| `SUPABASE_ANON_KEY` | Runtime Render | Chave anon usada na validação do token pelo Auth |
| `CORS_ORIGINS` | Runtime Render | Origens exatas da SPA, separadas por vírgula, sem caminho; evitar curingas |
| `PORT` | Runtime Render | Fornecida pelo provedor; usada pelo comando de início |
| `SUPABASE_AUTH_EXTERNAL_GOOGLE_CLIENT_ID` / `SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET` | Supabase local/configuração do provedor OAuth hospedado | Client ID e segredo do Google; segredo nunca enviado ao bundle |
| `TEST_SUPABASE_DB_URL` | Job de teste | Somente conexão do Supabase local descartável; testes rejeitam host remoto |
| Tokens Vercel/Render/Supabase e senha de migração | GitHub Environments/Secrets | Segredos exclusivos da automação; provisionar somente na implementação do pipeline |

O Vite lê o ambiente na raiz do repositório (`envDir: '..'`) e incorpora `VITE_*` no build. Alterar esses valores exige novo build. Não incluir senha PostgreSQL, chave de serviço ou tokens de deploy em variáveis `VITE_*`, exemplos ou logs. O build precisa das dependências de desenvolvimento: o SDK Supabase está declarado nessa categoria no estado atual.

Configurar a conexão PostgreSQL usando a opção oferecida pelo projeto Supabase que seja alcançável pelo Render, preferindo pooler em modo de sessão quando necessário por conectividade. Confirmar TLS, driver psycopg e limites de conexões antes da homologação. Não afirmar que RLS protege conexões administrativas: o backend também deve aplicar suas verificações de usuário/papel.

### SPA, CORS e arquitetura multi-serviços (Vercel)

A raiz do repositório contém a configuração [`vercel.json`](../vercel.json) operando em modo de múltiplos serviços (Vercel Services):

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "services": {
    "backend": {
      "root": "backend",
      "framework": "fastapi"
    },
    "frontend": {
      "root": "frontend",
      "framework": "vite",
      "rewrites": [
        { "source": "/(.*)", "destination": "/index.html" }
      ]
    }
  },
  "rewrites": [
    { "source": "/health", "destination": { "service": "backend" } },
    { "source": "/api/(.*)", "destination": { "service": "backend" } },
    { "source": "/(.*)", "destination": { "service": "frontend" } }
  ]
}
```

O fallback SPA está configurado tanto nas regras do serviço `frontend` quanto em [`frontend/vercel.json`](../frontend/vercel.json) para garantir acesso direto e recarga em `/eventos`, `/evento/<id>`, `/sugestoes`, `/admin` e `/plano-de-ensino`.

A SPA consome a API através de URLs relativas (`/api/v1/...`), aproveitando o roteamento unificado da Vercel no mesmo domínio sem requisições cross-origin (CORS). Se necessário apontar para um backend externo, a variável `VITE_API_URL` pode ser preenchida no ambiente.

> [!WARNING]
> **Atenção ao limite de upload (4,5 MB nas Vercel Functions):**
> O fluxo atual de upload de planos de ensino em `/api/v1/syllabus/upload` suporta arquivos de até 10 MB no FastAPI. Contudo, o limite de payload de requisições nas Vercel Serverless Functions é de 4,5 MB. Arquivos maiores que esse limite serão rejeitados com HTTP 413 pela camada de borda da Vercel antes de alcançar o FastAPI.
> Caso uploads entre 4,5 MB e 10 MB devam ser suportados sem falhas:
> 1. Adotar upload direto do frontend para o Supabase Storage via client SDK com RLS ou pre-signed URLs (enviando ao FastAPI apenas metadados/referência); ou
> 2. Manter a execução do backend como Web Service dedicado (ex: Render/container) para as rotas com transferências volumosas.

Configurar no Supabase a Site URL da SPA e as URLs de retorno necessárias para login OAuth/confirmação de e-mail de cada ambiente. No Google, registrar o callback fornecido pelo projeto Supabase correspondente. Manter as origens de homologação e produção separadas; não abrir CORS de produção para previews arbitrários.

## Fluxo de CI/CD proposto

Nenhuma etapa abaixo existe como workflow da aplicação nesta referência. O workflow de documentação continua independente.

1. **PR:** instalar dependências; executar pytest com SQLite, testes de calendário, build frontend e MkDocs. Subir Supabase local descartável, aplicar migrações/seed e executar os testes PostgreSQL com `TEST_SUPABASE_DB_URL` local. Falha bloqueia promoção; teste ignorado não equivale a aprovação de RLS.
2. **Merge em `main`:** repetir as verificações do commit final e publicar homologação, com exclusão mútua por ambiente para impedir migrações/deploys simultâneos. Somente jobs com sucesso liberam a sequência de publicação.
3. **Banco:** conferir projeto de destino e migrações pendentes; aplicar migrações versionadas antes do código dependente. Usar Supabase CLI autenticada com alvo explícito e `db push` após revisão. Não executar `db reset` nem seed demonstrativo em banco persistente.
4. **Backend:** publicar exatamente o SHA validado. Verificar `/health` e uma leitura real de eventos: `/health` sozinho não testa banco/Auth.
5. **Frontend:** gerar build do mesmo SHA com variáveis do ambiente e publicar. Executar os testes de fumaça abaixo.
6. **Produção:** acionamento manual informa o SHA homologado e exige aprovação do responsável pela release. Repetir banco → backend → frontend → fumaça com configuração de produção. Como `VITE_*` muda por ambiente, usar o mesmo código-fonte, não reutilizar cegamente o bundle de homologação.

Desabilitar deploy automático independente dos provedores quando o workflow assumir a publicação; do contrário, um push pode publicar código antes das migrações ou dos testes. Preservar o SHA e o resultado de cada etapa no registro de release. Congelar versões das ferramentas/dependências em tarefa futura: as dependências Python atuais não são fixadas, portanto o mesmo SHA ainda não garante build reproduzível.

### Recuperação e acompanhamento

- Exigir migrações compatíveis com a versão anterior durante a transição; alterações destrutivas precisam de plano próprio antes da promoção.
- Se migração falhar, interromper a publicação. Se API/SPA falhar, restaurar a versão anterior conhecida nos provedores, conferindo compatibilidade com o schema vigente.
- Rollback de código não desfaz migração. Para banco, priorizar migração corretiva; restauração só após avaliar perda de dados, janela e backup disponível. Verificar e ensaiar restauração em ambiente separado antes de depender dela.
- Acompanhar logs da API, erros HTTP, falhas de autenticação e execução de migrações; registrar horário, SHA, resultado e responsável. O monitoramento completo ainda é pendência de implementação.

## Homologação e aceite operacional

Usar duas contas estudantes, uma professora e uma administradora fictícias, criadas pelo fluxo Auth. Não incluir credenciais em documentação. Os testes automatizados de banco devem continuar no Supabase local descartável; verificar o ambiente hospedado por testes de fumaça controlados, sem contornar a restrição de host da suíte.

| Cenário | Resultado esperado |
| --- | --- |
| Login por senha/OAuth e retorno para SPA | Sessão válida no projeto correto, sem redirecionamento para ambiente errado |
| Catálogo anônimo | Apenas aprovados; filtros e paginação funcionam |
| CRUD privado com duas contas | Dono cria/consulta/atualiza/exclui; outra conta recebe 404 para o recurso |
| Papéis e publicação | Estudante não publica diretamente; professor/admin publicam e excluem |
| Salvar/remover público repetidamente | Sem duplicatas; remover vínculo não remove evento; usuários isolados |
| Sugestão aprovada/recusada | Pendência fora do catálogo; recusa exige justificativa; avisos ao autor; segunda decisão recusada |
| Administração | Só admin altera terceiros; cargo divergente detectado; sem autorrebaixamento |
| RLS de notificações e Storage | Usuário não lê/atualiza recursos alheios; bucket permanece privado; isso não implica fluxo de upload implementado |
| Rotas SPA e CORS | Acesso direto funciona; origem autorizada integra API; origem não permitida não recebe liberação CORS |
| Saúde e dependências | `/health` responde e leituras reais/autenticação também funcionam |

Aceitar a implantação apenas com evidências registradas de migrações, builds, testes de fumaça e recuperação preparada. Não marcar como homologado somente porque um deploy terminou.

## Pendências e responsabilidades propostas

| Pendência futura | Papel responsável |
| --- | --- |
| Aprovar arquitetura final (Vercel multi-service vs Render para backend) considerando o limite de 4,5 MB de upload | Time e responsável pela release |
| Validar comportamento de upload de planos de ensino em ambiente hospedado Vercel | Backend e Frontend |
| Provisionar projetos Supabase, Auth, migrações, dados de homologação e recuperação | Banco de dados, com Backend |
| Criar workflows, secrets por ambiente, gates e publicação pelo SHA | Time, com Backend |
| Atualizar este documento com evidências e URLs efetivas | Responsável pela release |

Nenhum desses papéis representa atribuição nominal já aprovada. Mudanças de hospedagem, variáveis, migrações ou pipeline devem atualizar este documento no mesmo PR. Ver [Arquitetura](Architecture.md), [Contratos](api-specs.md) e [Contribuição](processo/contribuindo.md).
