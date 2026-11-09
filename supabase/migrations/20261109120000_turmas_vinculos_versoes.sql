-- =============================================================
-- S7-D01 (#69) — Turmas, vínculos, versões e isolamento dos planos
--
-- Requisitos: RF05, RF07, RNF02 e RNF04.
--
-- Modelo:
--   disciplinas      disciplina abstrata (código e nome)
--   ofertas_turma    a disciplina num semestre: turma + ano + semestre
--   vinculos_turma   usuário segue uma oferta (vínculo autodeclarado)
--   versoes_plano    versões de um plano, privadas por padrão
--   avaliacoes       candidatos extraídos, agora ligados à versão
--
-- Decisões registradas com a equipe:
--   - avaliacoes é a tabela oficial de candidatos; candidatos_avaliacao
--     (#53) não é usada pelo código e é removida aqui;
--   - escrita nessas tabelas passa pelo back-end, como planos desde
--     20261107000000. O navegador só lê, conforme as políticas abaixo;
--   - o PDF e o registro do plano continuam visíveis só ao dono. Uma
--     versão compartilhada expõe apenas a versão e seus candidatos a
--     quem segue a mesma oferta. Compartilhar o PDF é tema da S8-B01.
--
-- Dados existentes são preservados: cada plano ganha a versão 1, e
-- seus candidatos e eventos importados passam a apontar para ela.
-- =============================================================


-- -------------------------------------------------------------
-- 1. Disciplinas e ofertas (catálogo)
--
-- Identidade canônica, como pedido na issue:
--   - com o identificador da origem (Followw): ele identifica;
--   - sem ele: código + unidade + nível identificam a disciplina,
--     e disciplina + turma + período identificam a oferta.
-- Semestre segue o contrato da API (1 ou 2).
-- -------------------------------------------------------------
create table public.disciplinas (
  id                        uuid primary key default gen_random_uuid(),
  origem                    text not null default 'followw'
                            check (origem in ('followw', 'manual')),
  origem_id                 text check (origem_id is null or char_length(btrim(origem_id)) between 1 and 100),
  codigo                    text not null check (char_length(btrim(codigo)) between 1 and 30),
  nome                      text not null check (char_length(btrim(nome)) between 1 and 300),
  unidade                   text check (unidade is null or char_length(btrim(unidade)) between 1 and 120),
  nivel                     text check (nivel is null or char_length(btrim(nivel)) between 1 and 60),
  atualizado_na_origem_em   timestamptz,
  criado_em                 timestamptz not null default now(),
  atualizado_em             timestamptz not null default now()
);

create unique index uq_disciplinas_origem_id
  on public.disciplinas (origem, origem_id)
  where origem_id is not null;

create unique index uq_disciplinas_codigo
  on public.disciplinas (origem, upper(btrim(codigo)), coalesce(unidade, ''), coalesce(nivel, ''))
  where origem_id is null;

create table public.ofertas_turma (
  id                        uuid primary key default gen_random_uuid(),
  disciplina_id             uuid not null references public.disciplinas(id) on delete restrict,
  origem                    text not null default 'followw'
                            check (origem in ('followw', 'manual')),
  origem_id                 text check (origem_id is null or char_length(btrim(origem_id)) between 1 and 100),
  turma                     text not null check (char_length(btrim(turma)) between 1 and 20),
  ano                       smallint not null check (ano between 2000 and 2100),
  semestre                  smallint not null check (semestre in (1, 2)),
  atualizado_na_origem_em   timestamptz,
  sincronizado_em           timestamptz,
  criado_em                 timestamptz not null default now(),
  atualizado_em             timestamptz not null default now(),

  constraint ofertas_turma_identidade unique (disciplina_id, turma, ano, semestre)
);

create unique index uq_ofertas_turma_origem_id
  on public.ofertas_turma (origem, origem_id)
  where origem_id is not null;

create index idx_ofertas_turma_periodo
  on public.ofertas_turma (ano, semestre, disciplina_id);

create trigger disciplinas_atualiza_timestamp
  before update on public.disciplinas
  for each row execute function public.tg_atualiza_timestamp();

create trigger ofertas_turma_atualiza_timestamp
  before update on public.ofertas_turma
  for each row execute function public.tg_atualiza_timestamp();

comment on table public.disciplinas is
  'Disciplina abstrata do catálogo público. Não confundir com a oferta em um semestre.';
comment on table public.ofertas_turma is
  'Oferta de uma disciplina em um período (turma + ano + semestre). Ofertas de semestres diferentes são registros distintos.';
comment on column public.ofertas_turma.sincronizado_em is
  'Última sincronização bem-sucedida com a origem. Permite avisar catálogo desatualizado.';


-- -------------------------------------------------------------
-- 2. Vínculo usuário ↔ oferta
--
-- A chave primária garante que seguir a mesma oferta de novo não
-- duplica o vínculo. O vínculo é autodeclarado.
-- -------------------------------------------------------------
create table public.vinculos_turma (
  user_id    uuid not null references public.profiles(id) on delete cascade,
  oferta_id  uuid not null references public.ofertas_turma(id) on delete restrict,
  origem     text not null default 'autodeclarado' check (origem in ('autodeclarado')),
  criado_em  timestamptz not null default now(),
  primary key (user_id, oferta_id)
);

create index idx_vinculos_turma_oferta on public.vinculos_turma (oferta_id);

comment on table public.vinculos_turma is
  'Turmas que o usuário segue. Vínculo autodeclarado, sem comprovação de matrícula.';


-- -------------------------------------------------------------
-- 3. Plano ligado à oferta
--
-- Opcional: planos antigos e envios sem turma continuam válidos.
-- -------------------------------------------------------------
alter table public.planos_ensino
  add column oferta_id uuid references public.ofertas_turma(id) on delete set null;

create index idx_planos_ensino_oferta
  on public.planos_ensino (oferta_id)
  where oferta_id is not null;


-- -------------------------------------------------------------
-- 4. Versões do plano
--
-- Toda versão nasce privada. Compartilhar exige registrar quando.
-- (plano_id, numero) é único e (plano_id, id) permite que os
-- candidatos referenciem uma versão do próprio plano.
-- -------------------------------------------------------------
create table public.versoes_plano (
  id                uuid primary key default gen_random_uuid(),
  plano_id          uuid not null references public.planos_ensino(id) on delete cascade,
  numero            smallint not null check (numero >= 1),
  autor_id          uuid not null references public.profiles(id) on delete cascade,
  visibilidade      text not null default 'privada'
                    check (visibilidade in ('privada', 'compartilhada')),
  compartilhada_em  timestamptz,
  criado_em         timestamptz not null default now(),

  constraint versoes_plano_numero_unico unique (plano_id, numero),
  constraint versoes_plano_do_plano unique (plano_id, id),
  constraint versoes_plano_compartilhamento
    check ((visibilidade = 'compartilhada') = (compartilhada_em is not null))
);

create index idx_versoes_plano_compartilhadas
  on public.versoes_plano (plano_id)
  where visibilidade = 'compartilhada';

comment on table public.versoes_plano is
  'Versões de um plano de ensino. Privadas por padrão; uma nova revisão cria nova versão e não sobrescreve calendários pessoais.';

-- Planos existentes ganham a versão 1, de autoria do dono.
insert into public.versoes_plano (plano_id, numero, autor_id, criado_em)
select id, 1, user_id, criado_em
  from public.planos_ensino;

-- Novos planos também nascem com a versão 1, sem exigir mudança
-- no upload atual do back-end.
create or replace function public.tg_cria_versao_inicial()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.versoes_plano (plano_id, numero, autor_id)
  values (new.id, 1, new.user_id);
  return new;
end;
$$;

create trigger planos_ensino_cria_versao_inicial
  after insert on public.planos_ensino
  for each row execute function public.tg_cria_versao_inicial();

revoke execute on function public.tg_cria_versao_inicial() from public, anon, authenticated;


-- -------------------------------------------------------------
-- 5. Candidatos ligados à versão
--
-- versao_id: preenchido automaticamente com a versão mais recente
-- do plano quando o worker não o informar.
-- ordem: posição do candidato na versão; (versao_id, ordem) único
-- permite reprocessar sem duplicar.
-- -------------------------------------------------------------
alter table public.avaliacoes
  add column versao_id uuid,
  add column ordem smallint check (ordem is null or ordem >= 0);

update public.avaliacoes a
   set versao_id = v.id
  from public.versoes_plano v
 where v.plano_id = a.plano_id
   and v.numero = 1;

alter table public.avaliacoes
  alter column versao_id set not null,
  add constraint avaliacoes_versao_do_plano
    foreign key (plano_id, versao_id)
    references public.versoes_plano (plano_id, id)
    on delete cascade;

create unique index uq_avaliacoes_versao_ordem
  on public.avaliacoes (versao_id, ordem)
  where ordem is not null;

create index idx_avaliacoes_versao on public.avaliacoes (versao_id);

create or replace function public.tg_avaliacao_versao_padrao()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.versao_id is null then
    select v.id into new.versao_id
      from public.versoes_plano v
     where v.plano_id = new.plano_id
     order by v.numero desc
     limit 1;
  end if;
  return new;
end;
$$;

create trigger avaliacoes_versao_padrao
  before insert on public.avaliacoes
  for each row execute function public.tg_avaliacao_versao_padrao();

revoke execute on function public.tg_avaliacao_versao_padrao() from public, anon, authenticated;


-- -------------------------------------------------------------
-- 6. Importação por usuário / candidato / versão
--
-- Antes: um candidato gerava no máximo um evento no sistema inteiro,
-- o que impediria dois colegas de importar a mesma versão
-- compartilhada. Agora: no máximo um evento por usuário e candidato.
-- -------------------------------------------------------------
drop index if exists public.uq_eventos_pessoais_origem_avaliacao;

create unique index uq_eventos_pessoais_usuario_avaliacao
  on public.eventos_pessoais (user_id, origem_avaliacao_id)
  where origem_avaliacao_id is not null;

alter table public.eventos_pessoais
  add column origem_versao_id uuid references public.versoes_plano(id) on delete set null;

update public.eventos_pessoais e
   set origem_versao_id = a.versao_id
  from public.avaliacoes a
 where a.id = e.origem_avaliacao_id;

create index idx_eventos_pessoais_usuario_versao
  on public.eventos_pessoais (user_id, origem_versao_id)
  where origem_versao_id is not null;

comment on column public.eventos_pessoais.origem_avaliacao_id is
  'Candidato que originou o evento. Único por usuário: cada um importa uma vez para a própria agenda.';
comment on column public.eventos_pessoais.origem_versao_id is
  'Versão do plano de onde o evento foi importado.';


-- -------------------------------------------------------------
-- 7. Remoção do modelo paralelo de candidatos (#53)
-- -------------------------------------------------------------
drop table if exists public.candidatos_avaliacao;


-- -------------------------------------------------------------
-- 8. Isolamento (RLS)
--
-- Regra de leitura de uma versão: o dono do plano, ou, se a versão
-- estiver compartilhada, quem segue a oferta do plano. A função é
-- security definer para consultar planos e vínculos sem depender
-- das políticas dessas tabelas.
-- -------------------------------------------------------------
create or replace function public.pode_ler_versao(p_versao_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
      from public.versoes_plano v
      join public.planos_ensino p on p.id = v.plano_id
     where v.id = p_versao_id
       and (
         p.user_id = (select auth.uid())
         or (
           v.visibilidade = 'compartilhada'
           and p.oferta_id is not null
           and exists (
             select 1 from public.vinculos_turma vt
              where vt.oferta_id = p.oferta_id
                and vt.user_id = (select auth.uid())
           )
         )
       )
  );
$$;

revoke execute on function public.pode_ler_versao(uuid) from public, anon;
grant  execute on function public.pode_ler_versao(uuid) to authenticated;

-- Catálogo: público para leitura.
alter table public.disciplinas enable row level security;
alter table public.ofertas_turma enable row level security;

create policy "catalogo de disciplinas e publico"
  on public.disciplinas for select
  to anon, authenticated
  using (true);

create policy "catalogo de ofertas e publico"
  on public.ofertas_turma for select
  to anon, authenticated
  using (true);

-- Vínculos: cada um vê os próprios.
alter table public.vinculos_turma enable row level security;

create policy "usuario consulta os proprios vinculos"
  on public.vinculos_turma for select
  to authenticated
  using (user_id = (select auth.uid()));

-- Versões: dono, ou seguidor da oferta quando compartilhada.
alter table public.versoes_plano enable row level security;

create policy "leitura de versoes autorizadas"
  on public.versoes_plano for select
  to authenticated
  using (public.pode_ler_versao(id));

-- Candidatos: além do dono (política existente), quem pode ler a
-- versão compartilhada.
create policy "leitura de candidatos de versoes compartilhadas"
  on public.avaliacoes for select
  to authenticated
  using (public.pode_ler_versao(versao_id));
