create table public.eventos_pessoais (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references auth.users(id) default auth.uid(),
  titulo         text not null check (char_length(trim(titulo)) >= 3),
  descricao      text,
  data_hora      timestamptz not null,
  campus_id      uuid references public.campus(id),
  category_id    uuid references public.categories(id),
  criado_em      timestamptz not null default now()
);

comment on table public.eventos_pessoais is 'Eventos privados criados por cada utilizador, associados a campus e categoria.';

alter table public.eventos_pessoais enable row level security;

create policy "utilizadores podem ver os seus proprios eventos"
  on public.eventos_pessoais for select
  using (auth.uid() = user_id);

create policy "utilizadores podem criar eventos"
  on public.eventos_pessoais for insert
  with check (auth.uid() = user_id);

create policy "utilizadores podem atualizar os seus proprios eventos"
  on public.eventos_pessoais for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

create policy "utilizadores podem deletar os seus proprios eventos"
  on public.eventos_pessoais for delete
  using (auth.uid() = user_id);