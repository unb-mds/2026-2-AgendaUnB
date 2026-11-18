-- Serialize a new saved event with changes to its public start or status (#81).
create or replace function public.tg_lembrete_evento_salvo()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_inicio timestamptz;
  v_status text;
begin
  if tg_op = 'DELETE' then
    delete from public.lembretes
     where user_id = old.user_id and evento_id = old.event_id and status = 'pendente';
    return old;
  end if;

  -- The FK lock alone allows concurrent updates to non-key columns.
  -- Hold a shared lock until the new link is visible to the event's trigger.
  select data_evento, status into v_inicio, v_status
    from public.eventos
   where id = new.event_id
   for share;
  if v_status = 'aprovado' then
    perform public.agendar_lembrete(new.user_id, null, new.event_id, v_inicio);
  end if;
  return new;
end;
$$;
