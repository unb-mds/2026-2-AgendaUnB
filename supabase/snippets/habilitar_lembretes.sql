-- Executar como postgres no ambiente validado, após as migrações da #81.
-- O mesmo nome atualiza a configuração do job em reexecuções.
begin;

select 'public.disparar_lembretes(integer)'::regprocedure;

do $install$
begin
  if not exists (select 1 from pg_extension where extname = 'pg_cron') then
    create extension pg_cron with schema pg_catalog;
  end if;
end;
$install$;

select cron.schedule(
  'agenda-unb-lembretes',
  '*/5 * * * *',
  $job$select public.disparar_lembretes()$job$
);

commit;
