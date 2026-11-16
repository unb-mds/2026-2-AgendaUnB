create table public.google_calendar_oauth_states (
  state_hash text primary key check (state_hash ~ '^[0-9a-f]{64}$'),
  user_id uuid not null references public.profiles(id) on delete cascade,
  agenda_email text not null,
  encrypted_code_verifier text not null,
  expires_at timestamptz not null,
  criado_em timestamptz not null default now()
);
create index google_calendar_oauth_states_expiry_idx
  on public.google_calendar_oauth_states (expires_at);
create index google_calendar_oauth_states_user_idx
  on public.google_calendar_oauth_states (user_id);

alter table public.google_calendar_oauth_states enable row level security;
revoke all on table public.google_calendar_oauth_states from public, anon, authenticated;

alter table public.google_calendar_connections
  alter column encrypted_access_token drop not null,
  alter column encrypted_refresh_token drop not null,
  alter column access_token_expires_at drop not null;

-- Preserve destinations while retiring credentials from the login OAuth client.
update public.google_calendar_connections
   set encrypted_access_token = null,
       encrypted_refresh_token = null,
       access_token_expires_at = null,
       granted_scope = '';
