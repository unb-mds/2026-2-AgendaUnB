-- Vínculos pessoais com eventos públicos; os dados do evento não são copiados.
create table public.eventos_salvos (
  user_id uuid not null references public.profiles(id) on delete cascade,
  event_id uuid not null references public.eventos(id) on delete cascade,
  criado_em timestamptz not null default now(),
  primary key (user_id, event_id)
);

create index eventos_salvos_event_id_idx on public.eventos_salvos(event_id);

alter table public.eventos_salvos enable row level security;

create policy "usuario consulta seus eventos salvos"
  on public.eventos_salvos for select to authenticated
  using (user_id = (select auth.uid()));

create policy "usuario salva eventos aprovados para si"
  on public.eventos_salvos for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and exists (
      select 1 from public.eventos
      where eventos.id = event_id and eventos.status = 'aprovado'
    )
  );

create policy "usuario remove seus eventos salvos"
  on public.eventos_salvos for delete to authenticated
  using (user_id = (select auth.uid()));

grant select, insert, delete on public.eventos_salvos to authenticated;
grant all on public.eventos_salvos to service_role;
