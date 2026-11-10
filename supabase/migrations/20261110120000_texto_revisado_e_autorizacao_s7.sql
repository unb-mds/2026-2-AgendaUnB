-- S7-B01: preparação local sem retenção do PDF; somente snapshot autorizado entra na fila.
-- Não migra PDFs existentes para a IA e não concede autorização retroativa.
alter table public.planos_ensino
  add column texto_preparado jsonb,
  add column texto_aprovado jsonb,
  add column hash_texto_aprovado text,
  add column autorizado_em timestamptz,
  add column enfileirado_em timestamptz,
  add column duracao_preparacao_ms integer check (duracao_preparacao_ms >= 0),
  add column versao_texto integer not null default 0 check (versao_texto >= 0);

alter table public.planos_ensino drop constraint planos_particular_exige_arquivo;
alter table public.planos_ensino drop constraint planos_tipo_arquivo_pdf;
alter table public.planos_ensino
  add constraint planos_tipo_arquivo_digital check (tipo_arquivo in ('pdf','text')),
  add constraint planos_particular_exige_fonte check (
    tipo <> 'particular' or caminho_arquivo is not null or texto_preparado is not null),
  add constraint planos_texto_preparado_limitado check (
    texto_preparado is null or (jsonb_typeof(texto_preparado)='array'
      and jsonb_array_length(texto_preparado) between 1 and 10
      and octet_length(texto_preparado::text) <= 260000)),
  add constraint planos_autorizacao_coerente check (
    (autorizado_em is null and texto_aprovado is null and hash_texto_aprovado is null
      and enfileirado_em is null and versao_texto=0)
    or (autorizado_em is not null and texto_aprovado is not null
      and jsonb_typeof(texto_aprovado)='array'
      and jsonb_array_length(texto_aprovado) between 1 and 10
      and octet_length(texto_aprovado::text) <= 260000
      and hash_texto_aprovado is not null and hash_texto_aprovado ~ '^[a-f0-9]{64}$'
      and enfileirado_em is not null and versao_texto > 0));

alter table public.candidatos_avaliacao alter column pagina_origem drop not null;
-- Linhas históricas de outros tipos continuam legíveis; novas escritas são restritas.
alter table public.candidatos_avaliacao add constraint candidatos_s7_prova_trabalho
  check (versao_processamento <> 'syllabus-v3-approved-text' or tipo in ('prova','trabalho'));

create function public.tg_preserva_texto_autorizado()
returns trigger language plpgsql set search_path = '' as $$
begin
  if old.status='processando' and
     (new.texto_aprovado, new.hash_texto_aprovado, new.autorizado_em, new.versao_texto)
       is distinct from
     (old.texto_aprovado, old.hash_texto_aprovado, old.autorizado_em, old.versao_texto) then
    raise exception 'O snapshot em processamento não pode ser alterado' using errcode='42501';
  end if;
  return new;
end;
$$;
create trigger planos_preserva_texto_autorizado before update on public.planos_ensino
  for each row execute function public.tg_preserva_texto_autorizado();
revoke all on function public.tg_preserva_texto_autorizado() from public, anon, authenticated;

-- Concilia as políticas conhecidas das branches S6-D02. Somente leitura do dono
-- é permitida ao cliente; novas colunas de texto não recebem escrita direta.
do $$
declare item record;
begin
  for item in select tablename, policyname from pg_policies
    where schemaname='public' and tablename in ('planos_ensino','candidatos_avaliacao','avaliacoes') loop
    execute format('drop policy %I on public.%I',item.policyname,item.tablename);
  end loop;
end;
$$;
revoke all on public.planos_ensino,public.candidatos_avaliacao,public.avaliacoes from anon,authenticated;
grant select on public.planos_ensino,public.candidatos_avaliacao,public.avaliacoes to authenticated;
grant all on public.planos_ensino,public.candidatos_avaliacao,public.avaliacoes to service_role;
create policy "planos particulares: usuario le apenas os proprios planos"
  on public.planos_ensino for select to authenticated using (user_id=(select auth.uid()));
create policy "dono le candidatos privados" on public.candidatos_avaliacao for select to authenticated
  using (exists(select 1 from public.planos_ensino p where p.id=plano_id and p.user_id=(select auth.uid())));
create policy "dono le avaliacoes legadas" on public.avaliacoes for select to authenticated
  using (exists(select 1 from public.planos_ensino p where p.id=plano_id and p.user_id=(select auth.uid())));

create index planos_fila_texto_autorizado on public.planos_ensino(status,enfileirado_em)
  where autorizado_em is not null and status in ('pendente','processando');
comment on column public.planos_ensino.texto_aprovado is
  'Snapshot privado exato autorizado pelo dono. Somente o servidor escreve. Não contém PDF.';

-- Novos PDFs não são retidos. Fechar o caminho de upload direto pelo cliente;
-- arquivos históricos continuam privados e legíveis somente pelo dono.
drop policy if exists "planos: usuario envia para a propria pasta" on storage.objects;
drop policy if exists "planos: usuario le apenas os proprios arquivos" on storage.objects;
create policy "planos: usuario le apenas os proprios arquivos" on storage.objects
  for select to authenticated using (
    bucket_id='syllabus_files'
    and name ~* ('^' || (select auth.uid())::text || '/[^/]+[.]pdf$')
    and position(chr(92) in name)=0);
