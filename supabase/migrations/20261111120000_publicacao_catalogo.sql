-- Publicação atômica do catálogo #70/#71; ofertas e vínculos nunca são apagados.
alter table public.sincronizacoes_catalogo
  add column unidades jsonb not null default '[]',
  add column periodos jsonb not null default '[]',
  add column cobertura jsonb not null default '[]',
  add column rejeitadas jsonb not null default '[]';
alter table public.ofertas_turma add column publicacao_id uuid references public.sincronizacoes_catalogo(id);
create index idx_ofertas_publicacao on public.ofertas_turma(publicacao_id);

create or replace function public.estado_catalogo(p_origem text default 'followw',
                                                p_validade interval default interval '24 hours')
returns jsonb language sql stable set search_path = '' as $$
  with ultima_ok as (
    select max(concluida_em) em from public.sincronizacoes_catalogo
    where origem=p_origem and status='concluida'
  ), ultima as (
    select status from public.sincronizacoes_catalogo where origem=p_origem and status <> 'executando'
    order by iniciada_em desc, id desc limit 1
  ) select jsonb_build_object('atualizado_em', em,
    'desatualizado', em is null or em < now()-p_validade or coalesce((select status from ultima),'falha')='falha',
    'tem_cache', em is not null) from ultima_ok;
$$;

-- Vínculos só pelo backend: valida disponibilidade e proprietário.
revoke insert, update, delete on public.vinculos_turma from anon, authenticated;
grant all on public.sincronizacoes_catalogo to service_role;

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
  v_natural_id uuid;
  v_natural_oid text;
  v_oferta      public.ofertas_turma;
begin
  if v_semestre not in (1,2) or v_ano not between 2000 and 2100 then
    raise exception 'Periodo invalido' using errcode='22023';
  end if;
  if v_codigo = '' or v_nome = '' or v_turma = '' or v_ano is null or v_semestre is null then
    raise exception 'Oferta sem código, nome, turma, ano ou semestre: revisar antes de disponibilizar'
      using errcode = '22023';
  end if;

  perform pg_advisory_xact_lock(hashtextextended(
    'catalogo:' || v_origem || ':' || coalesce(v_disc_oid, v_codigo), 0));

  -- Reconcilia o ID da disciplina sem substituir a identidade local preexistente.
  select id, origem_id into v_natural_id, v_natural_oid from public.disciplinas
   where origem=v_origem and upper(btrim(codigo))=v_codigo
     and coalesce(unidade,'')=coalesce(v_unidade,'') and coalesce(nivel,'')=coalesce(v_nivel,'')
   order by criado_em limit 1 for update;
  if v_disc_oid is not null then
    select id into v_disc_id from public.disciplinas where origem=v_origem and origem_id=v_disc_oid;
    if (v_disc_id is not null and v_natural_id is not null and v_disc_id <> v_natural_id)
       or (v_natural_oid is not null and v_natural_oid <> v_disc_oid) then
      raise exception 'Identidade da disciplina conflitante' using errcode='55000';
    end if;
  end if;
  v_disc_id := coalesce(v_disc_id, v_natural_id);
  if v_disc_id is not null and v_disc_oid is not null then
    update public.disciplinas set origem_id=v_disc_oid where id=v_disc_id and origem_id is null;
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

  if v_oferta.origem_id is not null and v_oferta_oid is not null and v_oferta.origem_id <> v_oferta_oid then
    raise exception 'ID da oferta conflitante' using errcode='55000';
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

