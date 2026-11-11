-- =============================================================
-- S8-B02 (#79) — Redirecionamento de Conferir evento contado por clique
--
--   S8-B02 (#79)  redirecionamento contado uma vez por click_id,
--                 com validação do link e sem identificar a pessoa
--
-- Requisitos: RF17 e RNF02.
--
-- As regras que precisam valer em qualquer caminho de escrita ficam
-- no banco (chaves únicas, triggers e funções). A API chama
-- registrar_clique_evento() e devolve a URL.
-- Nada desta migração é gravável pelo navegador.
-- =============================================================


-- -------------------------------------------------------------
-- 1. Conferir evento: redirecionamento contado uma vez por clique (#79)
--
-- click_id é um UUID gerado pelo navegador a cada acionamento; não
-- identifica a pessoa. Reenviar o mesmo click_id (retry, duplo
-- clique) não soma de novo. A API chama esta função e devolve a URL.
--
-- registrar_interesse(uuid), o caminho antigo sem deduplicação nem
-- validação de link, deixa de existir.
-- -------------------------------------------------------------
create table public.cliques_evento (
  evento_id  uuid not null references public.eventos(id) on delete cascade,
  click_id   uuid not null,
  criado_em  timestamptz not null default now(),
  primary key (evento_id, click_id)
);

create index idx_cliques_evento_criado on public.cliques_evento (criado_em);

comment on table public.cliques_evento is
  'Deduplicação dos redirecionamentos. Sem usuário, IP ou agente: só o evento e um identificador aleatório do clique.';

create or replace function public.registrar_clique_evento(p_evento_id uuid, p_click_id uuid)
returns text
language plpgsql
set search_path = ''
as $$
declare
  v_link text;
begin
  if p_click_id is null then
    raise exception 'click_id obrigatório' using errcode = '22023';
  end if;

  select link_externo into v_link
    from public.eventos
   where id = p_evento_id
     and status = 'aprovado'
     and link_externo ~* '^https?://[^[:space:]<>"]+$';
  if not found then
    raise exception 'Evento indisponível ou sem link' using errcode = 'P0002';
  end if;

  insert into public.cliques_evento (evento_id, click_id)
  values (p_evento_id, p_click_id)
  on conflict do nothing;

  if found then
    update public.eventos
       set interessados_count = interessados_count + 1
     where id = p_evento_id;
  end if;

  return v_link;
end;
$$;

drop function if exists public.registrar_interesse(uuid);

comment on column public.eventos.interessados_count is
  'Redirecionamentos acionados em Conferir evento, um por click_id. Não mede visitantes únicos, inscrição ou presença.';

-- -------------------------------------------------------------
-- 2. Acesso
--
-- Só o servidor registra cliques e lê o registro de deduplicação.
-- -------------------------------------------------------------
alter table public.cliques_evento enable row level security;

revoke all on public.cliques_evento from anon, authenticated;

revoke execute on function public.registrar_clique_evento(uuid, uuid) from public, anon, authenticated;
grant execute on function public.registrar_clique_evento(uuid, uuid) to service_role;
