# Supabase Cloud, Render e Vercel

Use o [guia de implantação](/implantacao) para validar migrações, configurar variáveis de ambiente, publicar, realizar backup/restauração e executar o checklist de aceite e rollback.

| Serviço | Configuração |
| --- | --- |
| Supabase Cloud | PostgreSQL, Auth, Storage privado e Cron (`pg_cron`). Use Session Pooler com TLS e configure SMTP e retornos de login no painel Auth. |
| Render | FastAPI. [Blueprint](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/render.yaml) com raiz `backend`, Docker (`backend/Dockerfile`, Python 3.11), `$PORT` e `/health`. As variáveis estão em [render.env.example](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/docs/deploy/render.env.example). |
| Vercel | Root Directory `frontend`, Vite, `npm ci`, `npm run build`, saída `dist`. [Configuração de rotas e busca](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/frontend/vercel.json) e [variáveis públicas](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/docs/deploy/vercel.env.example). |
| GitHub Actions | [Jobs de produção](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/.github/workflows/production-jobs.yml) em `main`: `worker --drain --max-items 25` processa planos, `collector` coleta a Agenda UnB Notícias e `catalog` sincroniza ofertas sob demanda. |

1. Confira o projeto Supabase, realize backup lógico (`pg_dump`) quando houver mudança de schema e aplique as migrações pendentes (`supabase db push`) antes de publicar a API dependente.
2. Confirme o health check, o preflight CORS e uma consulta real ao PostgreSQL via API no Render. Configure o OAuth do Google Agenda no Render e o provedor de login Google no Supabase com os respectivos callbacks.
3. Publique a SPA na Vercel e teste recarga em `/configuracoes`, `/plano-de-ensino`, `/eventos`, `/evento/<id>` e `/auth/retorno`. Use a URL HTTPS da API com o sufixo `/api/v1` e as credenciais públicas do mesmo projeto Supabase.
4. Ative o [agendador de lembretes](https://github.com/unb-mds/2026-2-AgendaUnB/blob/main/supabase/snippets/habilitar_lembretes.sql) no banco migrado e valide a fila de planos, o coletor, a exportação Google Agenda e os fluxos de privacidade com dados sintéticos.
