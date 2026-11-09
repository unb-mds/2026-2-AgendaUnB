-- =============================================================
-- Dados de planos da Release 2
--
--   S7-B04 (#72)  confirmação idempotente por ação, por usuário
--   S8-B01 (#77)  compartilhamento, revisões, procedência e votos
--   S7-B03 (#70)  sincronização do catálogo de turmas
--   ADR-009 e ADR-010
--
-- Requisitos: RF05, RF06, RF07, RF09, RNF02, RNF04 e RNF11.
--
-- O back-end conecta com um usuário que ignora RLS, então as regras
-- de quem pode publicar, revisar, votar e importar ficam em funções
-- que recebem o ator (id da conta validada pela API) e conferem a
-- permissão no banco. Nenhuma delas é chamável pelo navegador.
--
-- Códigos de erro, para a API traduzir:
--   42501 -> 403   sem permissão sobre a versão
--   P0002 -> 404   versão, candidato ou plano inexistente
--   22023 -> 422   dados inválidos (inclui data ambígua sem correção)
--   55000 -> 409   estado não permite a ação
--   AG409 -> 409   Idempotency-Key reutilizada com outro conteúdo
-- =============================================================


-- -------------------------------------------------------------
-- 1. Versões: procedência institucional e retirada
-- -------------------------------------------------------------
alter table public.versoes_plano
  add column fonte_institucional_url   text
    check (fonte_institucional_url is null
           or (char_length(fonte_institucional_url) <= 2048
               and fonte_institucional_url ~* '^https?://[^[:space:]<>"]+$')),
  add column procedencia_validada_por  uuid references public.profiles(id) on delete set null,
  add column procedencia_validada_em   timestamptz,
  add column retirada_em               timestamptz,
  add column retirada_por              uuid references public.profiles(id) on delete set null;

alter table public.versoes_plano
  add constraint versoes_plano_procedencia_tem_evidencia
    check (not procedencia_institucional
           or (fonte_institucional_url is not null and procedencia_validada_em is not null));

create index idx_versoes_plano_origem
  on public.versoes_plano (versao_origem_id)
  where versao_origem_id is not null;

create index idx_versoes_plano_autor on public.versoes_plano (autor_id);

comment on column public.versoes_plano.fonte_institucional_url is
  'Evidência pública oficial da origem institucional. Só um admin a valida; revisões de professor/admin a herdam.';
comment on column public.versoes_plano.retirada_em is
  'Quando o compartilhamento foi retirado pela última vez. Revisões e cópias já importadas permanecem.';


-- -------------------------------------------------------------
-- 2. Quem lê uma versão
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

-- A leitura de candidatos passa a depender só da versão.
drop policy if exists "dono do plano consulta candidatos" on public.avaliacoes;


-- -------------------------------------------------------------
-- 3. Conteúdo compartilhado não muda de lugar
--
-- Votos e importações referem-se a um candidato de uma versão. Se o
-- texto ou a data de um candidato compartilhado pudesse ser editado,
-- o voto de ontem passaria a apoiar outra data. Corrigir conteúdo
-- compartilhado é criar uma revisão (criar_revisao).
--
-- O status do candidato continua editável: é a decisão particular
-- do autor no fluxo privado.
-- -------------------------------------------------------------
create or replace function public.tg_avaliacao_compartilhada_imutavel()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_visibilidade text;
begin
  select visibilidade into v_visibilidade
    from public.versoes_plano where id = old.versao_id;
  -- Versão já removida (exclusão em cascata da versão ou da conta).
  if not found or v_visibilidade <> 'compartilhada' then
    return coalesce(new, old);
  end if;
  if tg_op = 'DELETE' then
    -- Exclusão do plano inteiro: os candidatos saem antes das versões.
    if not exists (select 1 from public.planos_ensino where id = old.plano_id) then
      return old;
    end if;
    raise exception 'Candidato de versão compartilhada não pode ser excluído; retire o compartilhamento ou crie uma revisão'
      using errcode = '55000';
  end if;
  if new.titulo is distinct from old.titulo
     or new.data_avaliacao is distinct from old.data_avaliacao
     or new.tipo is distinct from old.tipo
     or new.ambiguo is distinct from old.ambiguo
     or new.pagina_origem is distinct from old.pagina_origem
     or new.trecho_origem is distinct from old.trecho_origem
     or new.ordem is distinct from old.ordem
     or new.versao_id is distinct from old.versao_id
     or new.plano_id is distinct from old.plano_id then
    raise exception 'Conteúdo compartilhado não é editado: crie uma revisão'
      using errcode = '55000';
  end if;
  return new;
end;
$$;

create trigger avaliacoes_compartilhada_imutavel
  before update or delete on public.avaliacoes
  for each row execute function public.tg_avaliacao_compartilhada_imutavel();

-- Candidato novo também não entra em versão já compartilhada.
create or replace function public.tg_avaliacao_nao_entra_em_compartilhada()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if exists (select 1 from public.versoes_plano
              where id = new.versao_id and visibilidade = 'compartilhada') then
    raise exception 'Versão compartilhada não recebe novos candidatos: crie uma revisão'
      using errcode = '55000';
  end if;
  return new;
end;
$$;

-- "zz": roda depois de avaliacoes_versao_padrao, que preenche versao_id.
create trigger avaliacoes_zz_nao_entra_em_compartilhada
  before insert on public.avaliacoes
  for each row execute function public.tg_avaliacao_nao_entra_em_compartilhada();


-- -------------------------------------------------------------
-- 4. Compartilhar, retirar, revisar e validar procedência (#77)
-- -------------------------------------------------------------
create or replace function public.compartilhar_versao(p_ator uuid, p_versao_id uuid)
returns public.versoes_plano
language plpgsql
set search_path = ''
as $$
declare
  v public.versoes_plano;
  v_plano public.planos_ensino;
begin
  select * into v from public.versoes_plano where id = p_versao_id for update;
  if not found then
    raise exception 'Versão não encontrada' using errcode = 'P0002';
  end if;
  -- Só o autor publica o que escreveu. Papel nenhum publica material alheio.
  if p_ator is null or v.autor_id <> p_ator then
    raise exception 'Apenas o autor compartilha a versão' using errcode = '42501';
  end if;
  if v.visibilidade = 'compartilhada' then
    return v;
  end if;
  select * into v_plano from public.planos_ensino where id = v.plano_id;
  if v_plano.oferta_id is null then
    raise exception 'Associe o plano a uma turma antes de compartilhar' using errcode = '55000';
  end if;
  if v_plano.status <> 'concluido' then
    raise exception 'O plano ainda não terminou de ser processado' using errcode = '55000';
  end if;
  update public.versoes_plano
     set visibilidade = 'compartilhada', compartilhada_em = now()
   where id = p_versao_id
  returning * into v;
  return v;
end;
$$;

create or replace function public.retirar_compartilhamento(p_ator uuid, p_versao_id uuid)
returns public.versoes_plano
language plpgsql
set search_path = ''
as $$
declare
  v public.versoes_plano;
begin
  select * into v from public.versoes_plano where id = p_versao_id for update;
  if not found then
    raise exception 'Versão não encontrada' using errcode = 'P0002';
  end if;
  if p_ator is null or (v.autor_id <> p_ator and not exists (
       select 1 from public.profiles where id = p_ator and papel = 'admin')) then
    raise exception 'Apenas o autor ou um administrador retira o compartilhamento' using errcode = '42501';
  end if;
  if v.visibilidade = 'privada' then
    return v;
  end if;
  -- Revisões desta versão e eventos já importados não são tocados.
  update public.versoes_plano
     set visibilidade = 'privada', compartilhada_em = null,
         retirada_em = now(), retirada_por = p_ator
   where id = p_versao_id
  returning * into v;
  return v;
end;
$$;

-- Nova versão a partir de outra, com os candidatos copiados. Nasce
-- privada, para o autor da revisão ajustar e então compartilhar.
--   - o autor revisa as próprias versões, privadas ou compartilhadas;
--   - professor e admin revisam versões compartilhadas;
--   - a procedência institucional só é herdada por professor/admin.
create or replace function public.criar_revisao(p_ator uuid, p_versao_origem_id uuid)
returns public.versoes_plano
language plpgsql
set search_path = ''
as $$
declare
  v_origem public.versoes_plano;
  v_papel  text;
  v_nova   public.versoes_plano;
  v_herda  boolean;
begin
  select papel into v_papel from public.profiles where id = p_ator;
  if not found then
    raise exception 'Conta não encontrada' using errcode = '42501';
  end if;
  select * into v_origem from public.versoes_plano where id = p_versao_origem_id;
  if not found then
    raise exception 'Versão não encontrada' using errcode = 'P0002';
  end if;
  if v_origem.autor_id <> p_ator
     and not (v_origem.visibilidade = 'compartilhada' and v_papel in ('professor', 'admin')) then
    raise exception 'Sem permissão para revisar esta versão' using errcode = '42501';
  end if;

  -- Serializa a numeração das versões do plano.
  perform 1 from public.planos_ensino where id = v_origem.plano_id for update;

  v_herda := v_origem.procedencia_institucional and v_papel in ('professor', 'admin');

  insert into public.versoes_plano (
    plano_id, numero, autor_id, autor_papel, versao_origem_id,
    procedencia_institucional, fonte_institucional_url, procedencia_validada_por, procedencia_validada_em
  )
  select v_origem.plano_id,
         (select max(numero) + 1 from public.versoes_plano where plano_id = v_origem.plano_id),
         p_ator, v_papel, v_origem.id,
         v_herda,
         case when v_herda then v_origem.fonte_institucional_url end,
         case when v_herda then v_origem.procedencia_validada_por end,
         case when v_herda then v_origem.procedencia_validada_em end
  returning * into v_nova;

  insert into public.avaliacoes (
    plano_id, versao_id, ordem, titulo, data_avaliacao, tipo, ambiguo,
    pagina_origem, trecho_origem, status, versao_processamento, provedor
  )
  select a.plano_id, v_nova.id, a.ordem, a.titulo, a.data_avaliacao, a.tipo, a.ambiguo,
         a.pagina_origem, a.trecho_origem, 'pendente', a.versao_processamento, a.provedor
    from public.avaliacoes a
   where a.versao_id = v_origem.id
     and a.status <> 'descartado'
   order by a.ordem nulls last, a.criado_em, a.id;

  return v_nova;
end;
$$;

-- Atribuição inicial da origem institucional: evidência pública
-- oficial, validada por admin. Papel de professor, voto e vínculo
-- autodeclarado não contam como evidência.
create or replace function public.validar_procedencia_institucional(
  p_ator uuid, p_versao_id uuid, p_url text
)
returns public.versoes_plano
language plpgsql
set search_path = ''
as $$
declare
  v public.versoes_plano;
begin
  if not exists (select 1 from public.profiles where id = p_ator and papel = 'admin') then
    raise exception 'Apenas administradores validam a origem institucional' using errcode = '42501';
  end if;
  if p_url is null or char_length(p_url) > 2048 or p_url !~* '^https?://[^[:space:]<>"]+$' then
    raise exception 'Informe a URL pública oficial da evidência' using errcode = '22023';
  end if;
  update public.versoes_plano
     set procedencia_institucional = true, fonte_institucional_url = btrim(p_url),
         procedencia_validada_por = p_ator, procedencia_validada_em = now()
   where id = p_versao_id and visibilidade = 'compartilhada'
  returning * into v;
  if not found then
    raise exception 'Versão compartilhada não encontrada' using errcode = 'P0002';
  end if;
  return v;
end;
$$;


-- -------------------------------------------------------------
-- 5. Votos (#77)
--
-- Um voto por conta e candidato (o candidato pertence a uma única
-- versão). Votar de novo troca o próprio voto; não soma outro.
-- O voto de cada pessoa é privado: a API expõe apenas contagens.
-- Votos nunca alteram datas.
-- -------------------------------------------------------------
create table public.votos_avaliacao (
  user_id        uuid not null references public.profiles(id) on delete cascade,
  avaliacao_id   uuid not null references public.avaliacoes(id) on delete cascade,
  valor          text not null check (valor in ('confirma', 'contesta')),
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),
  primary key (user_id, avaliacao_id)
);

create index idx_votos_avaliacao_candidato on public.votos_avaliacao (avaliacao_id, valor);

comment on table public.votos_avaliacao is
  'Voto de um seguidor sobre um candidato de versão compartilhada. Não é prova e não altera datas.';

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
  select a.versao_id into v_versao
    from public.avaliacoes a
    join public.versoes_plano v on v.id = a.versao_id
   where a.id = p_avaliacao_id and v.visibilidade = 'compartilhada';
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
     group by a.id, a.ordem
     order by a.ordem nulls last, a.id;
end;
$$;


-- -------------------------------------------------------------
-- 6. Confirmação idempotente por ação (#72, ADR-010)
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
-- 7. Sincronização do catálogo de turmas (#70, ADR-009)
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
-- 8. Acesso
--
-- Tudo aqui é escrito pelo back-end. Pelo navegador, a conta lê
-- apenas os próprios votos e as próprias operações.
-- -------------------------------------------------------------
alter table public.votos_avaliacao         enable row level security;
alter table public.operacoes_importacao    enable row level security;
alter table public.itens_importacao        enable row level security;
alter table public.sincronizacoes_catalogo enable row level security;

revoke all on public.votos_avaliacao, public.operacoes_importacao,
              public.itens_importacao, public.sincronizacoes_catalogo
  from anon, authenticated;

grant select on public.votos_avaliacao, public.operacoes_importacao, public.itens_importacao to authenticated;

create policy "conta le os proprios votos"
  on public.votos_avaliacao for select
  to authenticated
  using (user_id = (select auth.uid()));

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
  public.tg_avaliacao_compartilhada_imutavel(),
  public.tg_avaliacao_nao_entra_em_compartilhada(),
  public.compartilhar_versao(uuid, uuid),
  public.retirar_compartilhamento(uuid, uuid),
  public.criar_revisao(uuid, uuid),
  public.validar_procedencia_institucional(uuid, uuid, text),
  public.votar_avaliacao(uuid, uuid, text),
  public.resumo_votos_versao(uuid, uuid),
  public.confirmar_importacao(uuid, text, uuid, jsonb),
  public.registrar_oferta_catalogo(jsonb),
  public.estado_catalogo(text, interval)
  from public, anon, authenticated;

-- Usada pelas políticas de versoes_plano e avaliacoes.
grant execute on function public.pode_ler_versao(uuid) to authenticated;

grant execute on function
  public.ator_pode_ler_versao(uuid, uuid),
  public.compartilhar_versao(uuid, uuid),
  public.retirar_compartilhamento(uuid, uuid),
  public.criar_revisao(uuid, uuid),
  public.validar_procedencia_institucional(uuid, uuid, text),
  public.votar_avaliacao(uuid, uuid, text),
  public.resumo_votos_versao(uuid, uuid),
  public.confirmar_importacao(uuid, text, uuid, jsonb),
  public.registrar_oferta_catalogo(jsonb),
  public.estado_catalogo(text, interval)
  to service_role;
