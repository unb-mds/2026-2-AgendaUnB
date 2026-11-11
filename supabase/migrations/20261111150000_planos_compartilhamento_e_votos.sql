-- =============================================================
-- S8-B01 (#77) — Compartilhamento, revisões, procedência e votos
--
--   S8-B01 (#77)  compartilhar, retirar, revisar, validar procedência
--                 institucional e votar
--   ADR-010
--
-- Requisitos: RF05, RF06, RNF02 e RNF04.
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
-- 2. Conteúdo compartilhado não muda de lugar
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
-- 3. Compartilhar, retirar, revisar e validar procedência (#77)
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
-- 4. Votos (#77)
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
-- 5. Acesso
--
-- Tudo aqui é escrito pelo back-end. Pelo navegador, a conta lê
-- apenas os próprios votos.
-- -------------------------------------------------------------
alter table public.votos_avaliacao enable row level security;

revoke all on public.votos_avaliacao from anon, authenticated;
grant select on public.votos_avaliacao to authenticated;

create policy "conta le os proprios votos"
  on public.votos_avaliacao for select
  to authenticated
  using (user_id = (select auth.uid()));

revoke execute on function
  public.tg_avaliacao_compartilhada_imutavel(),
  public.tg_avaliacao_nao_entra_em_compartilhada(),
  public.compartilhar_versao(uuid, uuid),
  public.retirar_compartilhamento(uuid, uuid),
  public.criar_revisao(uuid, uuid),
  public.validar_procedencia_institucional(uuid, uuid, text),
  public.votar_avaliacao(uuid, uuid, text),
  public.resumo_votos_versao(uuid, uuid)
  from public, anon, authenticated;

grant execute on function
  public.compartilhar_versao(uuid, uuid),
  public.retirar_compartilhamento(uuid, uuid),
  public.criar_revisao(uuid, uuid),
  public.validar_procedencia_institucional(uuid, uuid, text),
  public.votar_avaliacao(uuid, uuid, text),
  public.resumo_votos_versao(uuid, uuid)
  to service_role;
