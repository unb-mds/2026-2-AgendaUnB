-- =============================================================
-- S8-D01 (#83) — Privacidade, termos, consentimentos e ciclo de vida
-- Requisitos: RF07, RNF02, RNF04 (ADR-003)
-- =============================================================

-- -------------------------------------------------------------
-- 1. Corrigir FKs e trigger de preservação para exclusão de conta
-- -------------------------------------------------------------
alter table public.eventos_pessoais
  drop constraint if exists eventos_pessoais_user_id_fkey;

alter table public.eventos_pessoais
  add constraint eventos_pessoais_user_id_fkey
    foreign key (user_id) references auth.users(id) on delete cascade;

alter table public.planos_ensino
  drop constraint if exists planos_ensino_versao_aprovada_id_fkey;

alter table public.planos_ensino
  add constraint planos_ensino_versao_aprovada_id_fkey
    foreign key (versao_aprovada_id) references public.versoes_plano(id) on delete set null;

create or replace function public.tg_preserva_texto_autorizado()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if not exists (select 1 from public.profiles where id = old.user_id) then
    return new;
  end if;
  if old.status = 'processando' and
     (new.texto_aprovado, new.hash_texto_aprovado, new.autorizado_em, new.versao_texto, new.versao_aprovada_id)
       is distinct from
     (old.texto_aprovado, old.hash_texto_aprovado, old.autorizado_em, old.versao_texto, old.versao_aprovada_id) then
    raise exception 'O snapshot em processamento não pode ser alterado' using errcode = '42501';
  end if;
  return new;
end;
$$;

revoke all on function public.tg_preserva_texto_autorizado() from public, anon, authenticated;

-- -------------------------------------------------------------
-- 2. Descarte registrado de PDFs legados em planos_ensino (ADR-003)
-- -------------------------------------------------------------
alter table public.planos_ensino
  add column arquivo_descartado_em timestamptz;

alter table public.planos_ensino
  drop constraint if exists planos_particular_exige_fonte,
  add constraint planos_particular_exige_fonte check (
    tipo <> 'particular'
    or caminho_arquivo is not null
    or texto_preparado is not null
    or arquivo_descartado_em is not null
  ),
  add constraint planos_descarte_remove_caminho check (
    arquivo_descartado_em is null
    or (caminho_arquivo is null and arquivo_url is null)
  );

comment on column public.planos_ensino.arquivo_descartado_em is
  'Data/hora em que o PDF original legado no Storage foi descartado após extração.';

-- -------------------------------------------------------------
-- 3. Aceites de termos/política, consentimentos e registro anônimo de exclusões
-- -------------------------------------------------------------
create table public.aceites_termos (
  user_id    uuid not null references public.profiles(id) on delete cascade,
  documento  text not null check (documento in ('terms', 'privacy')),
  versao     text not null check (char_length(btrim(versao)) between 1 and 40),
  aceito_em  timestamptz not null default now(),
  primary key (user_id, documento, versao)
);

create index idx_aceites_termos_user_doc
  on public.aceites_termos (user_id, documento, aceito_em desc);

create table public.consentimentos (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references public.profiles(id) on delete cascade,
  finalidade     text not null check (finalidade in ('google_agenda')),
  referencia_id  uuid,
  conteudo_hash  text check (conteudo_hash is null or conteudo_hash ~ '^[a-f0-9]{64}$'),
  concedido_em   timestamptz not null default now(),
  revogado_em    timestamptz,
  check (revogado_em is null or revogado_em >= concedido_em)
);

create index idx_consentimentos_user_finalidade
  on public.consentimentos (user_id, finalidade, concedido_em desc);

create unique index uq_consentimentos_ativo_por_finalidade
  on public.consentimentos (user_id, finalidade)
  where revogado_em is null;

create table public.exclusoes_conta (
  id                           uuid primary key default gen_random_uuid(),
  status                       text not null default 'iniciada'
                               check (status in ('iniciada', 'concluida')),
  iniciada_em                  timestamptz not null default now(),
  concluida_em                 timestamptz,
  planos_removidos             integer not null default 0 check (planos_removidos >= 0),
  eventos_pessoais_removidos   integer not null default 0 check (eventos_pessoais_removidos >= 0),
  eventos_publicos_removidos   integer not null default 0 check (eventos_publicos_removidos >= 0),
  arquivos_storage_removidos   integer not null default 0 check (arquivos_storage_removidos >= 0),
  check (concluida_em is null or (status = 'concluida' and concluida_em >= iniciada_em))
);

comment on table public.aceites_termos is
  'Registro de leitura/ciência por versão de Termos de Uso e Política de Privacidade.';
comment on table public.consentimentos is
  'Consentimentos específicos e revogáveis (separados do aceite de termos).';
comment on table public.exclusoes_conta is
  'Registro anônimo apenas com contagens agregadas de exclusões de conta (sem PII/user_id).';

-- -------------------------------------------------------------
-- 4. RLS e privilégios
-- -------------------------------------------------------------
alter table public.aceites_termos enable row level security;
alter table public.consentimentos enable row level security;
alter table public.exclusoes_conta enable row level security;

revoke all on table public.aceites_termos from public, anon, authenticated;
revoke all on table public.consentimentos from public, anon, authenticated;
revoke all on table public.exclusoes_conta from public, anon, authenticated;

grant select on table public.aceites_termos to authenticated;
grant select on table public.consentimentos to authenticated;
grant all on table public.aceites_termos to service_role;
grant all on table public.consentimentos to service_role;
grant all on table public.exclusoes_conta to service_role;

create policy confirmed_account
  on public.aceites_termos as restrictive
  for all to authenticated
  using ((select public.current_account_has_confirmed_email()))
  with check ((select public.current_account_has_confirmed_email()));

create policy "conta le os proprios aceites"
  on public.aceites_termos for select
  to authenticated
  using (user_id = (select auth.uid()));

create policy confirmed_account
  on public.consentimentos as restrictive
  for all to authenticated
  using ((select public.current_account_has_confirmed_email()))
  with check ((select public.current_account_has_confirmed_email()));

create policy "conta le os proprios consentimentos"
  on public.consentimentos for select
  to authenticated
  using (user_id = (select auth.uid()));

-- -------------------------------------------------------------
-- 5. Funções auxiliares server-only (não chamáveis pelo navegador)
-- -------------------------------------------------------------
create or replace function public.revogar_consentimento(
  p_user_id uuid,
  p_finalidade text
)
returns integer
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_count integer;
begin
  if p_finalidade is null or p_finalidade not in ('google_agenda') then
    raise exception 'Finalidade de consentimento inválida' using errcode = '22023';
  end if;
  update public.consentimentos
     set revogado_em = now()
   where user_id = p_user_id
     and finalidade = p_finalidade
     and revogado_em is null;
  get diagnostics v_count = row_count;
  return v_count;
end;
$$;

create or replace function public.preparar_exclusao_conta(p_user_id uuid)
returns table (
  exclusao_id uuid,
  caminhos_arquivos text[]
)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_papel text;
  v_outros_admins integer;
  v_planos integer;
  v_pessoais integer;
  v_publicos integer;
  v_caminhos text[];
  v_exclusao_id uuid;
begin
  -- Serializa verificações de último administrador.
  perform id from public.profiles where papel = 'admin' for update;

  select papel into v_papel
    from public.profiles
   where id = p_user_id
   for update;

  if not found then
    raise exception 'Conta não encontrada' using errcode = 'P0002';
  end if;

  if v_papel = 'admin' then
    select count(*) into v_outros_admins
      from public.profiles
     where papel = 'admin' and id <> p_user_id;
    if v_outros_admins = 0 then
      raise exception 'O último administrador não pode excluir a própria conta'
        using errcode = '55000';
    end if;
  end if;

  select count(*) into v_planos
    from public.planos_ensino where user_id = p_user_id or professor_id = p_user_id;
  select count(*) into v_pessoais
    from public.eventos_pessoais where user_id = p_user_id;
  select count(*) into v_publicos
    from public.eventos where autor_id = p_user_id;

  select coalesce(array_agg(legacy.path order by legacy.criado_em), '{}'::text[])
    into v_caminhos
    from (
      select criado_em, coalesce(caminho_arquivo, arquivo_url) as path
        from public.planos_ensino
       where (user_id = p_user_id or professor_id = p_user_id)
         and (caminho_arquivo is not null or arquivo_url is not null)
    ) as legacy;

  insert into public.exclusoes_conta (
    status, planos_removidos, eventos_pessoais_removidos, eventos_publicos_removidos
  ) values (
    'iniciada', v_planos, v_pessoais, v_publicos
  ) returning id into v_exclusao_id;

  exclusao_id := v_exclusao_id;
  caminhos_arquivos := v_caminhos;
  return next;
end;
$$;

create or replace function public.concluir_exclusao_conta(
  p_exclusao_id uuid,
  p_arquivos_removidos integer default 0
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  update public.exclusoes_conta
     set status = 'concluida',
         concluida_em = now(),
         arquivos_storage_removidos = greatest(0, coalesce(p_arquivos_removidos, 0))
   where id = p_exclusao_id;
end;
$$;

create or replace function public.arquivos_a_descartar()
returns table (
  plano_id uuid,
  user_id uuid,
  caminho_arquivo text
)
language sql
stable
security definer
set search_path = ''
as $$
  select id, user_id, coalesce(caminho_arquivo, arquivo_url)
    from public.planos_ensino
   where (caminho_arquivo is not null or arquivo_url is not null)
     and status in ('concluido', 'falha')
   order by criado_em asc, id asc;
$$;

create or replace function public.registrar_descarte_arquivo(p_plano_id uuid)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_updated integer;
begin
  update public.planos_ensino
     set caminho_arquivo = null,
         arquivo_url = null,
         arquivo_descartado_em = now()
   where id = p_plano_id
     and status in ('concluido', 'falha')
     and (caminho_arquivo is not null or arquivo_url is not null);
  get diagnostics v_updated = row_count;
  return v_updated > 0;
end;
$$;

revoke all on function
  public.revogar_consentimento(uuid, text),
  public.preparar_exclusao_conta(uuid),
  public.concluir_exclusao_conta(uuid, integer),
  public.arquivos_a_descartar(),
  public.registrar_descarte_arquivo(uuid)
  from public, anon, authenticated;

grant execute on function
  public.revogar_consentimento(uuid, text),
  public.preparar_exclusao_conta(uuid),
  public.concluir_exclusao_conta(uuid, integer),
  public.arquivos_a_descartar(),
  public.registrar_descarte_arquivo(uuid)
  to service_role;
