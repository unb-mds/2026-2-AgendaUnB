-- =============================================================
-- Issue #42 — RLS e políticas de segurança do painel admin
--
-- Tudo que o painel faz é conferido aqui no banco. Mesmo que o
-- front ou o back-end esqueçam uma verificação, o Postgres recusa.
--
-- Observação: o back-end conecta direto no Postgres (DATABASE_URL)
-- com um usuário que ignora RLS. As políticas abaixo protegem o
-- caminho supabase-js (navegador). Os triggers e as funções valem
-- para os dois caminhos.
-- =============================================================


-- -------------------------------------------------------------
-- 1. Quem é admin?
--
-- Função auxiliar usada pelas políticas. É security definer para
-- poder ler profiles sem cair nas políticas de profiles (o que
-- geraria recursão infinita).
-- -------------------------------------------------------------
create or replace function public.is_admin()
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.profiles
    where id = (select auth.uid())
      and papel = 'admin'
  );
$$;

revoke execute on function public.is_admin() from public, anon;
grant  execute on function public.is_admin() to authenticated;


-- -------------------------------------------------------------
-- 2. Ninguém se promove a admin sozinho
--
-- Até aqui, a política "usuario edita o proprio perfil" deixava
-- qualquer usuário logado rodar no navegador:
--   supabase.from('profiles').update({ papel: 'admin' }).eq('id', meuId)
-- e virar admin. A constraint do e-mail só barrava 'professor'.
--
-- Regra nova, para quem chega pela API (anon/authenticated):
--   - estudante -> professor: permitido (é o promoverParaProfessor
--     do front; a constraint do e-mail @unb.br continua valendo);
--   - qualquer outra troca de papel: recusada.
-- Admin troca papéis pela função admin_alterar_papel (seção 5),
-- que roda como dono da função e por isso passa por este trigger.
-- O painel do Supabase e o back-end também não são afetados.
-- -------------------------------------------------------------
create or replace function public.tg_protege_papel()
returns trigger
language plpgsql
as $$
begin
  if new.papel is distinct from old.papel
     and current_user in ('anon', 'authenticated')
     and not (old.papel = 'student' and new.papel = 'professor')
  then
    raise exception 'Alteração de papel não permitida'
      using errcode = '42501';
  end if;
  return new;
end;
$$;

create trigger profiles_protege_papel
  before update on public.profiles
  for each row execute function public.tg_protege_papel();


-- -------------------------------------------------------------
-- 3. Lista de usuários só para admin
--
-- Antes: "perfis visiveis para todos" (qualquer visitante lia
-- nome e e-mail de todo mundo). O front hoje só lê o próprio
-- perfil, e o back-end ignora RLS, então nada quebra.
-- -------------------------------------------------------------
drop policy if exists "perfis visiveis para todos" on public.profiles;
drop policy if exists "perfis visiveis para usuarios logados" on public.profiles;

create policy "usuario ve o proprio perfil"
  on public.profiles for select
  to authenticated
  using (id = (select auth.uid()));

create policy "admin ve todos os perfis"
  on public.profiles for select
  to authenticated
  using ((select public.is_admin()));


-- -------------------------------------------------------------
-- 4. Moderação de eventos
--
-- Políticas de SELECT se somam (OR). Resultado:
--   - visitante e qualquer usuário: só 'aprovado' (política antiga);
--   - autor: também os próprios 'pendente' e 'rejeitado';
--   - admin: todos.
-- Só admin altera evento (aprovar, rejeitar, justificar).
-- -------------------------------------------------------------
create policy "autor ve os proprios eventos"
  on public.eventos for select
  to authenticated
  using (autor_id = (select auth.uid()));

create policy "admin ve todos os eventos"
  on public.eventos for select
  to authenticated
  using ((select public.is_admin()));

create policy "admin modera eventos"
  on public.eventos for update
  to authenticated
  using      ((select public.is_admin()))
  with check ((select public.is_admin()));


-- -------------------------------------------------------------
-- 5. Funções (RPC) do painel
--
-- Os dados de login (e-mail confirmado, último acesso) ficam em
-- auth.users, que o navegador não pode ler. Estas funções rodam
-- com permissão do dono, mas a primeira coisa que fazem é
-- conferir se quem chamou é admin.
--
-- Uso no front:
--   await supabase.rpc('admin_listar_usuarios')
--   await supabase.rpc('admin_alterar_papel',
--     { p_usuario_id: id, p_novo_papel: 'professor' })
-- -------------------------------------------------------------
create or replace function public.admin_listar_usuarios()
returns table (
  id               uuid,
  email            text,
  nome_completo    text,
  papel            text,
  criado_em        timestamptz,
  ultimo_login     timestamptz,
  email_confirmado boolean
)
language plpgsql
stable
security definer
set search_path = ''
as $$
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores'
      using errcode = '42501';
  end if;

  return query
    select u.id,
           u.email::text,
           p.nome_completo,
           p.papel,
           u.created_at,
           u.last_sign_in_at,
           u.email_confirmed_at is not null
      from auth.users u
      join public.profiles p on p.id = u.id
     order by u.created_at desc;
end;
$$;

create or replace function public.admin_alterar_papel(
  p_usuario_id uuid,
  p_novo_papel text
)
returns public.profiles
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_perfil public.profiles;
begin
  if not public.is_admin() then
    raise exception 'Apenas administradores'
      using errcode = '42501';
  end if;

  if p_novo_papel not in ('student', 'professor', 'admin') then
    raise exception 'Papel inválido: %', p_novo_papel
      using errcode = '22023';
  end if;

  -- Evita que o último admin se rebaixe e tranque o painel.
  if p_usuario_id = (select auth.uid()) and p_novo_papel <> 'admin' then
    raise exception 'Um admin não pode remover o próprio papel de admin'
      using errcode = '42501';
  end if;

  -- Professor sem @unb.br continua barrado pela constraint
  -- professor_exige_email_institucional (erro 23514).
  update public.profiles
     set papel = p_novo_papel
   where id = p_usuario_id
  returning * into v_perfil;

  if not found then
    raise exception 'Usuário não encontrado'
      using errcode = 'P0002';
  end if;

  return v_perfil;
end;
$$;

revoke execute on function public.admin_listar_usuarios()            from public, anon;
revoke execute on function public.admin_alterar_papel(uuid, text)    from public, anon;
grant  execute on function public.admin_listar_usuarios()            to authenticated;
grant  execute on function public.admin_alterar_papel(uuid, text)    to authenticated;
revoke execute on function public.tg_protege_papel()                 from public, anon, authenticated;
