-- =============================================================
-- S8-B03 (#81) — Lembretes persistentes 24 h antes do início
--
--   S8-B03 (#81)  lembretes persistentes dentro da plataforma
--   ADR-013       agendamento idempotente e revalidação no disparo
--
-- Requisitos: RF18 e RNF02.
--
-- As regras que precisam valer em qualquer caminho de escrita ficam
-- no banco (chaves únicas, triggers e funções). O agendador só
-- chama disparar_lembretes().
-- Nada desta migração é gravável pelo navegador.
-- =============================================================


-- -------------------------------------------------------------
-- 1. Lembretes persistentes (#81, ADR-013)
--
-- Um aviso 24 h antes do início de cada evento da agenda da conta:
-- compromisso privado ou evento público salvo. Os triggers mantêm o
-- agendamento em qualquer caminho de escrita:
--   - entrar na agenda agenda o aviso, se ainda faltar mais de 24 h;
--   - mudar o início troca o aviso pendente;
--   - excluir o compromisso, remover o vínculo ou tirar o evento do
--     catálogo cancela o aviso pendente.
-- A chave (conta, evento, início de referência) torna tudo
-- idempotente. O agendador só precisa chamar disparar_lembretes().
-- -------------------------------------------------------------
create table public.lembretes (
  id                 uuid primary key default gen_random_uuid(),
  user_id            uuid not null references public.profiles(id) on delete cascade,
  tipo_evento        text not null check (tipo_evento in ('pessoal', 'publico_salvo')),
  evento_pessoal_id  uuid references public.eventos_pessoais(id) on delete cascade,
  evento_id          uuid references public.eventos(id) on delete cascade,
  inicio_referencia  timestamptz not null,
  agendado_para      timestamptz not null,
  status             text not null default 'pendente' check (status in ('pendente', 'disparado')),
  disparado_em       timestamptz,
  lido_em            timestamptz,
  criado_em          timestamptz not null default now(),

  constraint lembretes_evento_do_tipo check (
    (tipo_evento = 'pessoal' and evento_pessoal_id is not null and evento_id is null)
    or (tipo_evento = 'publico_salvo' and evento_id is not null and evento_pessoal_id is null)
  ),
  constraint lembretes_antecedencia check (agendado_para < inicio_referencia),
  constraint lembretes_disparo_coerente check ((status = 'disparado') = (disparado_em is not null)),
  constraint lembretes_leitura_apos_disparo check (lido_em is null or status = 'disparado')
);

create unique index uq_lembretes_pessoal
  on public.lembretes (user_id, evento_pessoal_id, inicio_referencia)
  where tipo_evento = 'pessoal';

create unique index uq_lembretes_publico
  on public.lembretes (user_id, evento_id, inicio_referencia)
  where tipo_evento = 'publico_salvo';

create index idx_lembretes_a_disparar on public.lembretes (agendado_para) where status = 'pendente';
create index idx_lembretes_usuario on public.lembretes (user_id, disparado_em desc) where status = 'disparado';
create index idx_lembretes_evento on public.lembretes (evento_id) where evento_id is not null;

comment on table public.lembretes is
  'Avisos na plataforma 24 h antes do início. pendente = agendado; disparado = visível na central de avisos da conta.';
comment on column public.lembretes.inicio_referencia is
  'Início do evento usado no agendamento. Se o início mudar, o aviso pendente é trocado.';

create or replace function public.agendar_lembrete(
  p_user_id uuid, p_evento_pessoal_id uuid, p_evento_id uuid, p_inicio timestamptz
)
returns void
language plpgsql
set search_path = ''
as $$
declare
  v_tipo    text := case when p_evento_pessoal_id is not null then 'pessoal' else 'publico_salvo' end;
  v_disparo timestamptz := p_inicio - interval '24 hours';
begin
  -- Remove o aviso pendente de um início anterior.
  delete from public.lembretes
   where user_id = p_user_id
     and status = 'pendente'
     and evento_pessoal_id is not distinct from p_evento_pessoal_id
     and evento_id is not distinct from p_evento_id
     and inicio_referencia is distinct from p_inicio;

  -- Entrou na agenda com menos de 24 h: segue sem aviso retroativo.
  if p_inicio is null or v_disparo <= now() then
    return;
  end if;

  insert into public.lembretes (user_id, tipo_evento, evento_pessoal_id, evento_id, inicio_referencia, agendado_para)
  values (p_user_id, v_tipo, p_evento_pessoal_id, p_evento_id, p_inicio, v_disparo)
  on conflict do nothing;
end;
$$;

create or replace function public.tg_lembrete_evento_pessoal()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if tg_op = 'UPDATE' and new.data_hora is not distinct from old.data_hora then
    return new;
  end if;
  -- Só contas com perfil recebem avisos (o FK de eventos_pessoais aponta para auth.users).
  if exists (select 1 from public.profiles where id = new.user_id) then
    perform public.agendar_lembrete(new.user_id, new.id, null, new.data_hora);
  end if;
  return new;
end;
$$;

create trigger eventos_pessoais_agenda_lembrete
  after insert or update on public.eventos_pessoais
  for each row execute function public.tg_lembrete_evento_pessoal();

create or replace function public.tg_lembrete_evento_salvo()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_inicio timestamptz;
begin
  if tg_op = 'DELETE' then
    delete from public.lembretes
     where user_id = old.user_id and evento_id = old.event_id and status = 'pendente';
    return old;
  end if;

  select data_evento into v_inicio
    from public.eventos
   where id = new.event_id and status = 'aprovado';
  if found then
    perform public.agendar_lembrete(new.user_id, null, new.event_id, v_inicio);
  end if;
  return new;
end;
$$;

create trigger eventos_salvos_agenda_lembrete
  after insert or delete on public.eventos_salvos
  for each row execute function public.tg_lembrete_evento_salvo();

create or replace function public.tg_lembrete_evento_publico()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.status is not distinct from old.status and new.data_evento is not distinct from old.data_evento then
    return new;
  end if;
  if new.status <> 'aprovado' or new.data_evento is null then
    -- Saiu do catálogo: cancela o que ainda não disparou.
    delete from public.lembretes where evento_id = new.id and status = 'pendente';
  elsif new.data_evento is distinct from old.data_evento or old.status <> 'aprovado' then
    perform public.agendar_lembrete(s.user_id, null, new.id, new.data_evento)
       from public.eventos_salvos s
      where s.event_id = new.id;
  end if;
  return new;
end;
$$;

create trigger eventos_reagenda_lembretes
  after update on public.eventos
  for each row execute function public.tg_lembrete_evento_publico();

-- Disparo: torna visíveis os avisos cujo horário chegou. Pode ser
-- chamado quantas vezes for, por um ou vários processos: cada aviso
-- dispara uma única vez (FOR UPDATE SKIP LOCKED + status).
--
-- Revalida a elegibilidade no disparo. Um aviso atrasado ainda é
-- entregue se o evento não começou; depois do início é descartado.
create or replace function public.disparar_lembretes(p_limite integer default 500)
returns integer
language plpgsql
set search_path = ''
as $$
declare
  v_lembrete   public.lembretes;
  v_elegivel   boolean;
  v_disparados integer := 0;
begin
  for v_lembrete in
    select * from public.lembretes
     where status = 'pendente' and agendado_para <= now()
     order by agendado_para
     limit greatest(1, least(coalesce(p_limite, 500), 5000))
     for update skip locked
  loop
    if v_lembrete.tipo_evento = 'pessoal' then
      v_elegivel := exists (
        select 1 from public.eventos_pessoais e
         where e.id = v_lembrete.evento_pessoal_id
           and e.user_id = v_lembrete.user_id
           and e.data_hora = v_lembrete.inicio_referencia);
    else
      v_elegivel := exists (
        select 1 from public.eventos_salvos s
          join public.eventos e on e.id = s.event_id
         where s.user_id = v_lembrete.user_id
           and s.event_id = v_lembrete.evento_id
           and e.status = 'aprovado'
           and e.data_evento = v_lembrete.inicio_referencia);
    end if;

    if v_elegivel and v_lembrete.inicio_referencia > now() then
      update public.lembretes
         set status = 'disparado', disparado_em = now()
       where id = v_lembrete.id;
      v_disparados := v_disparados + 1;
    else
      delete from public.lembretes where id = v_lembrete.id;
    end if;
  end loop;
  return v_disparados;
end;
$$;

-- A primeira leitura vale: retries não alteram lido_em e nada mais
-- do aviso pode ser editado pelo dono.
create or replace function public.tg_lembrete_preserva_leitura()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if old.lido_em is not null then
    new.lido_em := old.lido_em;
  end if;
  return new;
end;
$$;

create trigger lembretes_preserva_leitura
  before update of lido_em on public.lembretes
  for each row execute function public.tg_lembrete_preserva_leitura();

-- Eventos que já estão na agenda ganham o aviso, se ainda couber.
insert into public.lembretes (user_id, tipo_evento, evento_pessoal_id, inicio_referencia, agendado_para)
select e.user_id, 'pessoal', e.id, e.data_hora, e.data_hora - interval '24 hours'
  from public.eventos_pessoais e
  join public.profiles p on p.id = e.user_id
 where e.data_hora - interval '24 hours' > now()
on conflict do nothing;

insert into public.lembretes (user_id, tipo_evento, evento_id, inicio_referencia, agendado_para)
select s.user_id, 'publico_salvo', e.id, e.data_evento, e.data_evento - interval '24 hours'
  from public.eventos_salvos s
  join public.eventos e on e.id = s.event_id
 where e.status = 'aprovado'
   and e.data_evento - interval '24 hours' > now()
on conflict do nothing;

-- -------------------------------------------------------------
-- 2. Acesso
--
-- A conta lê os próprios avisos já disparados e pode marcá-los como
-- lidos; o restante é do back-end e do agendador.
-- -------------------------------------------------------------
alter table public.lembretes enable row level security;

revoke all on public.lembretes from anon, authenticated;

grant select on public.lembretes to authenticated;
grant update (lido_em) on public.lembretes to authenticated;

create policy "dono le os proprios lembretes disparados"
  on public.lembretes for select
  to authenticated
  using (user_id = (select auth.uid()) and status = 'disparado');

create policy "dono marca o proprio lembrete como lido"
  on public.lembretes for update
  to authenticated
  using (user_id = (select auth.uid()) and status = 'disparado')
  with check (user_id = (select auth.uid()) and status = 'disparado');

revoke execute on function
  public.agendar_lembrete(uuid, uuid, uuid, timestamptz),
  public.tg_lembrete_evento_pessoal(),
  public.tg_lembrete_evento_salvo(),
  public.tg_lembrete_evento_publico(),
  public.disparar_lembretes(integer),
  public.tg_lembrete_preserva_leitura()
  from public, anon, authenticated;

-- O agendador roda com a credencial do servidor.
grant execute on function public.disparar_lembretes(integer) to service_role;
