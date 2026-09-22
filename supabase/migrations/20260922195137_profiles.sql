-- =============================================================
-- perfis de usuário
--
-- O Supabase Auth cuida do login, da senha e do OAuth do Google,
-- e guarda o usuário na tabela auth.users, que é dele e não deve
-- ser alterada por nós.
--
-- Esta tabela guarda o que o Auth não guarda e o nosso produto
-- precisa: nome completo (RF02) e papel (RF04).
--
-- Requisitos atendidos: RF01, RF02, RF03, RF04
-- =============================================================

create table public.profiles (
  id             uuid primary key references auth.users(id) on delete cascade,
  nome_completo  text        not null check (char_length(trim(nome_completo)) >= 2),
  email          text        not null,
  papel          text        not null default 'student'
                 check (papel in ('student', 'professor', 'admin')),
  criado_em      timestamptz not null default now(),
  atualizado_em  timestamptz not null default now(),

  -- Regra de negócio central do RF04: professor só com conta
  -- institucional da UnB.
  --
  -- O til-til (~*) compara com expressão regular, sem diferenciar
  -- maiúsculas. O '@' antes de unb\.br é o que impede que
  -- fulano@aluno.unb.br passe: nesse e-mail, antes de "unb.br"
  -- vem "aluno.", e não a arroba.
  --
  -- Estar como CHECK e não como validação de tela significa que
  -- não há como burlar: nem pelo DevTools, nem por chamada direta
  -- à API.
  constraint professor_exige_email_institucional
    check (papel <> 'professor' or email ~* '@unb\.br$')
);

comment on table public.profiles is
  'Dados de perfil do usuário. Criado automaticamente no primeiro login.';

-- -------------------------------------------------------------
-- atualizado_em mantido pelo banco, não pelo front.
-- -------------------------------------------------------------
create or replace function public.tg_atualiza_timestamp()
returns trigger
language plpgsql
as $$
begin
  new.atualizado_em = now();
  return new;
end;
$$;

create trigger profiles_atualiza_timestamp
  before update on public.profiles
  for each row execute function public.tg_atualiza_timestamp();

-- -------------------------------------------------------------
-- O perfil nasce junto com a conta.
--
-- Vale para os dois caminhos de cadastro:
--   - Google (RF03): o nome vem da conta Google, em full_name ou name
--   - e-mail e senha (RF02): o nome vem do formulário de cadastro,
--     que precisa enviá-lo em options.data.nome_completo
--
-- O coalesce garante que, enquanto a tela de cadastro não enviar
-- o nome, o cadastro não quebra: cai para a parte do e-mail antes
-- da arroba.
--
-- Sobre o papel (RF04): a tela de cadastro tem o seletor
-- Estudante / Professor, então o papel escolhido é respeitado —
-- mas apenas entre esses dois. 'admin' nunca vem do cliente: se
-- viesse, bastaria abrir o DevTools e enviá-lo no cadastro.
--
-- A regra do e-mail institucional é verificada aqui com mensagem
-- legível, para o front conseguir exibi-la. A constraint da
-- tabela continua valendo como rede de segurança — ela pega
-- qualquer caminho que não passe por este gatilho.
-- -------------------------------------------------------------
create or replace function public.tg_cria_perfil()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  v_papel text;
begin
  v_papel := coalesce(nullif(trim(new.raw_user_meta_data ->> 'papel'), ''), 'student');

  -- Só estes dois podem vir da tela de cadastro.
  if v_papel not in ('student', 'professor') then
    v_papel := 'student';
  end if;

  if v_papel = 'professor' and new.email !~* '@unb\.br$' then
    raise exception 'Cadastro como professor exige e-mail institucional da UnB (@unb.br)'
      using errcode = 'check_violation';
  end if;

  insert into public.profiles (id, nome_completo, email, papel)
  values (
    new.id,
    coalesce(
      nullif(trim(new.raw_user_meta_data ->> 'nome_completo'), ''),
      nullif(trim(new.raw_user_meta_data ->> 'full_name'), ''),
      nullif(trim(new.raw_user_meta_data ->> 'name'), ''),
      split_part(new.email, '@', 1)
    ),
    new.email,
    v_papel
  );
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.tg_cria_perfil();

-- -------------------------------------------------------------
-- O e-mail do perfil é cópia do e-mail da conta, e não pode ser
-- editado por aqui.
--
-- Sem isto, a regra do professor teria um buraco: bastaria o
-- usuário trocar o próprio e-mail para algo@unb.br na tabela
-- profiles e então se promover a professor.
-- -------------------------------------------------------------
create or replace function public.tg_email_imutavel()
returns trigger
language plpgsql
as $$
begin
  if new.email is distinct from old.email then
    raise exception 'O e-mail do perfil não pode ser alterado';
  end if;
  return new;
end;
$$;

create trigger profiles_email_imutavel
  before update on public.profiles
  for each row execute function public.tg_email_imutavel();

-- -------------------------------------------------------------
-- Row Level Security
--
-- O front é um SPA sem servidor: o navegador fala direto com a
-- API do Supabase usando uma chave que está no bundle público.
-- Estas políticas não são uma camada extra de segurança — são a
-- única que existe.
-- -------------------------------------------------------------
alter table public.profiles enable row level security;

-- Usuário logado enxerga os perfis (nome de quem publicou um
-- evento, por exemplo), mas edita apenas o próprio.
create policy "perfis visiveis para usuarios logados"
  on public.profiles for select
  to authenticated
  using (true);

create policy "usuario edita o proprio perfil"
  on public.profiles for update
  to authenticated
  using      (id = (select auth.uid()))
  with check (id = (select auth.uid()));

-- Sem política de INSERT: quem cria o perfil é o trigger.
-- Sem política de DELETE: o perfil some junto com a conta.
--
-- Nota sobre o papel 'admin': não existe tela para virar admin.
-- É definido manualmente no painel do Supabase.