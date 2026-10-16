-- =============================================================
-- Issue #41 — Modelagem para sugestão de eventos e contador
--
-- Estudantes passam a poder sugerir eventos. Toda sugestão de
-- estudante entra como 'pendente' e só vai para a agenda pública
-- depois de aprovada por um admin (ver migration da issue #42).
--
-- Os status seguem os valores que já existem na tabela:
-- 'pendente', 'aprovado' e 'rejeitado'.
-- =============================================================


-- -------------------------------------------------------------
-- Novas colunas
-- -------------------------------------------------------------
alter table public.eventos
  add column justificativa_recusa text,
  add column interessados_count   integer not null default 0;

-- O contador nunca fica negativo.
alter table public.eventos
  add constraint interessados_count_nao_negativo
  check (interessados_count >= 0);

-- Justificativa só faz sentido em evento rejeitado. Se um admin
-- reverter a recusa, precisa limpar a justificativa junto.
alter table public.eventos
  add constraint justificativa_apenas_em_rejeitado
  check (justificativa_recusa is null or status = 'rejeitado');

comment on column public.eventos.justificativa_recusa is
  'Motivo da recusa, escrito pelo admin. Nulo exceto quando status = rejeitado.';
comment on column public.eventos.interessados_count is
  'Quantas vezes o botão de redirecionamento do evento foi clicado.';


-- -------------------------------------------------------------
-- Evento de estudante nasce 'pendente'
--
-- Feito com trigger, e não com política de RLS, porque o back-end
-- grava direto no Postgres e não passa pelo RLS. O trigger vale
-- para qualquer caminho de escrita: supabase-js, back-end ou SQL.
--
-- O papel é lido do autor do evento, e não de auth.uid(), pelo
-- mesmo motivo: chamadas do back-end não têm auth.uid().
--
-- Professor e admin continuam escolhendo o status (hoje o
-- back-end cria os eventos deles já como 'aprovado').
-- -------------------------------------------------------------
create or replace function public.tg_evento_de_estudante_pendente()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_papel text;
begin
  select papel into v_papel
  from public.profiles
  where id = new.autor_id;

  if v_papel is distinct from 'professor' and v_papel is distinct from 'admin' then
    new.status := 'pendente';
    new.justificativa_recusa := null;
  end if;

  -- Ninguém cria evento com contador já preenchido.
  new.interessados_count := 0;

  return new;
end;
$$;

create trigger eventos_estudante_pendente
  before insert on public.eventos
  for each row execute function public.tg_evento_de_estudante_pendente();


-- -------------------------------------------------------------
-- Incrementar o contador
--
-- Quem clica no botão não tem permissão de UPDATE em eventos,
-- então o incremento passa por esta função. Ela só soma 1, e só
-- em evento aprovado: não dá para escolher o valor nem mexer em
-- outra coluna.
--
-- Uso no front:
--   await supabase.rpc('registrar_interesse', { p_evento_id: id })
-- -------------------------------------------------------------
create or replace function public.registrar_interesse(p_evento_id uuid)
returns integer
language sql
security definer
set search_path = ''
as $$
  update public.eventos
     set interessados_count = interessados_count + 1
   where id = p_evento_id
     and status = 'aprovado'
  returning interessados_count;
$$;

revoke execute on function public.registrar_interesse(uuid) from public;
grant  execute on function public.registrar_interesse(uuid) to anon, authenticated;

-- A função de trigger não é para ser chamada direto pela API.
revoke execute on function public.tg_evento_de_estudante_pendente() from public, anon, authenticated;
