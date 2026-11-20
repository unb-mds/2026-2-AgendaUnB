-- Preserva chaves de deduplicação dos dois fluxos antigos sem alterar o contador.
begin;

lock table public.eventos_cliques_redirecionamento in access exclusive mode;

insert into public.cliques_evento (evento_id, click_id, criado_em)
select event_id, click_id, criado_em from public.eventos_cliques_redirecionamento
on conflict (evento_id, click_id) do nothing;

create or replace function public.registrar_redirecionamento_evento(
  p_evento_id uuid,
  p_click_id uuid
)
returns jsonb
language plpgsql
set search_path = ''
as $$
declare
  v_link text;
  v_count integer;
  v_novo boolean;
begin
  if p_evento_id is null or p_click_id is null then
    raise exception 'Informe o evento e o identificador do acionamento'
      using errcode = '22023';
  end if;

  select e.link_externo, e.interessados_count
    into v_link, v_count
    from public.eventos e
   where e.id = p_evento_id
     and e.status = 'aprovado'
     for update;

  if not found then
    raise exception 'Evento não encontrado' using errcode = 'P0002';
  end if;

  if v_link is null or v_link !~* '^https?://[^[:space:]<>"]+$' then
    raise exception 'Este evento não possui link oficial disponível'
      using errcode = '22023';
  end if;

  insert into public.cliques_evento (evento_id, click_id)
  values (p_evento_id, p_click_id)
  on conflict (evento_id, click_id) do nothing;
  v_novo := found;

  if v_novo then
    update public.eventos
       set interessados_count = coalesce(interessados_count, 0) + 1
     where id = p_evento_id
    returning interessados_count into v_count;
  end if;

  return jsonb_build_object(
    'external_url', v_link,
    'outbound_clicks_count', coalesce(v_count, 0),
    'incremented', v_novo
  );
end;
$$;

revoke execute on function public.registrar_redirecionamento_evento(uuid, uuid)
  from public, anon, authenticated;
grant execute on function public.registrar_redirecionamento_evento(uuid, uuid) to service_role;
grant select, insert on public.cliques_evento to service_role;
grant select (id, status, link_externo, interessados_count), update (interessados_count)
  on public.eventos to service_role;

drop function public.registrar_clique_evento(uuid, uuid);
drop table public.eventos_cliques_redirecionamento;

-- A única fila consumida pelo worker usa o estado e o lease de planos_ensino.
drop table public.fila_processamento_ia;

commit;
