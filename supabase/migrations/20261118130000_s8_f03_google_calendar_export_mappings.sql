-- =============================================================
-- S8-F03 (#82) — Exportação direta para agenda secundária "Agenda UnB"
--
--   ADR-011       datas civis, instantes, fim exclusivo e fuso America/Sao_Paulo
--   ADR-012       exportação idempotente, mapeamento por evento/destino e
--                 confirmação explícita de sobrescrita na reexportação
--
-- Requisitos: RF21 e RNF02.
-- =============================================================

-- Garante a coluna de localização em eventos pessoais (compatível com S8-F02).
alter table public.eventos_pessoais
  add column if not exists localizacao text
  check (localizacao is null or char_length(btrim(localizacao)) <= 250);

-- Mapeamento persistido por usuário, evento local e agenda de destino.
-- Exclusões locais não apagam cópias remotas no Google Agenda; a exclusão da
-- conta remove os registros em cascata por user_id.
create table if not exists public.google_calendar_event_exports (
  user_id uuid not null references public.profiles(id) on delete cascade,
  event_kind text not null check (event_kind in ('personal', 'saved')),
  local_event_id uuid not null,
  calendar_id text not null,
  google_event_id text not null check (google_event_id ~ '^[a-v0-9]{5,1024}$'),
  exported_version text not null check (exported_version ~ '^[0-9a-f]{64}$'),
  status text not null default 'exported'
         check (status in ('pending', 'exported', 'updated', 'already_exported', 'failed')),
  last_idempotency_key text check (last_idempotency_key is null or char_length(last_idempotency_key) <= 128),
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now(),
  primary key (user_id, event_kind, local_event_id)
);

create index if not exists google_calendar_event_exports_user_calendar_idx
  on public.google_calendar_event_exports (user_id, calendar_id);

drop trigger if exists google_calendar_event_exports_atualizado_em
  on public.google_calendar_event_exports;

create trigger google_calendar_event_exports_atualizado_em
  before update on public.google_calendar_event_exports
  for each row execute function public.tg_atualiza_timestamp();

alter table public.google_calendar_event_exports enable row level security;
revoke all on table public.google_calendar_event_exports from public, anon, authenticated;

comment on table public.google_calendar_event_exports is
  'Mapeamento de eventos exportados para a agenda secundária Agenda UnB; acesso somente pelo backend.';
