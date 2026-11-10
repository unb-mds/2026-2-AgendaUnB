-- =============================================================
-- S8-D02 (#84) — Endurecimento de segurança do banco exposto
--
-- Requisitos: RF04, RNF01, RNF02 e RNF04.
--
-- Corrige os achados da verificação preventiva (ver
-- docs/processo/seguranca.md). Em resumo:
--   1. eventos públicos só são gravados pela API ou pelas RPCs de
--      moderação. O INSERT direto do navegador permitia gravar um
--      link_externo "javascript:" que a tela de evento abria;
--   2. o banco valida o formato do link e o tamanho dos textos em
--      qualquer caminho de escrita;
--   3. papel de professor depende de e-mail institucional CONFIRMADO;
--   4. menor privilégio: visitante sem escrita, funções sem EXECUTE
--      por padrão e perfil editável só nas colunas previstas;
--   5. toda mudança de papel fica registrada.
--
-- Nada aqui muda o contrato da API nem as telas existentes: o
-- front-end já cria eventos pela API e só usa o Supabase direto para
-- ler o perfil, promover-se a professor e marcar notificações.
-- =============================================================


-- -------------------------------------------------------------
-- 1. Formato e tamanho validados no banco
--
-- A API já valida esses campos, mas o banco também é alcançável
-- pelo supabase-js. Os limites repetem os dos schemas da API.
-- Dados antigos fora do padrão são saneados antes: um link que não
-- é http(s) não pode ser aberto com segurança.
-- -------------------------------------------------------------
update public.eventos
   set link_externo = null
 where link_externo is not null
   and (char_length(link_externo) > 2048
        or link_externo !~* '^https?://[^[:space:]<>"]+$');

update public.eventos set titulo = left(btrim(titulo), 200) where char_length(titulo) > 200;
update public.eventos set descricao = left(descricao, 10000) where char_length(descricao) > 10000;
update public.eventos set localizacao = left(localizacao, 250) where char_length(localizacao) > 250;

alter table public.eventos
  add constraint eventos_titulo_tamanho
    check (char_length(titulo) <= 200),
  add constraint eventos_descricao_tamanho
    check (char_length(descricao) <= 10000),
  add constraint eventos_localizacao_tamanho
    check (localizacao is null or char_length(localizacao) <= 250),
  add constraint eventos_link_externo_http
    check (link_externo is null
           or (char_length(link_externo) <= 2048
               and link_externo ~* '^https?://[^[:space:]<>"]+$'));

comment on constraint eventos_link_externo_http on public.eventos is
  'Só http(s). Impede esquemas como javascript: e data:, que executariam código ao abrir o link.';

update public.eventos_pessoais set titulo = left(btrim(titulo), 200) where char_length(titulo) > 200;
update public.eventos_pessoais set descricao = left(descricao, 10000) where char_length(descricao) > 10000;
update public.eventos_pessoais set origem_trecho = left(origem_trecho, 2000) where char_length(origem_trecho) > 2000;

alter table public.eventos_pessoais
  add constraint eventos_pessoais_titulo_tamanho
    check (char_length(titulo) <= 200),
  add constraint eventos_pessoais_descricao_tamanho
    check (descricao is null or char_length(descricao) <= 10000),
  add constraint eventos_pessoais_origem_trecho_tamanho
    check (origem_trecho is null or char_length(origem_trecho) <= 2000);

update public.profiles set nome_completo = left(btrim(nome_completo), 200) where char_length(nome_completo) > 200;
update public.profiles
   set avatar_url = null
 where avatar_url is not null
   and (char_length(avatar_url) > 2048 or avatar_url !~* '^https://[^[:space:]<>"]+$');

alter table public.profiles
  add constraint profiles_nome_tamanho
    check (char_length(nome_completo) <= 200),
  add constraint profiles_avatar_https
    check (avatar_url is null
           or (char_length(avatar_url) <= 2048
               and avatar_url ~* '^https://[^[:space:]<>"]+$'));


-- -------------------------------------------------------------
-- 2. Eventos públicos: escrita só pela API e pelas RPCs
--
-- A política abaixo deixava qualquer conta logada inserir direto em
-- eventos, sem passar pela validação da API. As RPCs de moderação
-- são SECURITY DEFINER e continuam funcionando.
-- -------------------------------------------------------------
drop policy if exists "usuarios logados podem criar eventos" on public.eventos;
revoke insert, update, delete on public.eventos from anon, authenticated;


-- -------------------------------------------------------------
-- 3. Menor privilégio nas tabelas
--
-- O Supabase concede todos os privilégios a anon e authenticated
-- por padrão e deixa a proteção só com o RLS. Aqui o GRANT passa a
-- acompanhar o que as políticas permitem, para que um engano em uma
-- política futura não exponha escrita.
--
-- TRUNCATE não passa pelo RLS, por isso é o primeiro a sair.
-- -------------------------------------------------------------
revoke truncate, references, trigger on all tables in schema public from anon, authenticated;

-- Visitante: só leitura do que é público.
revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;
grant select on public.eventos, public.campus, public.categories,
                public.disciplinas, public.ofertas_turma to anon;

-- Conta logada: escrita apenas onde existe política de escrita.
revoke insert, update, delete on
  public.campus, public.categories, public.disciplinas, public.ofertas_turma,
  public.vinculos_turma, public.planos_ensino, public.versoes_plano, public.avaliacoes
  from authenticated;

-- Vínculo salvo não tem o que editar: só existe ou não existe.
revoke update on public.eventos_salvos from authenticated;

-- Perfil: nada de INSERT/DELETE, e UPDATE só nas colunas previstas.
-- papel continua protegido pelo trigger profiles_protege_papel.
revoke insert, update, delete on public.profiles from authenticated;
grant update (nome_completo, avatar_url, papel) on public.profiles to authenticated;

-- Tabelas futuras nascem sem acesso de visitante e sem TRUNCATE.
-- Uma tabela de leitura pública precisa de GRANT SELECT explícito.
alter default privileges in schema public revoke all on tables from anon;
alter default privileges in schema public revoke all on sequences from anon;
alter default privileges in schema public revoke truncate, references, trigger on tables from authenticated;


-- -------------------------------------------------------------
-- 4. Funções: EXECUTE só para quem precisa
--
-- Toda função nova nascia executável por qualquer visitante via
-- /rpc. A partir daqui o padrão é fechado e cada função declara
-- quem pode chamá-la.
--
-- registrar_interesse(uuid) não é mais chamável pelo navegador:
-- qualquer visitante inflava o contador sem limite e sem validar o
-- link. O front-end não a utiliza; o contador passa a ser
-- alimentado pela API (S8-B02).
-- -------------------------------------------------------------
revoke execute on all functions in schema public from public, anon, authenticated;

grant execute on function
  public.is_admin(),
  public.is_event_moderator(),
  public.admin_listar_usuarios(),
  public.admin_alterar_papel(uuid, text),
  public.admin_buscar_usuarios(text, text, text, integer),
  public.admin_definir_papel(uuid, text, text),
  public.moderar_sugestao(uuid, text, text),
  public.listar_sugestoes(text, text, integer),
  public.pode_ler_versao(uuid)
  to authenticated;

alter default privileges revoke execute on functions from public;
alter default privileges in schema public revoke execute on functions from anon, authenticated;


-- -------------------------------------------------------------
-- 5. Professor exige e-mail institucional confirmado
--
-- Antes: o cadastro com papel 'professor' e um endereço @unb.br
-- criava o perfil de professor antes de qualquer confirmação. Quem
-- informasse um @unb.br que não lhe pertence ganhava o papel no
-- momento do cadastro, e professor publica e modera eventos.
--
-- Agora o papel só é concedido com o e-mail confirmado:
--   - cadastro já confirmado (Google, ou ambiente local sem
--     confirmação): professor na hora, como antes;
--   - cadastro pendente de confirmação: nasce estudante e é
--     promovido automaticamente quando confirmar o e-mail.
-- -------------------------------------------------------------
create or replace function public.tg_cria_perfil()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_papel text;
begin
  v_papel := coalesce(nullif(btrim(new.raw_user_meta_data ->> 'papel'), ''), 'student');

  -- admin nunca vem do cadastro.
  if v_papel not in ('student', 'professor') then
    v_papel := 'student';
  end if;

  if v_papel = 'professor' and new.email !~* '@unb\.br$' then
    raise exception 'Cadastro como professor exige e-mail institucional da UnB (@unb.br)'
      using errcode = 'check_violation';
  end if;

  -- Sem confirmação ainda não há prova de que o endereço é da pessoa.
  if v_papel = 'professor' and new.email_confirmed_at is null then
    v_papel := 'student';
  end if;

  insert into public.profiles (id, nome_completo, email, papel)
  values (
    new.id,
    left(coalesce(
      nullif(btrim(new.raw_user_meta_data ->> 'nome_completo'), ''),
      nullif(btrim(new.raw_user_meta_data ->> 'full_name'), ''),
      nullif(btrim(new.raw_user_meta_data ->> 'name'), ''),
      split_part(new.email, '@', 1)
    ), 200),
    new.email,
    v_papel
  );

  return new;
end;
$$;

create or replace function public.tg_promove_professor_confirmado()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if old.email_confirmed_at is null
     and new.email_confirmed_at is not null
     and new.raw_user_meta_data ->> 'papel' = 'professor'
  then
    -- profiles.email é imutável: é o endereço confirmado no cadastro.
    update public.profiles
       set papel = 'professor'
     where id = new.id
       and papel = 'student'
       and email ~* '@unb\.br$';
  end if;
  return new;
end;
$$;

drop trigger if exists on_auth_user_email_confirmed on auth.users;
create trigger on_auth_user_email_confirmed
  after update of email_confirmed_at on auth.users
  for each row execute function public.tg_promove_professor_confirmado();

-- A autopromoção pelo navegador (promoverParaProfessor) passa a
-- exigir a mesma confirmação.
create or replace function public.meu_email_confirmado()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
      from auth.users u
     where u.id = (select auth.uid())
       and u.email_confirmed_at is not null
  );
$$;

create or replace function public.tg_protege_papel()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
  if new.papel is distinct from old.papel
     and current_user in ('anon', 'authenticated')
     and not (
       old.papel = 'student'
       and new.papel = 'professor'
       and new.email ~* '@unb\.br$'
       and public.meu_email_confirmado()
     )
  then
    raise exception 'Alteração de papel não permitida'
      using errcode = '42501';
  end if;
  return new;
end;
$$;

revoke execute on function public.tg_promove_professor_confirmado() from public, anon, authenticated;
revoke execute on function public.meu_email_confirmado() from public, anon;
grant  execute on function public.meu_email_confirmado() to authenticated;

-- Perfis que se declararam professor e nunca confirmaram o e-mail
-- voltam a estudante. Serão promovidos ao confirmar.
update public.profiles p
   set papel = 'student'
  from auth.users u
 where u.id = p.id
   and p.papel = 'professor'
   and u.email_confirmed_at is null
   and u.raw_user_meta_data ->> 'papel' = 'professor';


-- -------------------------------------------------------------
-- 6. Trilha de auditoria de papéis
--
-- Registra toda mudança de papel, por qualquer caminho: RPC do
-- painel, autopromoção, confirmação de e-mail, back-end ou SQL.
-- ator_id nulo significa que não havia sessão de usuário (back-end
-- ou painel do Supabase).
-- -------------------------------------------------------------
create table public.auditoria_papeis (
  id              bigint generated always as identity primary key,
  usuario_id      uuid not null references public.profiles(id) on delete cascade,
  ator_id         uuid references public.profiles(id) on delete set null,
  papel_anterior  text not null,
  papel_novo      text not null,
  criado_em       timestamptz not null default now()
);

create index idx_auditoria_papeis_usuario on public.auditoria_papeis (usuario_id, criado_em desc);

comment on table public.auditoria_papeis is
  'Histórico de mudanças de papel. Somente admins leem; ninguém altera pela API.';

create or replace function public.tg_audita_papel()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  if new.papel is distinct from old.papel then
    insert into public.auditoria_papeis (usuario_id, ator_id, papel_anterior, papel_novo)
    values (
      new.id,
      (select p.id from public.profiles p where p.id = (select auth.uid())),
      old.papel,
      new.papel
    );
  end if;
  return new;
end;
$$;

create trigger profiles_audita_papel
  after update of papel on public.profiles
  for each row execute function public.tg_audita_papel();

revoke execute on function public.tg_audita_papel() from public, anon, authenticated;

alter table public.auditoria_papeis enable row level security;

revoke all on public.auditoria_papeis from anon, authenticated;
grant select on public.auditoria_papeis to authenticated;

create policy "admin consulta auditoria de papeis"
  on public.auditoria_papeis for select
  to authenticated
  using ((select public.is_admin()));


-- -------------------------------------------------------------
-- Fila de processamento por IA (20261109185725, #92)
--
-- A tabela recebeu os privilégios padrão: contas logadas tinham
-- INSERT, UPDATE e DELETE sem política (o RLS bloqueava só porque
-- nenhuma política de escrita existia). E a política de leitura usava
-- planos_ensino.professor_id, nulo em plano particular: o dono nunca
-- via o próprio job.
--
-- Observação: o worker atual (S7-B01) controla a fila pelas colunas de
-- planos_ensino (status, token_processamento, proxima_tentativa_em) e
-- não usa esta tabela. Manter as duas é decisão da equipe; aqui só se
-- garante que ela não seja um caminho de escrita pelo navegador.
-- -------------------------------------------------------------
revoke all on public.fila_processamento_ia from anon, authenticated;
grant select on public.fila_processamento_ia to authenticated;

drop policy if exists "Usuário vê status do seu plano na fila" on public.fila_processamento_ia;
create policy "dono do plano acompanha o proprio job"
  on public.fila_processamento_ia for select
  to authenticated
  using (exists (
    select 1 from public.planos_ensino p
     where p.id = plano_id and p.user_id = (select auth.uid())));

-- Só um código curto (http_429, timeout). NOT VALID: não reprova linhas
-- antigas, mas vale para toda escrita nova.
alter table public.fila_processamento_ia
  add constraint fila_ia_erro_tecnico_curto
    check (erro_tecnico is null or char_length(erro_tecnico) <= 60) not valid;
