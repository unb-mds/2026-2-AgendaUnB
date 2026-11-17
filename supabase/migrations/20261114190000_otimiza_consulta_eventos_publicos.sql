-- Otimiza a consulta de eventos públicos e pessoais com índices e adiciona RPC pública
-- somente-leitura para permitir fallback rápido caso a API esteja em cold start.

create index if not exists idx_eventos_aprovados_data_evento
  on public.eventos (data_evento asc, id asc)
  where status = 'aprovado';

create index if not exists idx_eventos_campus_id
  on public.eventos (campus_id);

create index if not exists idx_eventos_category_id
  on public.eventos (category_id);

create index if not exists idx_eventos_autor_id
  on public.eventos (autor_id);

create index if not exists idx_eventos_pessoais_user_data_hora
  on public.eventos_pessoais (user_id, data_hora asc);

create or replace function public.listar_eventos_publicos()
returns table (
  id uuid,
  title text,
  description text,
  starts_at timestamptz,
  campus text,
  category text,
  location text,
  external_url text,
  organizer_name text,
  organizer_avatar text
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
    cp.nome as campus,
    cat.nome as category,
    e.localizacao as location,
    e.link_externo as external_url,
    p.nome_completo as organizer_name,
    p.avatar_url as organizer_avatar
  from public.eventos e
  left join public.campus cp on cp.id = e.campus_id
  left join public.categories cat on cat.id = e.category_id
  left join public.profiles p on p.id = e.autor_id
  where e.status = 'aprovado'
  order by e.data_evento asc, e.id asc;
$$;

revoke all on function public.listar_eventos_publicos() from public;
grant execute on function public.listar_eventos_publicos() to anon, authenticated;
