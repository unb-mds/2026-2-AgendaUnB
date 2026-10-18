-- Complementa #41/#42: professores moderam; contas continuam exclusivas de admins.
create or replace function public.is_event_moderator()
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.profiles
    where id = auth.uid() and papel in ('professor', 'admin'));
$$;
revoke all on function public.is_event_moderator() from public, anon;
grant execute on function public.is_event_moderator() to authenticated;

create policy "moderadores leem sugestoes" on public.eventos for select
  to authenticated using ((select public.is_event_moderator()));

-- Alterações de status passam pela RPC atômica, sem UPDATE amplo no navegador.
drop policy if exists "admin modera eventos" on public.eventos;

create table public.notificacoes (
  id uuid primary key default gen_random_uuid(),
  usuario_id uuid not null references public.profiles(id) on delete cascade,
  evento_id uuid references public.eventos(id) on delete set null,
  tipo text not null check (tipo in ('submissao', 'aprovacao', 'recusa')),
  titulo_evento text not null,
  justificativa text,
  criado_em timestamptz not null default now(),
  lida_em timestamptz,
  unique (evento_id, tipo)
);
create index notificacoes_usuario_data on public.notificacoes(usuario_id, criado_em desc);
create index eventos_status_criado on public.eventos(status, criado_em, id);
alter table public.notificacoes enable row level security;
revoke all on public.notificacoes from anon, authenticated;
grant select on public.notificacoes to authenticated;
grant update (lida_em) on public.notificacoes to authenticated;
create policy "dono le notificacoes" on public.notificacoes for select to authenticated
  using (usuario_id = (select auth.uid()));
create policy "dono marca notificacoes" on public.notificacoes for update to authenticated
  using (usuario_id = (select auth.uid())) with check (usuario_id = (select auth.uid()));

-- Registro durável: mantém a autoria estudantil mesmo se o usuário mudar de papel.
alter table public.eventos add column sugestao_estudante boolean not null default false;
update public.eventos e set sugestao_estudante = true from public.profiles p
  where p.id = e.autor_id and p.papel = 'student';
create or replace function public.tg_evento_de_estudante_pendente()
returns trigger language plpgsql security definer set search_path = '' as $$
declare v_papel text;
begin
  select papel into v_papel from public.profiles where id = new.autor_id;
  new.sugestao_estudante := v_papel is distinct from 'professor' and v_papel is distinct from 'admin';
  if new.sugestao_estudante then
    new.status := 'pendente'; new.justificativa_recusa := null;
  end if;
  new.interessados_count := 0;
  return new;
end;
$$;

create or replace function public.tg_notifica_sugestao()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if new.sugestao_estudante then
    if TG_OP = 'INSERT' then
      insert into public.notificacoes(usuario_id, evento_id, tipo, titulo_evento)
        values (new.autor_id, new.id, 'submissao', new.titulo);
    elsif old.status is distinct from new.status and new.status in ('aprovado', 'rejeitado') then
      insert into public.notificacoes(usuario_id, evento_id, tipo, titulo_evento, justificativa)
        values (new.autor_id, new.id,
          case when new.status = 'aprovado' then 'aprovacao' else 'recusa' end,
          new.titulo, new.justificativa_recusa);
    end if;
  end if;
  return new;
end;
$$;
create trigger eventos_notifica_sugestao after insert or update of status on public.eventos
  for each row execute function public.tg_notifica_sugestao();
revoke all on function public.tg_notifica_sugestao() from public, anon, authenticated;

create or replace function public.moderar_sugestao(p_evento_id uuid, p_status text, p_justificativa text default null)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if not public.is_event_moderator() then
    raise exception 'Apenas professores e administradores' using errcode = '42501';
  end if;
  if p_status is null or p_status not in ('aprovado', 'rejeitado') then
    raise exception 'Decisão inválida' using errcode = '22023';
  end if;
  if p_status = 'rejeitado' and (nullif(btrim(p_justificativa), '') is null or char_length(btrim(p_justificativa)) > 2000) then
    raise exception 'Informe uma justificativa de até 2000 caracteres' using errcode = '22023';
  end if;
  update public.eventos set status = p_status,
    justificativa_recusa = case when p_status = 'rejeitado' then btrim(p_justificativa) else null end
    where id = p_evento_id and status = 'pendente' and sugestao_estudante;
  if not found then
    raise exception 'Esta sugestão já foi analisada ou não está disponível. Atualize a lista.' using errcode = 'P0002';
  end if;
end;
$$;
revoke all on function public.moderar_sugestao(uuid, text, text) from public, anon;
grant execute on function public.moderar_sugestao(uuid, text, text) to authenticated;

create or replace function public.listar_sugestoes(p_status text default 'pendente', p_busca text default '', p_offset integer default 0)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare resultado jsonb;
begin
  if not public.is_event_moderator() then
    raise exception 'Apenas professores e administradores' using errcode = '42501';
  end if;
  if p_status is null or p_status not in ('pendente', 'aprovado', 'rejeitado') or p_offset is null or p_offset < 0 then
    raise exception 'Filtro inválido' using errcode = '22023';
  end if;
  with filtrados as (
    select e.id, e.titulo, e.descricao, e.data_evento, e.localizacao, e.link_externo,
      e.status, e.justificativa_recusa, e.criado_em, p.nome_completo as autor_nome,
      c.nome as campus, cat.nome as categoria
    from public.eventos e join public.profiles p on p.id = e.autor_id
    left join public.campus c on c.id = e.campus_id
    left join public.categories cat on cat.id = e.category_id
    where e.sugestao_estudante and e.status = p_status
      and (coalesce(p_busca, '') = '' or strpos(lower(e.titulo || ' ' || p.nome_completo), lower(btrim(p_busca))) > 0)
  ), pagina as (select * from filtrados order by criado_em, id limit 20 offset p_offset)
  select jsonb_build_object('items', coalesce((select jsonb_agg(to_jsonb(pagina)) from pagina), '[]'::jsonb),
    'total', (select count(*) from filtrados),
    'pending', (select count(*) from public.eventos where sugestao_estudante and status = 'pendente')) into resultado;
  return resultado;
end;
$$;
revoke all on function public.listar_sugestoes(text, text, integer) from public, anon;
grant execute on function public.listar_sugestoes(text, text, integer) to authenticated;

create or replace function public.admin_buscar_usuarios(p_busca text default '', p_papel text default '', p_confirmado text default '', p_offset integer default 0)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare resultado jsonb;
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores' using errcode = '42501';
  end if;
  if p_offset is null or p_offset < 0 or p_papel not in ('', 'student', 'professor', 'admin') or p_confirmado not in ('', 'sim', 'nao') then
    raise exception 'Filtro inválido' using errcode = '22023';
  end if;
  with usuarios as (
    select u.id, u.email::text, p.nome_completo, p.papel, u.created_at as criado_em,
      u.last_sign_in_at as ultimo_login, u.email_confirmed_at is not null as email_confirmado
    from auth.users u join public.profiles p on p.id = u.id
  ), filtrados as (
    select * from usuarios where (p_papel = '' or papel = p_papel)
      and (p_confirmado = '' or email_confirmado = (p_confirmado = 'sim'))
      and (coalesce(p_busca, '') = '' or strpos(lower(nome_completo || ' ' || email), lower(btrim(p_busca))) > 0)
  ), pagina as (select * from filtrados order by criado_em desc, id limit 20 offset p_offset)
  select jsonb_build_object('items', coalesce((select jsonb_agg(to_jsonb(pagina)) from pagina), '[]'::jsonb),
    'total', (select count(*) from filtrados), 'all', (select count(*) from usuarios),
    'unconfirmed', (select count(*) from usuarios where not email_confirmado)) into resultado;
  return resultado;
end;
$$;
revoke all on function public.admin_buscar_usuarios(text, text, text, integer) from public, anon;
grant execute on function public.admin_buscar_usuarios(text, text, text, integer) to authenticated;

-- Detecta alterações concorrentes antes de chamar a RPC de #42.
create or replace function public.admin_definir_papel(p_usuario_id uuid, p_novo_papel text, p_papel_atual text)
returns void language plpgsql security definer set search_path = '' as $$
declare atual text;
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores' using errcode = '42501';
  end if;
  select papel into atual from public.profiles where id = p_usuario_id for update;
  if atual is distinct from p_papel_atual or atual is null then
    raise exception 'Este perfil mudou ou não está disponível. Atualize a lista.' using errcode = 'P0002';
  end if;
  perform public.admin_alterar_papel(p_usuario_id, p_novo_papel);
end;
$$;
revoke all on function public.admin_definir_papel(uuid, text, text) from public, anon;
grant execute on function public.admin_definir_papel(uuid, text, text) to authenticated;
