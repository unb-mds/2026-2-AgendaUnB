-- =============================================================
-- S7-B05 (#75) — Datas de eventos e coleta da Agenda UnB Notícias
--
--   ADR-011       datas civis, instantes e fim exclusivo
--   S7-B05 (#75)  procedência, atualização e deduplicação da coleta
--
-- Requisitos: RF12–RF16 e RNF02.
--
-- As regras que precisam valer em qualquer caminho de escrita ficam
-- no banco (chaves únicas, triggers e funções). O coletor só chama
-- registrar_evento_coletado(); a revisão usa as RPCs de moderação.
-- Nada desta migração é gravável pelo navegador.
-- =============================================================


-- -------------------------------------------------------------
-- 1. Datas (ADR-011)
--
-- Instante continua em data_evento / data_hora (timestamptz).
-- Dia inteiro é data civil: data_inicio_civil e data_fim_civil, com
-- fim EXCLUSIVO (18 a 20/11 inclusive = início 18, fim 21).
--
-- Para dia inteiro, o trigger preenche o instante de início e de fim
-- com a meia-noite de Brasília dos dias civis. Assim ordenação,
-- filtro por intervalo e lembretes funcionam do mesmo jeito para os
-- dois tipos, e leitores antigos continuam recebendo um início.
--
-- Registros antigos não são reclassificados: meia-noite em um evento
-- legado não prova dia inteiro.
-- -------------------------------------------------------------
alter table public.eventos
  add column data_fim           timestamptz,
  add column dia_inteiro        boolean not null default false,
  add column data_inicio_civil  date,
  add column data_fim_civil     date;

alter table public.eventos_pessoais
  add column data_fim           timestamptz,
  add column dia_inteiro        boolean not null default false,
  add column data_inicio_civil  date,
  add column data_fim_civil     date;

create or replace function public.tg_normaliza_datas_evento()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.dia_inteiro and new.data_inicio_civil is not null and new.data_fim_civil is not null then
    new.data_evento := new.data_inicio_civil::timestamp at time zone 'America/Sao_Paulo';
    new.data_fim    := new.data_fim_civil::timestamp at time zone 'America/Sao_Paulo';
  end if;
  return new;
end;
$$;

create or replace function public.tg_normaliza_datas_evento_pessoal()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.dia_inteiro and new.data_inicio_civil is not null and new.data_fim_civil is not null then
    new.data_hora := new.data_inicio_civil::timestamp at time zone 'America/Sao_Paulo';
    new.data_fim  := new.data_fim_civil::timestamp at time zone 'America/Sao_Paulo';
  end if;
  return new;
end;
$$;

create trigger eventos_normaliza_datas
  before insert or update on public.eventos
  for each row execute function public.tg_normaliza_datas_evento();

create trigger eventos_pessoais_normaliza_datas
  before insert or update on public.eventos_pessoais
  for each row execute function public.tg_normaliza_datas_evento_pessoal();

alter table public.eventos
  add constraint eventos_dia_inteiro_coerente check (
    (dia_inteiro and data_inicio_civil is not null and data_fim_civil is not null
       and data_fim_civil > data_inicio_civil)
    or (not dia_inteiro and data_inicio_civil is null and data_fim_civil is null)
  ),
  add constraint eventos_intervalo_valido
    check (data_fim is null or data_evento is null or data_fim > data_evento);

alter table public.eventos_pessoais
  add constraint eventos_pessoais_dia_inteiro_coerente check (
    (dia_inteiro and data_inicio_civil is not null and data_fim_civil is not null
       and data_fim_civil > data_inicio_civil)
    or (not dia_inteiro and data_inicio_civil is null and data_fim_civil is null)
  ),
  add constraint eventos_pessoais_intervalo_valido
    check (data_fim is null or data_fim > data_hora);

comment on column public.eventos.data_fim is
  'Fim exclusivo do intervalo. Nulo em registros antigos e em eventos só com início.';
comment on column public.eventos.data_fim_civil is
  'Primeiro dia civil APÓS o evento (fim exclusivo), em America/Sao_Paulo.';
comment on column public.eventos_pessoais.data_fim_civil is
  'Primeiro dia civil APÓS o compromisso (fim exclusivo), em America/Sao_Paulo.';

-- Consultas mais frequentes: catálogo por data e agenda do usuário.
create index if not exists idx_eventos_aprovados_data
  on public.eventos (data_evento)
  where status = 'aprovado';

create index if not exists idx_eventos_pessoais_usuario_data
  on public.eventos_pessoais (user_id, data_hora);


-- -------------------------------------------------------------
-- 2. Procedência da coleta (#75)
--
-- Evento coletado não tem autor na plataforma: é identificado pela
-- fonte. Um item incompleto pode aguardar revisão sem data, mas
-- nada é publicado sem data.
-- -------------------------------------------------------------
alter table public.eventos
  alter column autor_id drop not null,
  alter column data_evento drop not null,
  add column fonte                  text check (fonte in ('agenda_unb_noticias')),
  add column fonte_id               text check (char_length(btrim(fonte_id)) between 1 and 200),
  add column fonte_url              text check (char_length(fonte_url) <= 2048
                                                and fonte_url ~* '^https?://[^[:space:]<>"]+$'),
  add column fonte_tipo             text check (fonte_tipo in ('evento', 'informe')),
  add column fonte_hash             text check (char_length(fonte_hash) between 8 and 128),
  add column coletado_em            timestamptz,
  add column campos_editados        text[] not null default '{}'
                                    check (campos_editados <@ array['titulo', 'descricao', 'datas', 'local',
                                                                    'link', 'campus', 'categoria']::text[]),
  add column motivo_revisao         text check (motivo_revisao in ('incompleto', 'ambiguo',
                                                                   'possivel_duplicata', 'informe')),
  add column possivel_duplicata_de  uuid references public.eventos(id) on delete set null,
  add column moderado_por           uuid references public.profiles(id) on delete set null,
  add column moderado_em            timestamptz;

alter table public.eventos
  add constraint eventos_autor_ou_fonte
    check (autor_id is not null or fonte is not null),
  add constraint eventos_fonte_completa
    check ((fonte is null and fonte_id is null and fonte_url is null and fonte_hash is null and coletado_em is null)
           or (fonte is not null and fonte_id is not null and fonte_url is not null
               and fonte_hash is not null and coletado_em is not null)),
  add constraint eventos_publicado_tem_data
    check (status <> 'aprovado' or data_evento is not null);

-- Chave única da origem: é o que impede duplicata entre coletas
-- sucessivas ou concorrentes.
create unique index uq_eventos_fonte
  on public.eventos (fonte, fonte_id)
  where fonte is not null;

create index idx_eventos_revisao_coleta
  on public.eventos (status, coletado_em)
  where fonte is not null and status = 'pendente';

comment on column public.eventos.fonte is
  'Fonte institucional de onde o evento foi coletado. Nulo em eventos criados na plataforma.';
comment on column public.eventos.fonte_id is
  'Identificador canônico do item na fonte. Com fonte, forma a chave de upsert.';
comment on column public.eventos.fonte_hash is
  'Hash do conteúdo coletado. Igual ao anterior = nada mudou na fonte.';
comment on column public.eventos.campos_editados is
  'Campos alterados na plataforma depois da coleta. Novas coletas não os sobrescrevem.';
comment on column public.eventos.motivo_revisao is
  'Por que o item coletado aguarda revisão em vez de ser publicado automaticamente.';
comment on column public.eventos.moderado_em is
  'Quando uma pessoa decidiu sobre o evento. A coleta nunca desfaz uma decisão humana.';

-- Evento coletado (sem autor) não é sugestão de estudante: mantém o
-- status definido pela função de coleta.
create or replace function public.tg_evento_de_estudante_pendente()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_papel text;
begin
  if new.autor_id is null then
    new.sugestao_estudante := false;
  else
    select papel into v_papel from public.profiles where id = new.autor_id;
    new.sugestao_estudante := v_papel is distinct from 'professor' and v_papel is distinct from 'admin';
    if new.sugestao_estudante then
      new.status := 'pendente';
      new.justificativa_recusa := null;
    end if;
  end if;
  new.interessados_count := 0;
  return new;
end;
$$;

-- Edição local de evento coletado: registra quais campos foram
-- alterados na plataforma, por qualquer caminho, para que a próxima
-- coleta não os sobrescreva. A função de coleta sinaliza as próprias
-- escritas com a configuração de transação agenda.coleta.
create or replace function public.tg_registra_edicao_local()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
  v_campos text[] := new.campos_editados;
begin
  if new.fonte is null or coalesce(current_setting('agenda.coleta', true), '') = '1' then
    return new;
  end if;
  if new.titulo is distinct from old.titulo then v_campos := v_campos || 'titulo'::text; end if;
  if new.descricao is distinct from old.descricao then v_campos := v_campos || 'descricao'::text; end if;
  if new.data_evento is distinct from old.data_evento or new.data_fim is distinct from old.data_fim
     or new.dia_inteiro is distinct from old.dia_inteiro
     or new.data_inicio_civil is distinct from old.data_inicio_civil
     or new.data_fim_civil is distinct from old.data_fim_civil then
    v_campos := v_campos || 'datas'::text;
  end if;
  if new.localizacao is distinct from old.localizacao then v_campos := v_campos || 'local'::text; end if;
  if new.link_externo is distinct from old.link_externo then v_campos := v_campos || 'link'::text; end if;
  if new.campus_id is distinct from old.campus_id then v_campos := v_campos || 'campus'::text; end if;
  if new.category_id is distinct from old.category_id then v_campos := v_campos || 'categoria'::text; end if;
  new.campos_editados := array(select distinct c from unnest(v_campos) c order by 1);
  return new;
end;
$$;

-- Roda depois da normalização de datas (ordem alfabética dos nomes).
create trigger eventos_registra_edicao_local
  before update on public.eventos
  for each row execute function public.tg_registra_edicao_local();

-- Procedência e registro de moderação só são gravados pelo servidor
-- (função de coleta, RPC de moderação ou back-end). Uma conta que
-- escreva em eventos pelo navegador não consegue apresentar um evento
-- próprio como coletado da fonte institucional, nem alterar a origem
-- de um evento coletado.
create or replace function public.tg_protege_procedencia()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if current_user not in ('anon', 'authenticated') then
    return new;
  end if;
  if tg_op = 'INSERT' then
    if new.fonte is not null or new.fonte_id is not null or new.fonte_url is not null
       or new.fonte_tipo is not null or new.fonte_hash is not null or new.coletado_em is not null
       or new.motivo_revisao is not null or new.possivel_duplicata_de is not null
       or new.moderado_por is not null or new.moderado_em is not null
       or new.campos_editados <> '{}' then
      raise exception 'Procedência e moderação são registradas pelo servidor' using errcode = '42501';
    end if;
  elsif new.fonte is distinct from old.fonte or new.fonte_id is distinct from old.fonte_id
     or new.fonte_url is distinct from old.fonte_url or new.fonte_tipo is distinct from old.fonte_tipo
     or new.fonte_hash is distinct from old.fonte_hash or new.coletado_em is distinct from old.coletado_em
     or new.motivo_revisao is distinct from old.motivo_revisao
     or new.possivel_duplicata_de is distinct from old.possivel_duplicata_de
     or new.moderado_por is distinct from old.moderado_por or new.moderado_em is distinct from old.moderado_em
     or new.campos_editados is distinct from old.campos_editados then
    raise exception 'Procedência e moderação são registradas pelo servidor' using errcode = '42501';
  end if;
  return new;
end;
$$;

create trigger eventos_protege_procedencia
  before insert or update on public.eventos
  for each row execute function public.tg_protege_procedencia();


-- -------------------------------------------------------------
-- 3. Coleta: uma chamada por item, atômica e idempotente
--
-- O coletor (Python) lê e normaliza a fonte; esta função decide o que
-- gravar. Uso:
--
--   select public.registrar_evento_coletado(jsonb_build_object(
--     'fonte', 'agenda_unb_noticias',
--     'fonte_id', '4521',
--     'fonte_url', 'https://noticias.unb.br/component/agenda/agenda/4521',
--     'hash', '<sha256 do conteúdo normalizado>',
--     'tipo', 'evento',                      -- ou 'informe'
--     'titulo', 'Semana Universitária',
--     'descricao', '...',
--     'inicio', '2026-11-18T14:00:00-03:00', -- instante com fuso
--     'fim', '2026-11-18T16:00:00-03:00',    -- opcional, exclusivo
--     'local', 'Auditório', 'link_externo', 'https://...',
--     'campus', 'Darcy Ribeiro (Plano Piloto)', 'categoria', 'Extensão',
--     'ambiguo', false                       -- true: hora de preenchimento, data incerta
--   ));
--
-- Dia inteiro: 'dia_inteiro': true, 'data_inicio': '2026-11-18',
-- 'data_fim': '2026-11-21' (fim exclusivo), sem 'inicio'/'fim'.
--
-- Retorno: {"id", "acao", "status", "motivo_revisao"}, com acao em
-- criado | atualizado | inalterado | conciliado.
--
-- Regras:
--   - mesma (fonte, fonte_id) = mesmo registro; hash igual só renova
--     coletado_em;
--   - item completo e inequívoco é publicado; informe, item sem data,
--     ambíguo ou parecido com outro evento do mesmo dia vai à revisão;
--   - URL idêntica à de um evento criado na plataforma: o evento
--     manual é mantido e passa a carregar a procedência (conciliado);
--   - campos editados na plataforma e decisões de moderação nunca são
--     desfeitos por uma nova coleta.
-- -------------------------------------------------------------
create or replace function public.normaliza_titulo(p_titulo text)
returns text
language sql
immutable
set search_path = ''
as $$
  select btrim(regexp_replace(
    translate(lower(coalesce(p_titulo, '')),
              'áàâãäéèêëíìîïóòôõöúùûüçñ',
              'aaaaaeeeeiiiiooooouuuucn'),
    '[^a-z0-9]+', ' ', 'g'));
$$;

create or replace function public.registrar_evento_coletado(p jsonb)
returns jsonb
language plpgsql
set search_path = ''
as $$
declare
  v_fonte       text := p ->> 'fonte';
  v_fonte_id    text := nullif(btrim(p ->> 'fonte_id'), '');
  v_fonte_url   text := nullif(btrim(p ->> 'fonte_url'), '');
  v_hash        text := nullif(btrim(p ->> 'hash'), '');
  v_tipo        text := coalesce(nullif(p ->> 'tipo', ''), 'evento');
  v_titulo      text := left(btrim(coalesce(p ->> 'titulo', '')), 200);
  v_descricao   text := left(coalesce(p ->> 'descricao', ''), 10000);
  v_local       text := nullif(left(btrim(coalesce(p ->> 'local', '')), 250), '');
  v_link        text := nullif(btrim(p ->> 'link_externo'), '');
  v_dia_inteiro boolean := coalesce((p ->> 'dia_inteiro')::boolean, false);
  v_ambiguo     boolean := coalesce((p ->> 'ambiguo')::boolean, false);
  v_inicio      timestamptz;
  v_fim         timestamptz;
  v_data_inicio date;
  v_data_fim    date;
  v_campus_id   uuid;
  v_category_id uuid;
  v_motivo      text;
  v_duplicata   uuid := nullif(p ->> 'possivel_duplicata_de', '')::uuid;
  v_status      text;
  v_atual       public.eventos;
  v_id          uuid;
  v_acao        text;
  v_dia         date;
begin
  if v_fonte is null or v_fonte_id is null or v_fonte_url is null or v_hash is null then
    raise exception 'Item coletado sem fonte, identificador, URL ou hash' using errcode = '22023';
  end if;
  if v_tipo not in ('evento', 'informe') then
    raise exception 'Tipo de item inválido: %', v_tipo using errcode = '22023';
  end if;
  if char_length(v_titulo) < 3 then
    raise exception 'Item coletado sem título' using errcode = '22023';
  end if;
  -- Link fora do padrão não derruba a coleta: o item segue sem link.
  if v_link is not null and (char_length(v_link) > 2048 or v_link !~* '^https?://[^[:space:]<>"]+$') then
    v_link := null;
  end if;

  if v_dia_inteiro then
    v_data_inicio := nullif(p ->> 'data_inicio', '')::date;
    v_data_fim    := coalesce(nullif(p ->> 'data_fim', '')::date, v_data_inicio + 1);
    if v_data_inicio is null then
      v_dia_inteiro := false;
    elsif v_data_fim <= v_data_inicio then
      raise exception 'Fim do dia inteiro deve ser posterior ao início (fim exclusivo)' using errcode = '22023';
    else
      v_inicio := v_data_inicio::timestamp at time zone 'America/Sao_Paulo';
    end if;
  else
    -- Sem deslocamento explícito o banco assumiria UTC e o evento sairia 3 h adiantado.
    if coalesce(p ->> 'inicio', '') || coalesce(p ->> 'fim', '') <> ''
       and (coalesce(nullif(p ->> 'inicio', ''), '2000-01-01T00:00:00Z') !~ '(Z|[+-][0-9]{2}:?[0-9]{2})$'
            or coalesce(nullif(p ->> 'fim', ''), '2000-01-01T00:00:00Z') !~ '(Z|[+-][0-9]{2}:?[0-9]{2})$') then
      raise exception 'inicio e fim devem trazer o fuso (ex.: 2026-11-18T14:00:00-03:00)' using errcode = '22023';
    end if;
    v_inicio := nullif(p ->> 'inicio', '')::timestamptz;
    v_fim    := nullif(p ->> 'fim', '')::timestamptz;
    if v_fim is not null and (v_inicio is null or v_fim <= v_inicio) then
      v_fim := null;  -- fim incoerente é descartado; o item vai à revisão como ambíguo
      v_ambiguo := true;
    end if;
  end if;

  select id into v_campus_id from public.campus
   where lower(nome) = lower(btrim(coalesce(p ->> 'campus', ''))) limit 1;
  select id into v_category_id from public.categories
   where lower(nome) = lower(btrim(coalesce(p ->> 'categoria', ''))) limit 1;

  v_motivo := case
    when v_tipo = 'informe' then 'informe'
    when v_inicio is null   then 'incompleto'
    when v_ambiguo          then 'ambiguo'
  end;

  -- Serializa coletas concorrentes do mesmo item.
  perform pg_advisory_xact_lock(hashtextextended(v_fonte || ':' || v_fonte_id, 0));
  perform set_config('agenda.coleta', '1', true);

  select * into v_atual from public.eventos
   where fonte = v_fonte and fonte_id = v_fonte_id
   for update;

  if not found then
    -- Mesma URL já cadastrada manualmente: conciliar em vez de duplicar.
    select id into v_id from public.eventos
     where fonte is null
       and rtrim(link_externo, '/') in (rtrim(v_fonte_url, '/'), rtrim(coalesce(v_link, v_fonte_url), '/'))
     order by criado_em
     limit 1
     for update;

    if found then
      update public.eventos
         set fonte = v_fonte, fonte_id = v_fonte_id, fonte_url = v_fonte_url, fonte_tipo = v_tipo,
             fonte_hash = v_hash, coletado_em = now(),
             -- O conteúdo manual prevalece: todos os campos ficam protegidos.
             campos_editados = array['campus', 'categoria', 'datas', 'descricao', 'link', 'local', 'titulo']
       where id = v_id;
      perform set_config('agenda.coleta', '', true);
      return jsonb_build_object('id', v_id, 'acao', 'conciliado',
        'status', (select status from public.eventos where id = v_id), 'motivo_revisao', null);
    end if;

    -- Título igual no mesmo dia: provável duplicata, decide uma pessoa.
    if v_motivo is null and v_duplicata is null then
      v_dia := (v_inicio at time zone 'America/Sao_Paulo')::date;
      select id into v_duplicata from public.eventos e
       where e.status in ('aprovado', 'pendente')
         and e.data_evento is not null
         and (e.data_evento at time zone 'America/Sao_Paulo')::date = v_dia
         and public.normaliza_titulo(e.titulo) = public.normaliza_titulo(v_titulo)
       order by e.criado_em
       limit 1;
    end if;
    if v_motivo is null and v_duplicata is not null then
      v_motivo := 'possivel_duplicata';
    end if;

    v_status := case when v_motivo is null then 'aprovado' else 'pendente' end;

    insert into public.eventos (
      autor_id, titulo, descricao, data_evento, data_fim, dia_inteiro, data_inicio_civil, data_fim_civil,
      localizacao, link_externo, campus_id, category_id, status,
      fonte, fonte_id, fonte_url, fonte_tipo, fonte_hash, coletado_em, motivo_revisao, possivel_duplicata_de
    ) values (
      null, v_titulo, v_descricao, v_inicio, v_fim, v_dia_inteiro,
      case when v_dia_inteiro then v_data_inicio end, case when v_dia_inteiro then v_data_fim end,
      v_local, coalesce(v_link, v_fonte_url), v_campus_id, v_category_id, v_status,
      v_fonte, v_fonte_id, v_fonte_url, v_tipo, v_hash, now(), v_motivo, v_duplicata
    )
    returning id into v_id;

    perform set_config('agenda.coleta', '', true);
    return jsonb_build_object('id', v_id, 'acao', 'criado', 'status', v_status, 'motivo_revisao', v_motivo);
  end if;

  -- Já coletado antes.
  if v_atual.fonte_hash = v_hash then
    update public.eventos set coletado_em = now() where id = v_atual.id;
    perform set_config('agenda.coleta', '', true);
    return jsonb_build_object('id', v_atual.id, 'acao', 'inalterado',
      'status', v_atual.status, 'motivo_revisao', v_atual.motivo_revisao);
  end if;

  -- Datas editadas na plataforma são mantidas. Se a fonte deixou de informar
  -- a data (página alterada ou leitura parcial), a data conhecida também é
  -- mantida e o evento não é rebaixado por isso.
  if 'datas' = any (v_atual.campos_editados) or (v_inicio is null and v_atual.data_evento is not null) then
    v_inicio      := v_atual.data_evento;
    v_fim         := v_atual.data_fim;
    v_dia_inteiro := v_atual.dia_inteiro;
    v_data_inicio := v_atual.data_inicio_civil;
    v_data_fim    := v_atual.data_fim_civil;
    if v_motivo in ('incompleto', 'ambiguo') then
      v_motivo := case when v_inicio is null then 'incompleto' end;
    end if;
  end if;

  -- Decisão humana e suspeita de duplicata não são desfeitas pela coleta.
  if v_atual.moderado_em is not null then
    v_status := v_atual.status;
    v_motivo := v_atual.motivo_revisao;
  elsif v_atual.motivo_revisao = 'possivel_duplicata' then
    v_status := 'pendente';
    v_motivo := 'possivel_duplicata';
  else
    v_status := case when v_motivo is null then 'aprovado' else 'pendente' end;
  end if;

  update public.eventos
     set titulo            = case when 'titulo' = any (campos_editados) then titulo else v_titulo end,
         descricao         = case when 'descricao' = any (campos_editados) then descricao else v_descricao end,
         data_evento       = v_inicio,
         data_fim          = v_fim,
         dia_inteiro       = v_dia_inteiro,
         data_inicio_civil = case when v_dia_inteiro then v_data_inicio end,
         data_fim_civil    = case when v_dia_inteiro then v_data_fim end,
         localizacao       = case when 'local' = any (campos_editados) then localizacao else v_local end,
         link_externo      = case when 'link' = any (campos_editados) then link_externo
                                  else coalesce(v_link, v_fonte_url) end,
         campus_id         = case when 'campus' = any (campos_editados) then campus_id
                                  else coalesce(v_campus_id, campus_id) end,
         category_id       = case when 'categoria' = any (campos_editados) then category_id
                                  else coalesce(v_category_id, category_id) end,
         status            = v_status,
         motivo_revisao    = v_motivo,
         fonte_url         = v_fonte_url,
         fonte_tipo        = v_tipo,
         fonte_hash        = v_hash,
         coletado_em       = now()
   where id = v_atual.id;

  perform set_config('agenda.coleta', '', true);
  return jsonb_build_object('id', v_atual.id, 'acao', 'atualizado', 'status', v_status, 'motivo_revisao', v_motivo);
end;
$$;

-- Registro de cada execução do coletor: evidência de execução
-- agendada e base para acompanhar falhas da fonte.
create table public.coletas_eventos (
  id              uuid primary key default gen_random_uuid(),
  fonte           text not null check (fonte in ('agenda_unb_noticias')),
  status          text not null default 'executando'
                  check (status in ('executando', 'concluida', 'falha')),
  iniciada_em     timestamptz not null default now(),
  concluida_em    timestamptz,
  itens_lidos     integer not null default 0 check (itens_lidos >= 0),
  criados         integer not null default 0 check (criados >= 0),
  atualizados     integer not null default 0 check (atualizados >= 0),
  inalterados     integer not null default 0 check (inalterados >= 0),
  conciliados     integer not null default 0 check (conciliados >= 0),
  para_revisao    integer not null default 0 check (para_revisao >= 0),
  erro_codigo     text check (erro_codigo is null or char_length(erro_codigo) <= 60),
  constraint coletas_conclusao_coerente
    check ((status = 'executando') = (concluida_em is null)),
  constraint coletas_erro_apenas_em_falha
    check (erro_codigo is null or status = 'falha')
);

create index idx_coletas_eventos_fonte on public.coletas_eventos (fonte, iniciada_em desc);

comment on table public.coletas_eventos is
  'Uma linha por execução do coletor. erro_codigo guarda só um código curto (ex.: http_503, timeout), nunca HTML ou conteúdo da fonte.';

-- Moderação: a mesma RPC decide sugestões de estudantes e itens
-- coletados que aguardam revisão, e registra quem decidiu.
create or replace function public.moderar_sugestao(p_evento_id uuid, p_status text, p_justificativa text default null)
returns void language plpgsql security definer set search_path = '' as $$
begin
  if not public.is_event_moderator() then
    raise exception 'Apenas professores e administradores' using errcode = '42501';
  end if;
  if p_status is null or p_status not in ('aprovado', 'rejeitado') then
    raise exception 'Decisão inválida' using errcode = '22023';
  end if;
  if p_status = 'rejeitado' and (nullif(btrim(p_justificativa), '') is null or char_length(btrim(p_justificativa)) > 2000) then
    raise exception 'Informe uma justificativa de até 2000 caracteres' using errcode = '22023';
  end if;
  if p_status = 'aprovado' and exists (
       select 1 from public.eventos where id = p_evento_id and data_evento is null) then
    raise exception 'Informe a data do evento antes de publicar' using errcode = '22023';
  end if;
  update public.eventos set status = p_status,
    justificativa_recusa = case when p_status = 'rejeitado' then btrim(p_justificativa) else null end,
    moderado_por = (select auth.uid()), moderado_em = now()
    where id = p_evento_id and status = 'pendente' and (sugestao_estudante or fonte is not null);
  if not found then
    raise exception 'Esta sugestão já foi analisada ou não está disponível. Atualize a lista.' using errcode = 'P0002';
  end if;
end;
$$;

-- Fila de revisão dos itens coletados, para professor e admin.
create or replace function public.listar_revisoes_coleta(p_status text default 'pendente', p_offset integer default 0)
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare resultado jsonb;
begin
  if not public.is_event_moderator() then
    raise exception 'Apenas professores e administradores' using errcode = '42501';
  end if;
  if p_status is null or p_status not in ('pendente', 'aprovado', 'rejeitado') or p_offset is null or p_offset < 0 then
    raise exception 'Filtro inválido' using errcode = '22023';
  end if;
  with filtrados as (
    select e.id, e.titulo, e.descricao, e.data_evento, e.data_fim, e.dia_inteiro,
      e.data_inicio_civil, e.data_fim_civil, e.localizacao, e.link_externo, e.status,
      e.justificativa_recusa, e.fonte, e.fonte_url, e.fonte_tipo, e.coletado_em,
      e.motivo_revisao, e.possivel_duplicata_de, c.nome as campus, cat.nome as categoria
    from public.eventos e
    left join public.campus c on c.id = e.campus_id
    left join public.categories cat on cat.id = e.category_id
    where e.fonte is not null and e.autor_id is null and e.status = p_status
      and (p_status <> 'aprovado' or e.moderado_em is not null)
  ), pagina as (select * from filtrados order by coletado_em, id limit 20 offset p_offset)
  select jsonb_build_object('items', coalesce((select jsonb_agg(to_jsonb(pagina)) from pagina), '[]'::jsonb),
    'total', (select count(*) from filtrados)) into resultado;
  return resultado;
end;
$$;

-- -------------------------------------------------------------
-- 4. Acesso
--
-- O coletor roda com a credencial do servidor. Professor e admin
-- revisam pelas RPCs; o restante não é acessível pelo navegador.
-- -------------------------------------------------------------
alter table public.coletas_eventos enable row level security;

revoke all on public.coletas_eventos from anon, authenticated;

revoke execute on function
  public.tg_normaliza_datas_evento(),
  public.tg_normaliza_datas_evento_pessoal(),
  public.tg_registra_edicao_local(),
  public.tg_protege_procedencia(),
  public.tg_evento_de_estudante_pendente(),
  public.normaliza_titulo(text),
  public.registrar_evento_coletado(jsonb),
  public.listar_revisoes_coleta(text, integer),
  public.moderar_sugestao(uuid, text, text)
  from public, anon, authenticated;

grant execute on function public.moderar_sugestao(uuid, text, text) to authenticated;
grant execute on function public.listar_revisoes_coleta(text, integer) to authenticated;
grant execute on function public.registrar_evento_coletado(jsonb) to service_role;
