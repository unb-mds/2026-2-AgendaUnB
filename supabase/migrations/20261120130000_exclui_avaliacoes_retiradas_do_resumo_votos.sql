create or replace function public.resumo_votos_versao(p_ator uuid, p_versao_id uuid)
returns table (avaliacao_id uuid, confirmam bigint, contestam bigint, meu_voto text)
language plpgsql
stable
set search_path = ''
as $$
begin
  if not public.ator_pode_ler_versao(p_ator, p_versao_id) then
    raise exception 'Sem acesso a esta versão' using errcode = '42501';
  end if;
  return query
    select a.id,
           count(vt.user_id) filter (where vt.valor = 'confirma'),
           count(vt.user_id) filter (where vt.valor = 'contesta'),
           max(vt.valor) filter (where vt.user_id = p_ator)
      from public.avaliacoes a
      left join public.votos_avaliacao vt on vt.avaliacao_id = a.id
     where a.versao_id = p_versao_id
       and a.status <> 'descartado'
     group by a.id, a.ordem
     order by a.ordem nulls last, a.id;
end;
$$;
