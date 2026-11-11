-- S7-F04: confirmation gate, role assignment and server-side Google OAuth.

-- Role metadata is only a request. A professor role is granted at creation
-- only if Supabase already confirms the actual account email and it belongs
-- to @unb.br. Otherwise, the account starts as a student.
create or replace function public.tg_cria_perfil()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.profiles (id, nome_completo, email, papel)
  values (
    new.id,
    coalesce(
      nullif(trim(new.raw_user_meta_data ->> 'nome_completo'), ''),
      nullif(trim(new.raw_user_meta_data ->> 'full_name'), ''),
      nullif(trim(new.raw_user_meta_data ->> 'name'), ''),
      split_part(new.email, '@', 1)
    ),
    new.email,
    case
      when new.email_confirmed_at is not null
       and new.email ~* '@unb\.br$'
       and new.raw_user_meta_data ->> 'papel' = 'professor'
      then 'professor'
      else 'student'
    end
  );
  return new;
end;
$$;

-- Authenticated users can self-promote to professor only if the actual
-- Supabase account email is verified and institutional. The admin RPC runs
-- as its trusted owner and can change roles of other confirmed accounts.
create or replace function public.current_account_is_confirmed_unb()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from auth.users
     where id = (select auth.uid())
       and email_confirmed_at is not null
       and email ~* '@unb\.br$'
  );
$$;
revoke all on function public.current_account_is_confirmed_unb() from public, anon;
grant execute on function public.current_account_is_confirmed_unb() to authenticated;

create or replace function public.tg_promove_professor_confirmado()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if old.email_confirmed_at is null
     and new.email_confirmed_at is not null
     and new.email ~* '@unb\.br$'
     and new.raw_user_meta_data ->> 'papel' = 'professor' then
    update public.profiles
       set papel = 'professor'
     where id = new.id and papel = 'student';
  end if;
  return new;
end;
$$;
create trigger on_auth_user_confirmed_professor_request
  after update of email_confirmed_at on auth.users
  for each row execute function public.tg_promove_professor_confirmado();

-- Changes to another account still go through the admin RPC.
create or replace function public.tg_protege_papel()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.papel is distinct from old.papel
     and current_user in ('anon', 'authenticated')
     and not (old.papel = 'student' and new.papel = 'professor'
              and (select auth.uid()) = new.id
              and public.current_account_is_confirmed_unb()) then
    raise exception 'Alteração de papel não permitida'
      using errcode = '42501';
  end if;
  return new;
end;
$$;

create or replace function public.admin_alterar_papel(
  p_usuario_id uuid,
  p_novo_papel text
)
returns public.profiles
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_perfil public.profiles;
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores' using errcode = '42501';
  end if;
  if p_novo_papel is null or p_novo_papel not in ('student', 'professor', 'admin') then
    raise exception 'Papel inválido' using errcode = '22023';
  end if;
  if p_usuario_id = (select auth.uid()) and p_novo_papel <> 'admin' then
    raise exception 'Um admin não pode remover o próprio papel de admin' using errcode = '42501';
  end if;
  if not exists (
    select 1 from auth.users
     where id = p_usuario_id and email_confirmed_at is not null
  ) then
    raise exception 'A conta precisa confirmar o e-mail antes de receber um papel' using errcode = '42501';
  end if;

  update public.profiles
     set papel = p_novo_papel
   where id = p_usuario_id
  returning * into v_perfil;
  if not found then
    raise exception 'Usuário não encontrado' using errcode = 'P0002';
  end if;
  return v_perfil;
end;
$$;
revoke all on function public.admin_alterar_papel(uuid, text) from public, anon;
grant execute on function public.admin_alterar_papel(uuid, text) to authenticated;

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

create table public.google_calendar_connections (
  user_id uuid primary key references public.profiles(id) on delete cascade,
  google_sub varchar(255) not null unique,
  google_email text not null,
  calendar_id text,
  encrypted_access_token text not null,
  encrypted_refresh_token text not null,
  access_token_expires_at timestamptz not null,
  granted_scope text not null,
  criado_em timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);

create trigger google_calendar_connections_atualizado_em
  before update on public.google_calendar_connections
  for each row execute function public.tg_atualiza_timestamp();

alter table public.google_calendar_oauth_states enable row level security;
alter table public.google_calendar_connections enable row level security;
revoke all on table public.google_calendar_oauth_states from public, anon, authenticated;
revoke all on table public.google_calendar_connections from public, anon, authenticated;

comment on table public.google_calendar_oauth_states is
  'State e verifier temporários de OAuth Calendar; leitura/escrita somente pelo backend.';
comment on table public.google_calendar_connections is
  'Vínculo Calendar e tokens criptografados no backend; nunca expostos ao cliente.';
