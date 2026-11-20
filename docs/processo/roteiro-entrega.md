---
title: "Roteiro de entrega e operação (24–25/11)"
description: "Checklist de implantação, backup, restauração, rollback, operação do Google Calendar e roteiro do ensaio de 24/11 e aceite de 25/11."
---

Este roteiro reúne os procedimentos operacionais da Release 2 para o ensaio de **24/11/2026** e a entrega de **25/11/2026**. A documentação canônica é publicada via Mintlify (`docs/docs.json` e proxy `/docs` na Vercel); o antigo `.github/mkdocs.yml` permanece apenas como legado sem publicação ativa.

## 1. Google Calendar API: configuração e regras de operação

- **Habilitação e escopos:** ativar a *Google Calendar API* no Google Cloud Console e solicitar apenas `openid`, `email` (conferência do e-mail verificado com a conta no Agenda UnB) e `https://www.googleapis.com/auth/calendar.app.created` (acesso restrito à agenda secundária **"Agenda UnB"**).
- **Callbacks:** cadastrar `https://<host-da-api>/api/v1/me/google-calendar/callback` no cliente OAuth Web e em `GOOGLE_CALENDAR_REDIRECT_URI`; apontar `GOOGLE_CALENDAR_FRONTEND_REDIRECT_URI` para a rota da SPA em `/eventos?aba=meus`.
- **Modo de teste vs. publicação:** enquanto o app OAuth estiver em *Testing*, apenas os e-mails cadastrados na lista de testadores conseguem autorizar o Calendar (limite de 100 usuários de teste). Para liberar ao público geral, concluir a verificação de domínio e tela de consentimento no Google Auth Platform.
- **Proteção e renovação de tokens:** os tokens ficam cifrados com Fernet (`GOOGLE_TOKEN_ENCRYPTION_KEY`) no servidor; o estado OAuth expira em 10 minutos. Quando o `access_token` expira, a API renova usando o `refresh_token` antes da chamada ao Google.
- **Desconexão e reexportação:** ao desconectar em **Meus Eventos** ou revogar em **Configurações**, os tokens são apagados no banco e a revogação é solicitada ao Google. A reexportação é idempotente por identificador técnico (até 20 eventos por lote, fuso `America/Sao_Paulo`, duração padrão de 1 hora).
- **Limites explícitos de sincronização:** não há sincronização bidirecional. Alterações ou exclusões feitas no Agenda UnB após a exportação não modificam nem apagam eventos já criados na agenda **"Agenda UnB"** do Google, e eventos editados no Google não retornam para o Agenda UnB.
- **Falhas recuperáveis:** em `429` (limite de taxa), timeout após criação, falha parcial no lote ou token expirado/revogado, a interface preserva os eventos na agenda local, informa quais itens falharam e permite tentar novamente ou usar a exportação `.ics`.

## 2. Checklist de implantação, backup, restauração e rollback

### Pré-implantação e migrations
1. Conferir histórico de migrations antes de aplicar em produção:
   ```bash
   npx supabase migration list
   npx supabase db push --dry-run --include-all
   ```
2. Revise a lista e aplique as migrações com `npx supabase db push --include-all` antes de publicar a API e a SPA. Confirme que a versão publicada continua compatível durante a janela.
3. Verificar variáveis sem segredos no código: `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_PUBLISHABLE_KEY` na Vercel; `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `GEMINI_API_KEY`, `GOOGLE_CALENDAR_*`, `GOOGLE_TOKEN_ENCRYPTION_KEY` e `CORS_ORIGINS` no Render/GitHub Environments.
4. Validar `/health`, resposta JSON de `/api/v1/events?limit=1` e headers CORS após o deploy.

### Backup e restauração (PostgreSQL / Supabase)
Como o plano Free do Supabase não oferece *Point-in-Time Recovery* automático acessível à equipe, executar backup lógico antes de migrations com mudança de schema:
```bash
# Backup lógico antes da janela de mudança
pg_dump "$DATABASE_URL" --format=custom --no-owner --no-acl -f "backup-agendaunb-$(date +%Y%m%d-%H%M).dump"

# Restauração em banco de contingência ou recuperação controlada
pg_restore --clean --if-exists --no-owner --no-acl -d "$DATABASE_URL" backup-agendaunb-YYYYMMDD-HHMM.dump
```

### Rollback
1. **Jobs (`production-jobs`):** desativar `PRODUCTION_EVENT_COLLECTION_ENABLED` e `PRODUCTION_SYLLABUS_WORKER_ENABLED` imediatamente se houver falha em lote.
2. **Aplicação (API e SPA):** no Render e na Vercel, selecionar o deploy anterior validado compatível com o schema vigente.
3. **Banco de dados (mudanças de schema):** preferir migration corretiva incremental. Se for indispensável reverter alteração destrutiva, restaurar o `pg_dump` pré-janela e confirmar integridade das tabelas `eventos`, `eventos_pessoais`, `planos_ensino` e `google_calendar_connections`.

## 3. Ensaio geral (24/11) e roteiro de aceite (25/11)

### Verificação do ambiente final (ensaio de 24/11)
- [ ] SHA implantado na Vercel e no Render confere com a tag/commit revisado.
- [ ] Todas as migrations aplicadas sem divergência em `supabase migration list`.
- [ ] `GET /health` e `GET /api/v1/events?limit=1` retornam `200` com TLS válido.
- [ ] Jobs `collector` (Agenda UnB Notícias) e `worker` (planos de ensino) executados com sucesso ao menos uma vez no ambiente final. Job `agenda-unb-lembretes` ativo e com execução registrada no Supabase Cron.
- [ ] Build de documentação Mintlify passando (`mint validate`, `mint broken-links --check-redirects`, `mint a11y`).

### Roteiro de demonstração e aceite (25/11)
1. **Catálogo público e filtros:** abrir `/eventos`, filtrar por campus/categoria/busca e alternar entre Lista e Calendário.
2. **Autenticação e termos:** entrar com conta de teste (e-mail/senha e Google), verificar exibição e aceite de Termos/Política.
3. **Turma, plano de ensino e extração:** selecionar oferta em `/plano-de-ensino`, enviar PDF sintético, conferir a sanitização automática e o andamento, revisar os candidatos extraídos e importar para **Meus Eventos**.
4. **Exportação direta ao Google Calendar:** conectar Google Calendar em **Meus Eventos**, selecionar eventos da agenda pessoal, exportar para **"Agenda UnB"** e conferir o aviso sobre cópias independentes e recuperação em caso de falha/revogação.
5. **Privacidade e ciclo de vida:** acessar `/configuracoes`, baixar os dados em JSON (`Baixar meus dados`) e demonstrar desconexão do Google Calendar / fluxo de exclusão de conta.
6. **Operação e documentação:** mostrar `/docs`, matriz de rastreabilidade (`RF01`–`RF21`, `RNF01`–`RNF13`) e checklist de rollback.

### Registro de correções impeditivas (ensaio 24/11)

| Data/Hora | Sintoma observado | Responsável | Ação / Commit de correção | Revalidação |
| --- | --- | --- | --- | --- |
| _24/11 (espaço reservado)_ | _Preencher se houver bloqueio no ensaio_ | _—_ | _—_ | _—_ |
