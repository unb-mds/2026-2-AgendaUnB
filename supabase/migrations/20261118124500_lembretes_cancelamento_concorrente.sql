-- Serialize public event rescheduling with deletion of its saved links (#81).
create or replace function public.tg_lembrete_evento_publico()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid;
begin
  if new.status is not distinct from old.status and new.data_evento is not distinct from old.data_evento then
    return new;
  end if;

  if new.status <> 'aprovado' or new.data_evento is null then
    delete from public.lembretes where evento_id = new.id and status = 'pendente';
  elsif new.data_evento is distinct from old.data_evento or old.status <> 'aprovado' then
    -- Lock each link before scheduling so a concurrent removal either skips
    -- this iteration or cancels the newly scheduled reminder after commit.
    for v_user_id in
      select s.user_id
        from public.eventos_salvos s
       where s.event_id = new.id
       for key share of s
    loop
      perform public.agendar_lembrete(v_user_id, null, new.id, new.data_evento);
    end loop;
  end if;

  return new;
end;
$$;
