-- Contracts for syllabus review/confirmation (S6-B02).
-- Additive changes: existing plans and personal events remain readable.

alter table public.avaliacoes
  alter column data_avaliacao drop not null,
  add column if not exists tipo text,
  add column if not exists ambiguo boolean not null default false,
  add column if not exists pagina_origem integer,
  add column if not exists trecho_origem text,
  add column if not exists status text not null default 'pendente',
  add column if not exists versao_processamento text,
  add column if not exists provedor text;

create index if not exists idx_avaliacoes_plano_status
  on public.avaliacoes (plano_id, status);

alter table public.eventos_pessoais
  add column if not exists origem_plano_id uuid,
  add column if not exists origem_avaliacao_id uuid,
  add column if not exists origem_pagina integer,
  add column if not exists origem_trecho text;

-- A candidate can create at most one personal event, including concurrent retries.
create unique index if not exists uq_eventos_pessoais_origem_avaliacao
  on public.eventos_pessoais (origem_avaliacao_id)
  where origem_avaliacao_id is not null;

-- Assessments are private to the owner of their parent syllabus.
drop policy if exists "avaliacoes sao publicas" on public.avaliacoes;
drop policy if exists "dono do plano consulta candidatos" on public.avaliacoes;
create policy "dono do plano consulta candidatos"
  on public.avaliacoes for select to authenticated
  using (
    exists (
      select 1 from public.planos_ensino plano
      where plano.id = avaliacoes.plano_id
        and plano.user_id = (select auth.uid())
    )
  );

comment on column public.avaliacoes.pagina_origem is
  'Página do PDF que fundamenta o candidato, quando conhecida.';
comment on column public.avaliacoes.trecho_origem is
  'Trecho do plano que fundamenta o candidato, quando conhecido.';
comment on column public.eventos_pessoais.origem_avaliacao_id is
  'Candidato que originou o evento pessoal; unicidade garante confirmação idempotente.';
