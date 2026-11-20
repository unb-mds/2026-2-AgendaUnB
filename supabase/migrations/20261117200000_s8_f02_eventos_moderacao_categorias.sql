-- =============================================================
-- S8-F02 (#80) — Fechar eventos, moderação, agenda e melhorias de uso
--
-- 1. Preserva localizacao (location) também em eventos_pessoais (RF09/RF14).
-- 2. Redirecionamento independente (Conferir evento) com deduplicação
--    atômica por (event_id, click_id) e desativação do caminho legado
--    sem validação (RF12).
-- 3. Gestão de categorias exclusiva de administradores via RLS e RPCs
--    protegidas (RF04, RF11, RNF04).
-- 4. Projeta datas civis, intervalos, procedência e contador de cliques
--    nas RPCs de listagem pública e moderação (RF08, RF14, RF16).
-- =============================================================

-- -------------------------------------------------------------
-- 1. Localização em eventos_pessoais
-- -------------------------------------------------------------
alter table public.eventos_pessoais
  add column if not exists localizacao text;

alter table public.eventos_pessoais
  drop constraint if exists eventos_pessoais_localizacao_tamanho;

alter table public.eventos_pessoais
  add constraint eventos_pessoais_localizacao_tamanho
  check (localizacao is null or char_length(btrim(localizacao)) <= 250);

comment on column public.eventos_pessoais.localizacao is
  'Local físico ou sala do compromisso pessoal (até 250 caracteres).';


-- -------------------------------------------------------------
-- 2. Redirecionamento independente e deduplicado (RF12 / S8-B02)
-- -------------------------------------------------------------
create table if not exists public.eventos_cliques_redirecionamento (
  event_id   uuid not null references public.eventos(id) on delete cascade,
  click_id   uuid not null,
  criado_em  timestamptz not null default now(),
  primary key (event_id, click_id)
);

create index if not exists idx_cliques_redirecionamento_evento
  on public.eventos_cliques_redirecionamento (event_id);

alter table public.eventos_cliques_redirecionamento enable row level security;

revoke all on public.eventos_cliques_redirecionamento from public, anon, authenticated;

comment on table public.eventos_cliques_redirecionamento is
  'Deduplicação de acionamentos de Conferir evento por (event_id, click_id), sem identificar o usuário.';

-- Impede que o caminho legado incremente o contador sem validar URL e click_id.
do $$
begin
  if to_regprocedure('public.registrar_interesse(uuid)') is not null then
    revoke all on function public.registrar_interesse(uuid) from public, anon, authenticated;
  end if;
end;
$$;

create or replace function public.registrar_redirecionamento_evento(
  p_evento_id uuid,
  p_click_id uuid
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_link  text;
  v_count integer;
  v_novo  boolean := false;
begin
  if p_evento_id is null or p_click_id is null then
    raise exception 'Informe o evento e o identificador do acionamento'
      using errcode = '22023';
  end if;

  select e.link_externo, e.interessados_count
    into v_link, v_count
    from public.eventos e
   where e.id = p_evento_id
     and e.status = 'aprovado'
     for update;

  if not found then
    raise exception 'Evento não encontrado'
      using errcode = 'P0002';
  end if;

  if v_link is null or btrim(v_link) = '' or v_link !~* '^https?://[^[:space:]<>"]+$' then
    raise exception 'Este evento não possui link oficial disponível'
      using errcode = '22023';
  end if;

  insert into public.eventos_cliques_redirecionamento (event_id, click_id)
  values (p_evento_id, p_click_id)
  on conflict (event_id, click_id) do nothing;

  if found then
    v_novo := true;
    insert into public.cliques_evento (evento_id, click_id)
    values (p_evento_id, p_click_id)
    on conflict (evento_id, click_id) do nothing;

    if found then
      update public.eventos
         set interessados_count = interessados_count + 1
       where id = p_evento_id
      returning interessados_count into v_count;
    else
      v_novo := false;
    end if;
  end if;

  return jsonb_build_object(
    'external_url', btrim(v_link),
    'outbound_clicks_count', coalesce(v_count, 0),
    'incremented', v_novo
  );
end;
$$;

revoke all on function public.registrar_redirecionamento_evento(uuid, uuid) from public;
grant execute on function public.registrar_redirecionamento_evento(uuid, uuid) to anon, authenticated, service_role;


-- -------------------------------------------------------------
-- 3. Gestão de categorias exclusiva de administradores (RF11 / RNF04)
-- -------------------------------------------------------------
revoke insert, update, delete on public.categories from public, anon, authenticated;

drop policy if exists "admin gerencia categorias" on public.categories;
create policy "admin gerencia categorias"
  on public.categories for all
  to authenticated
  using ((select public.is_admin()))
  with check ((select public.is_admin()));

create or replace function public.admin_listar_categorias()
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  v_resultado jsonb;
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores podem gerenciar categorias'
      using errcode = '42501';
  end if;

  select coalesce(
    jsonb_agg(
      jsonb_build_object(
        'id', c.id,
        'nome', c.nome,
        'cor', coalesce(c.cor, '#008bff'),
        'created_at', c.created_at,
        'events_count', (
          (select count(*) from public.eventos e where e.category_id = c.id)
          + (select count(*) from public.eventos_pessoais ep where ep.category_id = c.id)
        )
      )
      order by lower(c.nome), c.id
    ),
    '[]'::jsonb
  )
  into v_resultado
  from public.categories c;

  return v_resultado;
end;
$$;

create or replace function public.admin_criar_categoria(
  p_nome text,
  p_cor text default '#008bff'
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_nome text := btrim(coalesce(p_nome, ''));
  v_cor  text := coalesce(nullif(btrim(p_cor), ''), '#008bff');
  v_cat  public.categories;
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores podem gerenciar categorias'
      using errcode = '42501';
  end if;

  if char_length(v_nome) < 2 or char_length(v_nome) > 80 then
    raise exception 'O nome da categoria deve ter entre 2 e 80 caracteres'
      using errcode = '22023';
  end if;

  if v_cor !~* '^#[0-9a-f]{6}$' then
    raise exception 'Informe uma cor hexadecimal válida (ex.: #008bff)'
      using errcode = '22023';
  end if;

  if exists (select 1 from public.categories where lower(nome) = lower(v_nome)) then
    raise exception 'Já existe uma categoria com este nome'
      using errcode = '22023';
  end if;

  insert into public.categories (nome, cor)
  values (v_nome, v_cor)
  returning * into v_cat;

  return jsonb_build_object(
    'id', v_cat.id,
    'nome', v_cat.nome,
    'cor', coalesce(v_cat.cor, '#008bff'),
    'created_at', v_cat.created_at,
    'events_count', 0
  );
end;
$$;

create or replace function public.admin_excluir_categoria(
  p_categoria_id uuid
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores podem gerenciar categorias'
      using errcode = '42501';
  end if;

  if p_categoria_id is null then
    raise exception 'Categoria inválida'
      using errcode = '22023';
  end if;

  if exists (select 1 from public.eventos where category_id = p_categoria_id)
     or exists (select 1 from public.eventos_pessoais where category_id = p_categoria_id) then
    raise exception 'Não é possível excluir uma categoria vinculada a eventos existentes'
      using errcode = '22023';
  end if;

  delete from public.categories where id = p_categoria_id;

  if not found then
    raise exception 'Categoria não encontrada'
      using errcode = 'P0002';
  end if;
end;
$$;

revoke all on function
  public.admin_listar_categorias(),
  public.admin_criar_categoria(text, text),
  public.admin_excluir_categoria(uuid)
  from public, anon;

grant execute on function
  public.admin_listar_categorias(),
  public.admin_criar_categoria(text, text),
  public.admin_excluir_categoria(uuid)
  to authenticated;


-- -------------------------------------------------------------
-- 4. Atualização das RPCs de listagem pública e sugestões
-- -------------------------------------------------------------
drop function if exists public.listar_eventos_publicos();

create or replace function public.listar_eventos_publicos()
returns table (
  id uuid,
  title text,
  description text,
  starts_at timestamptz,
  ends_at timestamptz,
  all_day boolean,
  start_date date,
  end_date date,
  campus text,
  category text,
  location text,
  external_url text,
  organizer_name text,
  organizer_avatar text,
  source text,
  source_url text,
  outbound_clicks_count integer
)
language sql
stable
security definer
set search_path = ''
as $$
  select
    e.id,
    e.titulo as title,
    e.descricao as description,
    e.data_evento as starts_at,
    e.data_fim as ends_at,
    e.dia_inteiro as all_day,
    e.data_inicio_civil as start_date,
    e.data_fim_civil as end_date,
    cp.nome as campus,
    cat.nome as category,
    e.localizacao as location,
    e.link_externo as external_url,
    p.nome_completo as organizer_name,
    p.avatar_url as organizer_avatar,
    e.fonte as source,
    e.fonte_url as source_url,
    e.interessados_count as outbound_clicks_count
  from public.eventos e
  left join public.campus cp on cp.id = e.campus_id
  left join public.categories cat on cat.id = e.category_id
  left join public.profiles p on p.id = e.autor_id
  where e.status = 'aprovado'
  order by e.data_evento asc, e.id asc;
$$;

revoke all on function public.listar_eventos_publicos() from public;
grant execute on function public.listar_eventos_publicos() to anon, authenticated;

create or replace function public.listar_sugestoes(
  p_status text default 'pendente',
  p_busca text default '',
  p_offset integer default 0
)
returns jsonb
language plpgsql
stable
security definer
set search_path = ''
as $$
declare
  resultado jsonb;
begin
  if not public.is_event_moderator() then
    raise exception 'Apenas professores e administradores' using errcode = '42501';
  end if;
  if p_status is null or p_status not in ('pendente', 'aprovado', 'rejeitado') or p_offset is null or p_offset < 0 then
    raise exception 'Filtro inválido' using errcode = '22023';
  end if;
  with filtrados as (
    select e.id, e.titulo, e.descricao, e.data_evento, e.data_fim, e.dia_inteiro,
      e.data_inicio_civil, e.data_fim_civil, e.localizacao, e.link_externo,
      e.status, e.justificativa_recusa, e.criado_em, p.nome_completo as autor_nome,
      c.nome as campus, cat.nome as categoria
    from public.eventos e join public.profiles p on p.id = e.autor_id
    left join public.campus c on c.id = e.campus_id
    left join public.categories cat on cat.id = e.category_id
    where e.sugestao_estudante and e.status = p_status
      and (coalesce(p_busca, '') = '' or strpos(lower(e.titulo || ' ' || p.nome_completo), lower(btrim(p_busca))) > 0)
  ), pagina as (select * from filtrados order by criado_em, id limit 20 offset p_offset)
  select jsonb_build_object(
    'items', coalesce((select jsonb_agg(to_jsonb(pagina)) from pagina), '[]'::jsonb),
    'total', (select count(*) from filtrados),
    'pending', (select count(*) from public.eventos where sugestao_estudante and status = 'pendente')
  ) into resultado;
  return resultado;
end;
$$;

revoke all on function public.listar_sugestoes(text, text, integer) from public, anon;
grant execute on function public.listar_sugestoes(text, text, integer) to authenticated;
