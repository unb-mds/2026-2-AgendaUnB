-- =============================================================
-- S7-B04 (#72) — Confirmação idempotente e importação por usuário
--
--   S7-B04 (#72)  confirmação em transação, por usuário, com
--                 Idempotency-Key e sem restaurar evento apagado
--   ADR-010
--
-- Requisitos: RF07, RF09 e RNF04.
--
-- O back-end conecta com um usuário que ignora RLS, então as regras
-- de quem pode ler e importar ficam em funções que recebem o ator (id
-- da conta validada pela API) e conferem a permissão no banco.
-- Nenhuma delas é chamável pelo navegador.
--
-- Códigos de erro, para a API traduzir:
--   42501 -> 403   sem permissão sobre a versão
--   P0002 -> 404   versão, candidato ou plano inexistente
--   22023 -> 422   dados inválidos (inclui data ambígua sem correção)
--   55000 -> 409   estado não permite a ação
--   AG409 -> 409   Idempotency-Key reutilizada com outro conteúdo
-- =============================================================


-- -------------------------------------------------------------
-- 1. Quem lê uma versão
--
-- O autor da versão, sempre. Os demais, só se ela estiver
-- compartilhada e a conta seguir a oferta do plano.
--
-- Antes a regra usava o dono do PLANO. Com revisões, uma versão
-- pode ter autor diferente do dono do plano: o rascunho privado de
-- uma revisão pertence a quem a escreveu, e o papel professor/admin
-- não abre conteúdo privado de ninguém.
-- -------------------------------------------------------------
create or replace function public.ator_pode_ler_versao(p_ator uuid, p_versao_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select p_ator is not null and exists (
    select 1
      from public.versoes_plano v
      join public.planos_ensino p on p.id = v.plano_id
     where v.id = p_versao_id
       and (
         v.autor_id = p_ator
         or (
           v.visibilidade = 'compartilhada'
           and p.oferta_id is not null
           and exists (
             select 1 from public.vinculos_turma vt
              where vt.user_id = p_ator and vt.oferta_id = p.oferta_id
           )
         )
       )
  );
$$;

create or replace function public.pode_ler_versao(p_versao_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select public.ator_pode_ler_versao((select auth.uid()), p_versao_id);
$$;

-- A leitura de candidatos passa a depender da versão.
drop policy if exists "dono do plano consulta candidatos" on public.avaliacoes;

-- "dono le avaliacoes legadas" (20261110120000) liberava ao dono do
-- plano os candidatos de TODAS as versões, inclusive o rascunho privado
-- de uma revisão escrita por outra conta. Passa a cobrir só as versões
-- que o próprio dono escreveu; as demais seguem pode_ler_versao.
-- Nome, papel e comando são mantidos: o worker (privacy.py) confere
-- esse conjunto de políticas antes de processar.
alter policy "dono le avaliacoes legadas" on public.avaliacoes
  using (exists (
    select 1
      from public.planos_ensino p
      join public.versoes_plano v on v.plano_id = p.id
     where p.id = plano_id
       and v.id = versao_id
       and p.user_id = (select auth.uid())
       and v.autor_id = (select auth.uid())));


-- -------------------------------------------------------------
-- 2. Confirmação idempotente por ação (#72, ADR-010)
--
-- Cada ação de confirmar leva uma Idempotency-Key. A operação e seus
-- itens são gravados na mesma transação dos eventos.
--   - repetir a chave com o mesmo conteúdo devolve o resultado
--     anterior e NÃO recria evento que a pessoa já apagou;
--   - a mesma chave com outro conteúdo é recusada (AG409);
--   - no máximo um evento ativo por conta e candidato, mesmo com
--     chaves diferentes;
--   - reimportar depois de apagar exige uma chave nova.
-- -------------------------------------------------------------
create table public.operacoes_importacao (
  id             uuid primary key default gen_random_uuid(),
  user_id        uuid not null references public.profiles(id) on delete cascade,
  chave          text not null check (char_length(chave) between 8 and 200),
  versao_id      uuid references public.versoes_plano(id) on delete set null,
  conteudo_hash  text not null,
  criado_em      timestamptz not null default now(),
  constraint operacoes_importacao_chave_unica unique (user_id, chave)
);

create table public.itens_importacao (
  operacao_id        uuid not null references public.operacoes_importacao(id) on delete cascade,
  avaliacao_id       uuid not null,
  evento_pessoal_id  uuid references public.eventos_pessoais(id) on delete set null,
  resultado          text not null check (resultado in ('criado', 'ja_importado')),
  primary key (operacao_id, avaliacao_id)
);

create index idx_itens_importacao_evento
  on public.itens_importacao (evento_pessoal_id)
  where evento_pessoal_id is not null;

comment on table public.operacoes_importacao is
  'Uma ação de confirmação/importação, identificada pela Idempotency-Key da conta. Preservada mesmo que os eventos sejam apagados.';
comment on column public.itens_importacao.evento_pessoal_id is
  'Evento criado ou já existente. Fica nulo quando a pessoa apaga o evento: retry da mesma chave não o recria.';

-- p_itens = [{"candidato_id": uuid, "titulo"?: text, "descricao"?: text, "categoria"?: text,
--             "inicio"?: ISO 8601 com fuso,
--             "dia_inteiro"?: true, "data_inicio"?: date, "data_fim"?: date (exclusivo)}]
--
-- Retorno: {"operacao_id", "repetida", "itens": [{"candidato_id", "evento_id", "resultado", "removido"}]}
create or replace function public.confirmar_importacao(
  p_ator uuid, p_chave text, p_versao_id uuid, p_itens jsonb
)
returns jsonb
language plpgsql
set search_path = ''
as $$
declare
  v_hash       text;
  v_operacao   public.operacoes_importacao;
  v_versao     public.versoes_plano;
  v_plano      public.planos_ensino;
  v_item       jsonb;
  v_candidato  public.avaliacoes;
  v_ids        uuid[] := '{}';
  v_id         uuid;
  v_titulo     text;
  v_inicio     timestamptz;
  v_dia        boolean;
  v_data_ini   date;
  v_data_fim   date;
  v_categoria  uuid;
  v_evento     uuid;
  v_resultado  text;
begin
  if p_ator is null or not exists (select 1 from public.profiles where id = p_ator) then
    raise exception 'Conta não encontrada' using errcode = '42501';
  end if;
  if p_chave is null or char_length(p_chave) not between 8 and 200 then
    raise exception 'Idempotency-Key deve ter entre 8 e 200 caracteres' using errcode = '22023';
  end if;
  if p_itens is null or jsonb_typeof(p_itens) <> 'array'
     or jsonb_array_length(p_itens) not between 1 and 100 then
    raise exception 'Selecione entre 1 e 100 candidatos' using errcode = '22023';
  end if;

  -- Confirmações da mesma conta são processadas uma de cada vez.
  perform pg_advisory_xact_lock(hashtextextended('importacao:' || p_ator::text, 0));

  v_hash := encode(sha256(convert_to(p_versao_id::text || p_itens::text, 'UTF8')), 'hex');

  select * into v_operacao from public.operacoes_importacao
   where user_id = p_ator and chave = p_chave;
  if found then
    if v_operacao.conteudo_hash <> v_hash then
      raise exception 'Idempotency-Key já usada com outro conteúdo' using errcode = 'AG409';
    end if;
    return jsonb_build_object('operacao_id', v_operacao.id, 'repetida', true, 'itens', (
      select coalesce(jsonb_agg(jsonb_build_object(
               'candidato_id', i.avaliacao_id, 'evento_id', i.evento_pessoal_id,
               'resultado', i.resultado, 'removido', i.evento_pessoal_id is null)), '[]'::jsonb)
        from public.itens_importacao i where i.operacao_id = v_operacao.id));
  end if;

  select * into v_versao from public.versoes_plano where id = p_versao_id;
  if not found then
    raise exception 'Versão não encontrada' using errcode = 'P0002';
  end if;
  -- Versão retirada, conta que deixou de seguir a turma ou conteúdo
  -- privado alheio: a verificação vale a cada nova ação.
  if not public.ator_pode_ler_versao(p_ator, p_versao_id) then
    raise exception 'Sem acesso a esta versão' using errcode = '42501';
  end if;
  select * into v_plano from public.planos_ensino where id = v_versao.plano_id;
  if v_plano.status <> 'concluido' then
    raise exception 'O plano ainda não terminou de ser processado' using errcode = '55000';
  end if;

  insert into public.operacoes_importacao (user_id, chave, versao_id, conteudo_hash)
  values (p_ator, p_chave, p_versao_id, v_hash)
  returning * into v_operacao;

  for v_item in select value from jsonb_array_elements(p_itens) loop
    if jsonb_typeof(v_item) <> 'object' or nullif(v_item ->> 'candidato_id', '') is null then
      raise exception 'Item inválido' using errcode = '22023';
    end if;
    v_id := (v_item ->> 'candidato_id')::uuid;
    if v_id = any (v_ids) then
      raise exception 'Não repita o mesmo candidato na confirmação' using errcode = '22023';
    end if;
    v_ids := v_ids || v_id;

    select * into v_candidato from public.avaliacoes
     where id = v_id and versao_id = p_versao_id;
    if not found then
      raise exception 'Um ou mais candidatos não pertencem a esta versão' using errcode = '22023';
    end if;
    -- O descarte é a decisão particular do autor sobre a própria versão.
    if v_candidato.status = 'descartado' and v_versao.autor_id = p_ator then
      raise exception 'Um candidato descartado não pode ser confirmado' using errcode = '22023';
    end if;

    v_titulo := btrim(coalesce(nullif(v_item ->> 'titulo', ''), v_candidato.titulo));
    if char_length(v_titulo) not between 3 and 200
       or char_length(coalesce(v_item ->> 'descricao', '')) > 10000 then
      raise exception 'Título entre 3 e 200 caracteres e descrição de até 10000' using errcode = '22023';
    end if;

    v_dia := coalesce((v_item ->> 'dia_inteiro')::boolean, false);
    v_inicio := null; v_data_ini := null; v_data_fim := null;
    if v_dia then
      v_data_ini := nullif(v_item ->> 'data_inicio', '')::date;
      v_data_fim := coalesce(nullif(v_item ->> 'data_fim', '')::date, v_data_ini + 1);
      if v_data_ini is null or v_data_fim <= v_data_ini then
        raise exception 'Dia inteiro exige data_inicio e data_fim posterior (fim exclusivo)' using errcode = '22023';
      end if;
      v_inicio := v_data_ini::timestamp at time zone 'America/Sao_Paulo';
    elsif nullif(v_item ->> 'inicio', '') is not null then
      if (v_item ->> 'inicio') !~ '(Z|[+-][0-9]{2}:?[0-9]{2})$' then
        raise exception 'Informe data e hora com fuso horário' using errcode = '22023';
      end if;
      v_inicio := (v_item ->> 'inicio')::timestamptz;
    elsif not v_candidato.ambiguo then
      v_inicio := v_candidato.data_avaliacao;
    end if;
    if v_inicio is null then
      raise exception 'Corrija a data do candidato "%" antes de confirmar', left(v_candidato.titulo, 80)
        using errcode = '22023';
    end if;

    v_categoria := null;
    if nullif(btrim(v_item ->> 'categoria'), '') is not null then
      select id into v_categoria from public.categories
       where lower(nome) = lower(btrim(v_item ->> 'categoria')) limit 1;
    end if;

    insert into public.eventos_pessoais (
      user_id, titulo, descricao, data_hora, dia_inteiro, data_inicio_civil, data_fim_civil, category_id,
      origem_plano_id, origem_avaliacao_id, origem_versao_id, origem_pagina, origem_trecho
    ) values (
      p_ator, v_titulo, coalesce(nullif(v_item ->> 'descricao', ''), v_candidato.trecho_origem),
      v_inicio, v_dia, v_data_ini, v_data_fim, v_categoria,
      v_versao.plano_id, v_candidato.id, p_versao_id, v_candidato.pagina_origem, v_candidato.trecho_origem
    )
    on conflict (user_id, origem_avaliacao_id) where origem_avaliacao_id is not null do nothing
    returning id into v_evento;

    if v_evento is not null then
      v_resultado := 'criado';
    else
      v_resultado := 'ja_importado';
      select id into v_evento from public.eventos_pessoais
       where user_id = p_ator and origem_avaliacao_id = v_candidato.id;
    end if;

    insert into public.itens_importacao (operacao_id, avaliacao_id, evento_pessoal_id, resultado)
    values (v_operacao.id, v_candidato.id, v_evento, v_resultado);

    -- Fluxo particular: o autor marca o próprio candidato como confirmado.
    -- Em versão compartilhada a decisão é de cada conta e não toca o candidato.
    if v_versao.autor_id = p_ator and v_versao.visibilidade = 'privada' and v_candidato.status = 'pendente' then
      update public.avaliacoes set status = 'confirmado' where id = v_candidato.id;
    end if;
  end loop;

  return jsonb_build_object('operacao_id', v_operacao.id, 'repetida', false, 'itens', (
    select jsonb_agg(jsonb_build_object(
             'candidato_id', i.avaliacao_id, 'evento_id', i.evento_pessoal_id,
             'resultado', i.resultado, 'removido', false))
      from public.itens_importacao i where i.operacao_id = v_operacao.id));
end;
$$;

-- -------------------------------------------------------------
-- 3. Acesso
--
-- Operações e itens são gravados pelo back-end. Pelo navegador, a
-- conta lê apenas as próprias operações.
-- -------------------------------------------------------------
alter table public.operacoes_importacao enable row level security;
alter table public.itens_importacao     enable row level security;

revoke all on public.operacoes_importacao, public.itens_importacao from anon, authenticated;
grant select on public.operacoes_importacao, public.itens_importacao to authenticated;

create policy "conta le as proprias operacoes de importacao"
  on public.operacoes_importacao for select
  to authenticated
  using (user_id = (select auth.uid()));

create policy "conta le os itens das proprias operacoes"
  on public.itens_importacao for select
  to authenticated
  using (exists (select 1 from public.operacoes_importacao o
                  where o.id = operacao_id and o.user_id = (select auth.uid())));

revoke execute on function
  public.ator_pode_ler_versao(uuid, uuid),
  public.pode_ler_versao(uuid),
  public.confirmar_importacao(uuid, text, uuid, jsonb)
  from public, anon, authenticated;

-- Usada pelas políticas de versoes_plano e avaliacoes.
grant execute on function public.pode_ler_versao(uuid) to authenticated;

grant execute on function
  public.ator_pode_ler_versao(uuid, uuid),
  public.confirmar_importacao(uuid, text, uuid, jsonb)
  to service_role;
