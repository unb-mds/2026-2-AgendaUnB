# Supabase Cloud, Render e Vercel

Use o [guia de implantação](../docs/implantacao.md) para validar o SHA, aplicar migrações, publicar e executar os testes de fumaça. Para backup e recuperação, consulte o [roteiro de entrega](../docs/processo/roteiro-entrega.md).

| Serviço | Configuração |
| --- | --- |
| Supabase Cloud | PostgreSQL, Auth, Storage e Cron. Use Session Pooler com TLS e configure SMTP e retornos de login diretamente no painel Auth. |
| Render | FastAPI. [Blueprint](../render.yaml) com raiz `backend`, Docker Python 3.11, `$PORT` e `/health`. As variáveis estão em [render.env.example](render.env.example). |
| Vercel | Root Directory `frontend`, Vite, `npm ci`, `npm run build`, saída `dist`. [Configuração de rotas e busca](../frontend/vercel.json) e [variáveis públicas](vercel.env.example). |
| GitHub Actions | [Jobs de produção](../.github/workflows/production-jobs.yml) em `main`. `worker --drain --max-items 25` retoma os planos, `collector` coleta a Agenda UnB Notícias e `catalog` sincroniza ofertas sob demanda. |

1. Confira o projeto Supabase e o histórico de migrações. Revise e aplique as versões pendentes antes de publicar a API dependente. O ambiente que já recebeu o compartilhamento precisa de `--include-all` para incluir a migração de endurecimento anterior.
2. Confirme o Health Check e o preflight do Render, além de uma consulta ao PostgreSQL via API. Configure o OAuth do Google Agenda no Render e o provedor de login Google no Supabase com os respectivos callbacks.
3. Publique a SPA e teste a recarga de `/configuracoes`, a abertura de evento e `/auth/retorno`. Use a URL HTTPS da API com o sufixo `/api/v1` e as credenciais públicas do mesmo Supabase. O upload vai diretamente ao Render.
4. Ative o [agendador de lembretes](../supabase/snippets/habilitar_lembretes.sql) no banco migrado. Valide a fila de planos, o coletor, a exportação e os fluxos de conta com dados sintéticos.
