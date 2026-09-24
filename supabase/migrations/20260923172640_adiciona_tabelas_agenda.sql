-- Corrige a política anterior para permitir que visitantes vejam os perfis
drop policy if exists "perfis visiveis para usuarios logados" on public.profiles;

create policy "perfis visiveis para todos"
  on public.profiles for select
  using (true);

-- =============================================================
-- TABELA DE EVENTOS (Agenda Pública)
-- =============================================================
create table public.eventos (
  id             uuid primary key default gen_random_uuid(),
  autor_id       uuid not null references public.profiles(id) on delete cascade,
  titulo         text not null check (char_length(trim(titulo)) >= 3),
  descricao      text not null,
  data_evento    timestamptz not null, -- Cobre data e hora do RF14
  localizacao    text,
  link_externo   text, -- Campo adicionado para o RF14
  campus_id      uuid references public.campus(id),     -- Ligação com a tabela de Campus
  category_id    uuid references public.categories(id), -- Ligação com a tabela de Categorias
  status         text not null default 'pendente' 
                 check (status in ('pendente', 'aprovado', 'rejeitado')),
  criado_em      timestamptz not null default now()
);

comment on table public.eventos is 'Eventos propostos por professores ou verificados pela IA, associados a campus e categoria.';

-- =============================================================
-- TABELA DE PLANOS DE ENSINO
-- =============================================================
create table public.planos_ensino (
  id             uuid primary key default gen_random_uuid(),
  professor_id   uuid not null references public.profiles(id) on delete cascade,
  disciplina     text not null,
  turma          text not null,
  arquivo_url    text,
  criado_em      timestamptz not null default now()
);

comment on table public.planos_ensino is 'Planos de ensino enviados para extração de datas.';

-- =============================================================
-- TABELA DE AVALIAÇÕES (Organizador)
-- =============================================================
create table public.avaliacoes (
  id             uuid primary key default gen_random_uuid(),
  plano_id       uuid not null references public.planos_ensino(id) on delete cascade,
  titulo         text not null,
  data_avaliacao timestamptz not null,
  criado_em      timestamptz not null default now()
);

comment on table public.avaliacoes is 'Datas de provas extraídas automaticamente dos planos de ensino.';

-- =============================================================
-- POLÍTICAS DE SEGURANÇA (RLS) - Eventos e Avaliações
-- =============================================================
alter table public.eventos enable row level security;
alter table public.planos_ensino enable row level security;
alter table public.avaliacoes enable row level security;

create policy "eventos aprovados sao publicos"
  on public.eventos for select
  using (status = 'aprovado');

create policy "usuarios logados podem criar eventos"
  on public.eventos for insert
  to authenticated
  with check (autor_id = (select auth.uid()));

create policy "avaliacoes sao publicas"
  on public.avaliacoes for select
  using (true);