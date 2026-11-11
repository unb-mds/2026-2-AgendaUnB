-- =============================================================
-- S7-B03 (#70) — Sincronização do catálogo público de turmas
--
--   S7-B03 (#70)  upsert com identidade estável, registro das
--                 sincronizações e estado do cache
--   ADR-009
--
-- Requisitos: RF09 e RNF11.
--
-- O adaptador do Followw (Python) consulta a origem; esta migração
-- grava. Nada aqui é chamável pelo navegador.
-- =============================================================


-- -------------------------------------------------------------
-- 1. Sincronização do catálogo de turmas (#70, ADR-009)
--
-- O adaptador (Python) consulta o Followw; esta função grava. A
-- identidade da oferta não muda entre sincronizações:
--   1. origem + ID da oferta na origem, quando a origem o fornece;
--   2. senão disciplina + turma + ano + semestre, com a disciplina
--      identificada pelo ID da origem ou, na falta dele, por código,
--      unidade e nível.
-- Professor e horário são atualizados; turmas seguidas nunca são
-- removidas por uma sincronização.
--
-- p = {"origem": "followw", "oferta_origem_id"?, "disciplina_origem_id"?,
--      "codigo", "nome", "unidade"?, "nivel"?, "turma", "ano", "semestre",
--      "professor"?, "horarios"?, "atualizado_na_origem_em"?}
-- Retorno: {"id", "acao": "criada" | "atualizada" | "inalterada"}
-- -------------------------------------------------------------
create or replace function public.registrar_oferta_catalogo(p jsonb)
returns jsonb
language plpgsql
set search_path = ''
as $$
declare
  v_origem      text := coalesce(nullif(p ->> 'origem', ''), 'followw');
  v_oferta_oid  text := nullif(btrim(p ->> 'oferta_origem_id'), '');
  v_disc_oid    text := nullif(btrim(p ->> 'disciplina_origem_id'), '');
  v_codigo      text := upper(btrim(coalesce(p ->> 'codigo', '')));
  v_nome        text := btrim(coalesce(p ->> 'nome', ''));
  v_unidade     text := nullif(btrim(p ->> 'unidade'), '');
  v_nivel       text := nullif(btrim(p ->> 'nivel'), '');
  -- Só espaços nas pontas saem: "01" continua "01".
  v_turma       text := btrim(coalesce(p ->> 'turma', ''));
  v_ano         smallint := (p ->> 'ano')::smallint;
  v_semestre    smallint := (p ->> 'semestre')::smallint;
  v_professor   text := nullif(btrim(p ->> 'professor'), '');
  v_horarios    text := nullif(btrim(p ->> 'horarios'), '');
  v_na_origem   timestamptz := nullif(p ->> 'atualizado_na_origem_em', '')::timestamptz;
  v_disc_id     uuid;
  v_oferta      public.ofertas_turma;
begin
  if v_codigo = '' or v_nome = '' or v_turma = '' or v_ano is null or v_semestre is null then
    raise exception 'Oferta sem código, nome, turma, ano ou semestre: revisar antes de disponibilizar'
      using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'catalogo:' || v_origem || ':' || coalesce(v_disc_oid, v_codigo), 0));

  if v_disc_oid is not null then
    select id into v_disc_id from public.disciplinas where origem = v_origem and origem_id = v_disc_oid;
  else
    select id into v_disc_id from public.disciplinas
     where origem = v_origem and origem_id is null and upper(btrim(codigo)) = v_codigo
       and coalesce(unidade, '') = coalesce(v_unidade, '') and coalesce(nivel, '') = coalesce(v_nivel, '');
  end if;
  if v_disc_id is null then
    insert into public.disciplinas (origem, origem_id, codigo, nome, unidade, nivel, atualizado_na_origem_em)
    values (v_origem, v_disc_oid, v_codigo, left(v_nome, 300), v_unidade, v_nivel, v_na_origem)
    returning id into v_disc_id;
  else
    update public.disciplinas
       set codigo = v_codigo, nome = left(v_nome, 300), unidade = v_unidade, nivel = v_nivel,
           atualizado_na_origem_em = coalesce(v_na_origem, atualizado_na_origem_em)
     where id = v_disc_id
       and (codigo, nome, coalesce(unidade, ''), coalesce(nivel, ''))
           is distinct from (v_codigo, left(v_nome, 300), coalesce(v_unidade, ''), coalesce(v_nivel, ''));
  end if;

  if v_oferta_oid is not null then
    select * into v_oferta from public.ofertas_turma where origem = v_origem and origem_id = v_oferta_oid for update;
  end if;
  if v_oferta.id is null then
    select * into v_oferta from public.ofertas_turma
     where disciplina_id = v_disc_id and turma = v_turma and ano = v_ano and semestre = v_semestre for update;
  end if;

  if v_oferta.id is null then
    insert into public.ofertas_turma (disciplina_id, origem, origem_id, turma, ano, semestre,
                                      professor, horarios, atualizado_na_origem_em, sincronizado_em)
    values (v_disc_id, v_origem, v_oferta_oid, v_turma, v_ano, v_semestre,
            left(v_professor, 300), left(v_horarios, 500), v_na_origem, now())
    returning * into v_oferta;
    return jsonb_build_object('id', v_oferta.id, 'acao', 'criada');
  end if;

  -- Colisão: o ID da origem aponta para uma oferta e a chave natural para outra.
  if v_oferta.disciplina_id <> v_disc_id or v_oferta.turma <> v_turma
     or v_oferta.ano <> v_ano or v_oferta.semestre <> v_semestre then
    raise exception 'Identidade da oferta % diverge da já registrada: revisar antes de disponibilizar', v_oferta.id
      using errcode = '55000';
  end if;

  if (coalesce(v_oferta.professor, ''), coalesce(v_oferta.horarios, ''), coalesce(v_oferta.origem_id, ''))
     is not distinct from (coalesce(left(v_professor, 300), ''), coalesce(left(v_horarios, 500), ''),
                           coalesce(v_oferta_oid, coalesce(v_oferta.origem_id, ''))) then
    update public.ofertas_turma set sincronizado_em = now() where id = v_oferta.id;
    return jsonb_build_object('id', v_oferta.id, 'acao', 'inalterada');
  end if;

  update public.ofertas_turma
     set professor = left(v_professor, 300), horarios = left(v_horarios, 500),
         origem_id = coalesce(v_oferta_oid, origem_id),
         atualizado_na_origem_em = coalesce(v_na_origem, atualizado_na_origem_em),
         sincronizado_em = now()
   where id = v_oferta.id;
  return jsonb_build_object('id', v_oferta.id, 'acao', 'atualizada');
end;
$$;

-- Uma linha por sincronização: evidência e base do aviso de
-- catálogo desatualizado.
create table public.sincronizacoes_catalogo (
  id             uuid primary key default gen_random_uuid(),
  origem         text not null default 'followw' check (origem in ('followw')),
  status         text not null default 'executando'
                 check (status in ('executando', 'concluida', 'falha')),
  iniciada_em    timestamptz not null default now(),
  concluida_em   timestamptz,
  ofertas_lidas  integer not null default 0 check (ofertas_lidas >= 0),
  criadas        integer not null default 0 check (criadas >= 0),
  atualizadas    integer not null default 0 check (atualizadas >= 0),
  erro_codigo    text check (erro_codigo is null or char_length(erro_codigo) <= 60),
  constraint sincronizacoes_conclusao_coerente
    check ((status = 'executando') = (concluida_em is null)),
  constraint sincronizacoes_erro_apenas_em_falha
    check (erro_codigo is null or status = 'falha')
);

create index idx_sincronizacoes_catalogo on public.sincronizacoes_catalogo (origem, iniciada_em desc);

comment on table public.sincronizacoes_catalogo is
  'Execuções do adaptador do catálogo. erro_codigo guarda só um código curto, nunca o corpo da resposta da origem.';

-- Estado do cache para a API devolver source_updated_at e stale.
-- Desatualizado = a tentativa mais recente falhou, ou a última
-- sincronização concluída é mais antiga que a validade.
create or replace function public.estado_catalogo(p_origem text default 'followw',
                                                  p_validade interval default interval '24 hours')
returns jsonb
language sql
stable
set search_path = ''
as $$
  with ultima_ok as (
    select max(concluida_em) as em from public.sincronizacoes_catalogo
     where origem = p_origem and status = 'concluida'
  ), ultima as (
    select status from public.sincronizacoes_catalogo
     where origem = p_origem and status <> 'executando'
     order by iniciada_em desc limit 1
  )
  select jsonb_build_object(
    'atualizado_em', (select em from ultima_ok),
    'desatualizado', (select em from ultima_ok) is null
                     or (select em from ultima_ok) < now() - p_validade
                     or coalesce((select status from ultima), 'falha') = 'falha',
    'tem_cache', exists (select 1 from public.ofertas_turma where origem = p_origem));
$$;

-- -------------------------------------------------------------
-- 2. Acesso
--
-- Só o servidor sincroniza e lê o registro das execuções.
-- -------------------------------------------------------------
alter table public.sincronizacoes_catalogo enable row level security;

revoke all on public.sincronizacoes_catalogo from anon, authenticated;

revoke execute on function
  public.registrar_oferta_catalogo(jsonb),
  public.estado_catalogo(text, interval)
  from public, anon, authenticated;

grant execute on function
  public.registrar_oferta_catalogo(jsonb),
  public.estado_catalogo(text, interval)
  to service_role;
