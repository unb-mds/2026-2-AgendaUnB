-- S7-B01: preparação local sem retenção do PDF; somente snapshot autorizado entra na fila.
-- Não migra PDFs existentes para a IA e não concede autorização retroativa.
-- S7-D01 is the canonical candidate/version model. The historical S6 table
-- has already been removed; retain civil date/time separately from instants.
alter table public.avaliacoes
  add column execucao integer not null default 0 check (execucao >= 0),
  add column data_sugerida date,
  add column hora_sugerida time,
  add column campos_ambiguos text[] not null default '{}',
  add column modelo_ia text,
  add column revisado_em timestamptz;

alter table public.planos_ensino
  add column versao_aprovada_id uuid references public.versoes_plano(id) on delete restrict,
  add column texto_preparado jsonb,
  add column texto_aprovado jsonb,
  add column hash_texto_aprovado text,
  add column autorizado_em timestamptz,
  add column enfileirado_em timestamptz,
  add column duracao_preparacao_ms integer check (duracao_preparacao_ms >= 0),
  add column versao_texto integer not null default 0 check (versao_texto >= 0);

alter table public.planos_ensino drop constraint planos_particular_exige_arquivo;
alter table public.planos_ensino drop constraint planos_tipo_arquivo_pdf;
alter table public.planos_ensino
  add constraint planos_tipo_arquivo_digital check (tipo_arquivo in ('pdf','text')),
  add constraint planos_particular_exige_fonte check (
    tipo <> 'particular' or caminho_arquivo is not null or texto_preparado is not null),
  add constraint planos_texto_preparado_limitado check (
    texto_preparado is null or (jsonb_typeof(texto_preparado)='array'
      and jsonb_array_length(texto_preparado) between 1 and 10
      and octet_length(texto_preparado::text) <= 260000)),
  add constraint planos_autorizacao_coerente check (
    (autorizado_em is null and texto_aprovado is null and hash_texto_aprovado is null
      and enfileirado_em is null and versao_texto=0)
    or (autorizado_em is not null and texto_aprovado is not null
      and jsonb_typeof(texto_aprovado)='array'
      and jsonb_array_length(texto_aprovado) between 1 and 10
      and octet_length(texto_aprovado::text) <= 260000
      and hash_texto_aprovado is not null and hash_texto_aprovado ~ '^[a-f0-9]{64}$'
      and enfileirado_em is not null and versao_texto > 0));

alter table public.avaliacoes alter column pagina_origem drop not null;
-- Linhas históricas de outros tipos continuam legíveis; novas escritas são restritas.
alter table public.avaliacoes add constraint candidatos_s7_prova_trabalho
  check (versao_processamento <> 'syllabus-v3-approved-text' or tipo in ('prova','trabalho'));

create function public.tg_preserva_texto_autorizado()
returns trigger language plpgsql set search_path = '' as $$
begin
  if old.status='processando' and
     (new.texto_aprovado, new.hash_texto_aprovado, new.autorizado_em, new.versao_texto, new.versao_aprovada_id)
       is distinct from
     (old.texto_aprovado, old.hash_texto_aprovado, old.autorizado_em, old.versao_texto, old.versao_aprovada_id) then
    raise exception 'O snapshot em processamento não pode ser alterado' using errcode='42501';
  end if;
  return new;
end;
$$;
create trigger planos_preserva_texto_autorizado before update on public.planos_ensino
  for each row execute function public.tg_preserva_texto_autorizado();
revoke all on function public.tg_preserva_texto_autorizado() from public, anon, authenticated;

-- Concilia as políticas conhecidas das branches S6-D02. Somente leitura do dono
-- é permitida ao cliente; novas colunas de texto não recebem escrita direta.
do $$
declare item record;
begin
  for item in select tablename, policyname from pg_policies
    where schemaname='public' and tablename in ('planos_ensino','avaliacoes')
      and policyname <> 'leitura de candidatos de versoes compartilhadas' loop
    execute format('drop policy %I on public.%I',item.policyname,item.tablename);
  end loop;
end;
$$;
revoke all on public.planos_ensino,public.avaliacoes from anon,authenticated;
grant select on public.planos_ensino,public.avaliacoes to authenticated;
grant all on public.planos_ensino,public.avaliacoes to service_role;
create policy "planos particulares: usuario le apenas os proprios planos"
  on public.planos_ensino for select to authenticated using (user_id=(select auth.uid()));
create policy "dono le avaliacoes legadas" on public.avaliacoes for select to authenticated
  using (exists(select 1 from public.planos_ensino p where p.id=plano_id and p.user_id=(select auth.uid())));

create index planos_fila_texto_autorizado on public.planos_ensino(status,enfileirado_em)
  where autorizado_em is not null and status in ('pendente','processando');
comment on column public.planos_ensino.texto_aprovado is
  'Snapshot privado exato autorizado pelo dono. Somente o servidor escreve. Não contém PDF.';

-- Novos PDFs não são retidos. Fechar o caminho de upload direto pelo cliente;
-- arquivos históricos continuam privados e legíveis somente pelo dono.
drop policy if exists "planos: usuario envia para a propria pasta" on storage.objects;
drop policy if exists "planos: usuario le apenas os proprios arquivos" on storage.objects;
create policy "planos: usuario le apenas os proprios arquivos" on storage.objects
  for select to authenticated using (
    bucket_id='syllabus_files'
    and name ~* ('^' || (select auth.uid())::text || '/[^/]+[.]pdf$')
    and position(chr(92) in name)=0);

-- Compatibility RPC remains private-owner only; shared imports use S7-B04.
create or replace function public.revisar_candidatos_plano(p_plano_id uuid, p_itens jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_plano public.planos_ensino;
  v_candidato public.avaliacoes;
  v_item jsonb;
  v_id uuid;
  v_ids uuid[] := '{}'::uuid[];
  v_acao text;
  v_titulo text;
  v_descricao text;
  v_data_hora timestamptz;
  v_evento uuid;
  v_resultado jsonb := '[]'::jsonb;
begin
  if v_actor is null then
    raise exception 'Autenticação necessária' using errcode = '42501';
  end if;
  if p_itens is null or jsonb_typeof(p_itens) <> 'array' then
    raise exception 'Seleção inválida' using errcode = '22023';
  end if;
  if jsonb_array_length(p_itens) not between 1 and 100 then
    raise exception 'Selecione entre 1 e 100 candidatos' using errcode = '22023';
  end if;
  select * into v_plano from public.planos_ensino
    where id = p_plano_id and user_id = v_actor and tipo = 'particular' for update;
  if not found then
    raise exception 'Plano não encontrado' using errcode = 'P0002';
  end if;
  if v_plano.status <> 'concluido' then
    raise exception 'O plano ainda não foi concluído' using errcode = '22023';
  end if;

  for v_item in select value from jsonb_array_elements(p_itens) loop
    if jsonb_typeof(v_item) <> 'object' or
       (v_item - array['candidato_id','acao','titulo','descricao','data_hora']) <> '{}'::jsonb or
       jsonb_typeof(v_item->'candidato_id') is distinct from 'string' or
       jsonb_typeof(v_item->'acao') is distinct from 'string' then
      raise exception 'Item inválido' using errcode = '22023';
    end if;
    v_id := (v_item->>'candidato_id')::uuid;
    v_acao := v_item->>'acao';
    if v_id = any(v_ids) or v_acao not in ('confirmar', 'descartar') then
      raise exception 'Item duplicado ou ação inválida' using errcode = '22023';
    end if;
    v_ids := array_append(v_ids, v_id);
    select * into v_candidato from public.avaliacoes
      where id = v_id and plano_id = v_plano.id and execucao = v_plano.execucao_atual for update;
    if not found then
      raise exception 'Candidato indisponível neste plano' using errcode = 'P0002';
    end if;
    if v_acao = 'descartar' then
      if (v_item - array['candidato_id','acao']) <> '{}'::jsonb or v_candidato.status = 'confirmado' then
        raise exception 'Descarte inválido' using errcode = '22023';
      end if;
      update public.avaliacoes set status = 'descartado', revisado_em = now()
        where id = v_id and status = 'pendente';
      v_resultado := v_resultado || jsonb_build_array(jsonb_build_object(
        'candidato_id', v_id, 'status', 'descartado', 'evento_pessoal_id', null));
      continue;
    end if;

    if (v_item ? 'titulo' and jsonb_typeof(v_item->'titulo') <> 'string') or
       jsonb_typeof(v_item->'data_hora') is distinct from 'string' or
       (v_item ? 'descricao' and jsonb_typeof(v_item->'descricao') not in ('string','null')) then
      raise exception 'Dados de confirmação inválidos' using errcode = '22023';
    end if;
    v_titulo := btrim(coalesce(v_item->>'titulo', v_candidato.titulo));
    v_descricao := nullif(btrim(v_item->>'descricao'), '');
    if char_length(v_titulo) not between 3 and 200 or char_length(v_descricao) > 10000 or
       (v_item->>'data_hora') !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}(:[0-9]{2})?(Z|[+-][0-9]{2}:[0-9]{2})$' then
      raise exception 'Título ou data com fuso inválidos' using errcode = '22023';
    end if;
    v_data_hora := (v_item->>'data_hora')::timestamptz;
    if v_candidato.status = 'descartado' then
      raise exception 'Candidato já descartado' using errcode = '22023';
    end if;
    v_evento := null;
    select id into v_evento from public.eventos_pessoais
      where user_id=v_actor and origem_avaliacao_id=v_id;
    if v_candidato.status = 'pendente' then
      insert into public.eventos_pessoais(user_id, titulo, descricao, data_hora,
          origem_plano_id, origem_avaliacao_id, origem_versao_id, origem_pagina, origem_trecho)
        values (v_actor, v_titulo, v_descricao, v_data_hora, v_plano.id, v_id,
          v_candidato.versao_id, v_candidato.pagina_origem, v_candidato.trecho_origem) returning id into v_evento;
      update public.avaliacoes set status = 'confirmado', revisado_em = now() where id = v_id;
    end if;
    -- Confirmado com vínculo nulo significa evento apagado pelo dono. Não recriar.
    v_resultado := v_resultado || jsonb_build_array(jsonb_build_object(
      'candidato_id', v_id, 'status', 'confirmado', 'evento_pessoal_id', v_evento));
  end loop;
  return jsonb_build_object('plano_id', p_plano_id, 'itens', v_resultado);
exception when data_exception then
  raise exception 'Dados de revisão inválidos' using errcode = '22023';
end;
$$;
revoke all on function public.revisar_candidatos_plano(uuid, jsonb) from public, anon, authenticated, service_role;
grant execute on function public.revisar_candidatos_plano(uuid, jsonb) to authenticated;

comment on function public.revisar_candidatos_plano(uuid, jsonb) is
  'Revisão explícita, atômica e idempotente do dono. Backend privilegiado deve definir auth.uid via identidade verificada e somente na transação atual; nunca aceitar autoria do payload.';

-- No callable helper may retain a reference to the removed S6 candidate table.
drop function if exists public.tg_valida_dono_evento_candidato();
