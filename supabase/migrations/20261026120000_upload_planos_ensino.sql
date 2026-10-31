-- =============================================================
-- Issue #40 — Rastreamento e Upload de Planos de Ensino
--
-- Adapta a tabela planos_ensino para suportar uploads de planos
-- particulares por qualquer usuário autenticado (estudante,
-- professor ou administrador) e rastrear o status do processamento.
-- =============================================================

alter table public.planos_ensino
  add column if not exists user_id uuid references public.profiles(id) on delete cascade,
  add column if not exists nome_arquivo text,
  add column if not exists caminho_arquivo text,
  add column if not exists tamanho_bytes bigint,
  add column if not exists tipo_arquivo text not null default 'pdf',
  add column if not exists status text not null default 'processing'
    check (status in ('processing', 'pendente', 'processando', 'concluido', 'falha', 'failed', 'completed')),
  add column if not exists quantidade_eventos int not null default 0,
  add column if not exists erro text;

-- Torna os campos professor_id, disciplina e turma opcionais para planos particulares
alter table public.planos_ensino alter column professor_id drop not null;
alter table public.planos_ensino alter column disciplina drop not null;
alter table public.planos_ensino alter column turma drop not null;

-- Índices para buscas rápidas por usuário e status de processamento
create index if not exists idx_planos_ensino_user_id on public.planos_ensino(user_id);
create index if not exists idx_planos_ensino_status on public.planos_ensino(status);

-- RLS: Usuário visualiza e insere apenas os próprios planos de ensino particulares
drop policy if exists "planos particulares: usuario le apenas os proprios planos" on public.planos_ensino;
create policy "planos particulares: usuario le apenas os proprios planos"
  on public.planos_ensino for select
  to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists "planos particulares: usuario cria os proprios planos" on public.planos_ensino;
create policy "planos particulares: usuario cria os proprios planos"
  on public.planos_ensino for insert
  to authenticated
  with check (user_id = (select auth.uid()));

