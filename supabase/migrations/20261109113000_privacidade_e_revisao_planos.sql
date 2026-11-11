-- S6-D02: propriedade privada, estado exclusivo do servidor e revisão atômica.
-- Reaproveita o bucket #43; não cria turmas, matrículas ou confirmação implícita.

drop policy if exists "avaliacoes sao publicas" on public.avaliacoes;
drop policy if exists "planos particulares: usuario cria os proprios planos" on public.planos_ensino;

revoke all on public.planos_ensino, public.candidatos_avaliacao, public.avaliacoes from anon, authenticated;
grant select on public.planos_ensino, public.candidatos_avaliacao, public.avaliacoes to authenticated;
grant all on public.planos_ensino, public.candidatos_avaliacao, public.avaliacoes to service_role;

create policy "dono le candidatos privados"
  on public.candidatos_avaliacao for select to authenticated
  using (exists (select 1 from public.planos_ensino p
                where p.id = plano_id and p.user_id = (select auth.uid())));

create policy "dono le avaliacoes legadas"
  on public.avaliacoes for select to authenticated
  using (exists (select 1 from public.planos_ensino p
                where p.id = plano_id and p.user_id = (select auth.uid())));

-- A autoria é imutável inclusive em conexões de backend que ignoram RLS.
create function public.tg_preserva_dono_plano()
returns trigger language plpgsql set search_path = '' as $$
begin
  if new.user_id is distinct from old.user_id then
    raise exception 'A autoria do plano não pode ser alterada' using errcode = '42501';
  end if;
  return new;
end;
$$;
create trigger planos_preserva_dono before update of user_id on public.planos_ensino
  for each row execute function public.tg_preserva_dono_plano();
revoke all on function public.tg_preserva_dono_plano() from public, anon, authenticated;

-- Não permitir um vínculo privilegiado acidental com evento de outro dono.
create function public.tg_valida_dono_evento_candidato()
returns trigger language plpgsql security definer set search_path = '' as $$
begin
  if new.evento_pessoal_id is not null and not exists (
    select 1 from public.eventos_pessoais e
    join public.planos_ensino p on p.id = new.plano_id
    where e.id = new.evento_pessoal_id and e.user_id = p.user_id
  ) then
    raise exception 'Vínculo de confirmação inválido' using errcode = '42501';
  end if;
  return new;
end;
$$;
create trigger candidatos_valida_dono_evento
  before insert or update of plano_id, evento_pessoal_id on public.candidatos_avaliacao
  for each row execute function public.tg_valida_dono_evento_candidato();
revoke all on function public.tg_valida_dono_evento_candidato() from public, anon, authenticated;

-- Manter o bucket já existente privado e restringir os objetos a uma pasta
-- por dono. UPDATE/DELETE de objetos pelo cliente continuam sem políticas.
update storage.buckets set public = false, file_size_limit = 10485760,
  allowed_mime_types = array['application/pdf'] where id = 'syllabus_files';
drop policy if exists "planos: usuario envia para a propria pasta" on storage.objects;
drop policy if exists "planos: usuario le apenas os proprios arquivos" on storage.objects;
create policy "planos: usuario envia para a propria pasta"
  on storage.objects for insert to authenticated with check (
    bucket_id = 'syllabus_files'
    and name ~* ('^' || (select auth.uid())::text || '/[^/]+[.]pdf$')
    and position(chr(92) in name) = 0
  );
create policy "planos: usuario le apenas os proprios arquivos"
  on storage.objects for select to authenticated using (
    bucket_id = 'syllabus_files'
    and name ~* ('^' || (select auth.uid())::text || '/[^/]+[.]pdf$')
    and position(chr(92) in name) = 0
  );

-- Contrato para S6-B02: revisão explícita do estudante. Não recebe user_id.
-- p_itens = [{candidato_id, acao: confirmar|descartar, titulo?, descricao?, data_hora?}]
-- data_hora é obrigatória para confirmar e exige offset ISO 8601 explícito.
-- Lock do plano serializa seleções parciais/concorrentes; a função inteira é
-- uma transação. Um erro em qualquer item desfaz todas as gravações.
create function public.revisar_candidatos_plano(p_plano_id uuid, p_itens jsonb)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_actor uuid := auth.uid();
  v_plano public.planos_ensino;
  v_candidato public.candidatos_avaliacao;
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
    select * into v_candidato from public.candidatos_avaliacao
      where id = v_id and plano_id = v_plano.id and execucao = v_plano.execucao_atual for update;
    if not found then
      raise exception 'Candidato indisponível neste plano' using errcode = 'P0002';
    end if;
    if v_acao = 'descartar' then
      if (v_item - array['candidato_id','acao']) <> '{}'::jsonb or v_candidato.status = 'confirmado' then
        raise exception 'Descarte inválido' using errcode = '22023';
      end if;
      update public.candidatos_avaliacao set status = 'descartado', revisado_em = now()
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
    v_evento := v_candidato.evento_pessoal_id;
    if v_candidato.status = 'pendente' then
      insert into public.eventos_pessoais(user_id, titulo, descricao, data_hora)
        values (v_actor, v_titulo, v_descricao, v_data_hora) returning id into v_evento;
      update public.candidatos_avaliacao set status = 'confirmado', revisado_em = now(),
        evento_pessoal_id = v_evento where id = v_id;
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
