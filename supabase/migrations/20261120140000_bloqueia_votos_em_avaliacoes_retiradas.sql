create or replace function public.votar_avaliacao(p_ator uuid, p_avaliacao_id uuid, p_valor text)
returns jsonb
language plpgsql
set search_path = ''
as $$
declare
  v_versao uuid;
begin
  if p_valor is null or p_valor not in ('confirma', 'contesta') then
    raise exception 'Voto inválido' using errcode = '22023';
  end if;

  -- Mantém a elegibilidade do candidato até o fim da gravação do voto.
  select a.versao_id into v_versao
    from public.avaliacoes a
    join public.versoes_plano v on v.id = a.versao_id
   where a.id = p_avaliacao_id
     and a.status <> 'descartado'
     and v.visibilidade = 'compartilhada'
   for share of a;
  if not found then
    raise exception 'Candidato não disponível para voto' using errcode = 'P0002';
  end if;
  if not public.ator_pode_ler_versao(p_ator, v_versao) then
    raise exception 'Siga a turma para votar' using errcode = '42501';
  end if;

  insert into public.votos_avaliacao (user_id, avaliacao_id, valor)
  values (p_ator, p_avaliacao_id, p_valor)
  on conflict (user_id, avaliacao_id)
  do update set valor = excluded.valor, atualizado_em = now()
   where public.votos_avaliacao.valor is distinct from excluded.valor;

  return (
    select jsonb_build_object(
      'avaliacao_id', p_avaliacao_id,
      'confirmam', count(*) filter (where valor = 'confirma'),
      'contestam', count(*) filter (where valor = 'contesta'),
      'meu_voto', p_valor)
      from public.votos_avaliacao where avaliacao_id = p_avaliacao_id);
end;
$$;
