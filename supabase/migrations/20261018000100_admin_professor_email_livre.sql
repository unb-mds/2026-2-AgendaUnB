-- O cadastro e a autopromoção continuam exigindo @unb.br.
-- Um administrador pode atribuir professor a qualquer conta pela RPC protegida.
alter table public.profiles drop constraint professor_exige_email_institucional;

create or replace function public.tg_protege_papel()
returns trigger
language plpgsql
as $$
begin
  if new.papel is distinct from old.papel
     and current_user in ('anon', 'authenticated')
     and not (
       old.papel = 'student'
       and new.papel = 'professor'
       and new.email ~* '@unb\.br$'
     )
  then
    raise exception 'Alteração de papel não permitida'
      using errcode = '42501';
  end if;
  return new;
end;
$$;
