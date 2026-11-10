-- S7-D01 (#69): ofertas canônicas, vínculos por estudante e versões de planos.
-- Mantém os planos existentes e não tenta inferir o período dos registros antigos.

create table if not exists public.ofertas_turma (
  id                 uuid primary key default gen_random_uuid(),
  origem             text not null default 'sigaa' check (char_length(trim(origem)) > 0),
  id_origem          text,
  codigo_disciplina   text,
  nome_disciplina     text not null check (char_length(trim(nome_disciplina)) > 0),
  numero_turma        text not null check (char_length(trim(numero_turma)) > 0),
  periodo             text not null check (char_length(trim(periodo)) > 0),
  unidade             text,
  nivel               text,
  atualizado_em       timestamptz not null default now(),
  criado_em           timestamptz not null default now(),
  constraint ck_ofertas_turma_id_origem_nao_vazio
    check (id_origem is null or char_length(trim(id_origem)) > 0)
);

comment on table public.ofertas_turma is
  'Oferta de disciplina em turma e período; ids da origem pública são preferidos para deduplicação.';

drop trigger if exists ofertas_turma_atualiza_timestamp on public.ofertas_turma;
create trigger ofertas_turma_atualiza_timestamp
  before update on public.ofertas_turma
  for each row execute function public.tg_atualiza_timestamp();

-- A chave externa identifica a oferta dentro da fonte e período.
create unique index if not exists uq_ofertas_turma_origem_id_periodo
  on public.ofertas_turma (origem, id_origem, periodo)
  where id_origem is not null;

-- Fallback determinístico quando a fonte não fornece identificador da oferta.
create unique index if not exists uq_ofertas_turma_chave_composta
  on public.ofertas_turma (
    lower(btrim(origem)),
    lower(btrim(coalesce(nullif(btrim(codigo_disciplina), ''), nome_disciplina))),
    lower(btrim(numero_turma)),
    lower(btrim(periodo)),
    lower(btrim(coalesce(unidade, ''))),
    lower(btrim(coalesce(nivel, '')))
  )
  where id_origem is null;

create index if not exists idx_ofertas_turma_periodo_codigo
  on public.ofertas_turma (periodo, codigo_disciplina);

create table if not exists public.vinculos_turma (
  user_id     uuid not null references public.profiles(id) on delete cascade,
  oferta_id   uuid not null references public.ofertas_turma(id) on delete cascade,
  criado_em   timestamptz not null default now(),
  primary key (user_id, oferta_id)
);

create index if not exists idx_vinculos_turma_oferta_usuario
  on public.vinculos_turma (oferta_id, user_id);

alter table public.planos_ensino
  add column if not exists autor_id uuid references public.profiles(id) on delete set null,
  add column if not exists oferta_id uuid references public.ofertas_turma(id) on delete set null,
  add column if not exists versao integer not null default 1 check (versao > 0),
  add column if not exists visibilidade text not null default 'privado'
    check (visibilidade in ('privado', 'compartilhado'));

-- Compatibilidade: os dados legados não carregam semestre nem id de origem.
-- Cada plano antigo recebe oferta isolada para evitar juntar semestres por suposição.
insert into public.ofertas_turma (
  origem, id_origem, codigo_disciplina, nome_disciplina, numero_turma,
  periodo, unidade, nivel
)
select
  'legado',
  plano.id::text,
  null,
  coalesce(nullif(btrim(plano.disciplina), ''), 'Disciplina legada'),
  coalesce(nullif(btrim(plano.turma), ''), 'Turma legada'),
  'legado',
  null,
  null
from public.planos_ensino plano
where not exists (
  select 1 from public.ofertas_turma oferta
  where oferta.origem = 'legado' and oferta.id_origem = plano.id::text
);

update public.planos_ensino plano
set oferta_id = oferta.id
from public.ofertas_turma oferta
where plano.oferta_id is null
  and oferta.origem = 'legado'
  and oferta.id_origem = plano.id::text;

update public.planos_ensino
set autor_id = coalesce(professor_id, user_id)
where autor_id is null;

-- O fluxo de upload atual grava user_id. Planos da primeira versão tinham
-- professor_id; aproveita essa autoria para preencher o novo dono.
update public.planos_ensino
set user_id = professor_id
where user_id is null and professor_id is not null;

insert into public.vinculos_turma (user_id, oferta_id)
select distinct user_id, oferta_id
from public.planos_ensino
where user_id is not null and oferta_id is not null
on conflict (user_id, oferta_id) do nothing;

create index if not exists idx_planos_ensino_user_oferta_versao
  on public.planos_ensino (user_id, oferta_id, versao desc);

create index if not exists idx_planos_ensino_oferta_id
  on public.planos_ensino (oferta_id);

create unique index if not exists uq_planos_ensino_oferta_autor_versao
  on public.planos_ensino (oferta_id, autor_id, versao)
  where oferta_id is not null and autor_id is not null;

-- As ofertas são catálogo institucional; vínculos e planos seguem o escopo do usuário.
alter table public.ofertas_turma enable row level security;
alter table public.vinculos_turma enable row level security;

drop policy if exists "ofertas visiveis para usuarios autenticados" on public.ofertas_turma;
create policy "ofertas visiveis para usuarios autenticados"
  on public.ofertas_turma for select to authenticated using (true);

drop policy if exists "usuario consulta os proprios vinculos de turma" on public.vinculos_turma;
create policy "usuario consulta os proprios vinculos de turma"
  on public.vinculos_turma for select to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists "usuario cria os proprios vinculos de turma" on public.vinculos_turma;
create policy "usuario cria os proprios vinculos de turma"
  on public.vinculos_turma for insert to authenticated
  with check (user_id = (select auth.uid()));

drop policy if exists "usuario remove os proprios vinculos de turma" on public.vinculos_turma;
create policy "usuario remove os proprios vinculos de turma"
  on public.vinculos_turma for delete to authenticated
  using (user_id = (select auth.uid()));

-- Compartilhar só concede acesso a pessoas vinculadas à mesma oferta.
drop policy if exists "planos particulares: usuario le apenas os proprios planos" on public.planos_ensino;
create policy "dono ou colega vinculado consulta plano compartilhado"
  on public.planos_ensino for select to authenticated
  using (
    user_id = (select auth.uid())
    or (
      visibilidade = 'compartilhado'
      and oferta_id is not null
      and exists (
        select 1 from public.vinculos_turma vinculo
        where vinculo.user_id = (select auth.uid())
          and vinculo.oferta_id = planos_ensino.oferta_id
      )
    )
  );

drop policy if exists "planos particulares: usuario cria os proprios planos" on public.planos_ensino;
create policy "usuario cria plano proprio" on public.planos_ensino for insert to authenticated
  with check (
    user_id = (select auth.uid())
    and (autor_id is null or autor_id = (select auth.uid()))
    and (
      visibilidade = 'privado'
      or exists (
        select 1 from public.profiles perfil
        where perfil.id = (select auth.uid()) and perfil.papel in ('professor', 'admin')
      )
    )
  );

drop policy if exists "usuario atualiza plano proprio" on public.planos_ensino;
create policy "usuario atualiza plano proprio" on public.planos_ensino for update to authenticated
  using (user_id = (select auth.uid()))
  with check (
    user_id = (select auth.uid())
    and (autor_id is null or autor_id = (select auth.uid()))
    and (
      visibilidade = 'privado'
      or exists (
        select 1 from public.profiles perfil
        where perfil.id = (select auth.uid()) and perfil.papel in ('professor', 'admin')
      )
    )
  );

drop policy if exists "usuario remove plano proprio" on public.planos_ensino;
create policy "usuario remove plano proprio" on public.planos_ensino for delete to authenticated
  using (user_id = (select auth.uid()));

drop policy if exists "dono do plano consulta candidatos" on public.avaliacoes;
create policy "dono ou colega consulta candidatos compartilhados"
  on public.avaliacoes for select to authenticated
  using (
    exists (
      select 1 from public.planos_ensino plano
      where plano.id = avaliacoes.plano_id
        and (
          plano.user_id = (select auth.uid())
          or (
            plano.visibilidade = 'compartilhado'
            and plano.oferta_id is not null
            and exists (
              select 1 from public.vinculos_turma vinculo
              where vinculo.user_id = (select auth.uid())
                and vinculo.oferta_id = plano.oferta_id
            )
          )
        )
    )
  );

-- Mantém a leitura privada do Storage e permite leitura de arquivos somente
-- quando o plano correspondente foi explicitamente compartilhado com a turma.
drop policy if exists "planos compartilhados: colega vinculado le arquivo" on storage.objects;
create policy "planos compartilhados: colega vinculado le arquivo"
  on storage.objects for select to authenticated
  using (
    bucket_id = 'syllabus_files'
    and exists (
      select 1
      from public.planos_ensino plano
      join public.vinculos_turma vinculo
        on vinculo.oferta_id = plano.oferta_id
       and vinculo.user_id = (select auth.uid())
      where plano.visibilidade = 'compartilhado'
        and plano.arquivo_url = bucket_id || '/' || name
    )
  );

comment on column public.planos_ensino.oferta_id is
  'Oferta canônica em que o plano foi publicado; nulo enquanto turma/período não forem conhecidos.';
comment on column public.planos_ensino.autor_id is
  'Pessoa responsável pela autoria do documento; user_id permanece o dono dos dados privados.';
comment on column public.planos_ensino.visibilidade is
  'privado: somente o dono; compartilhado: colegas vinculados à mesma oferta também podem consultar.';
