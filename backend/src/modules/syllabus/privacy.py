"""Pré-requisitos do worker; não substituem a suíte comportamental de RLS."""
from sqlalchemy import text


def privacy_checks(connection) -> dict[str, bool]:
    if connection.dialect.name != "postgresql":
        return {"postgresql": False}
    result = connection.execute(text("""
      with private_tables as (
        select c.oid, c.relname, c.relrowsecurity
        from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
        where n.nspname='public' and c.relname in ('planos_ensino','candidatos_avaliacao','avaliacoes')
      ), private_policies as (
        select * from pg_catalog.pg_policies
        where schemaname='public' and tablename in ('planos_ensino','candidatos_avaliacao','avaliacoes')
      ), review_function as (
        select p.* from pg_catalog.pg_proc p
        where p.oid=to_regprocedure('public.revisar_candidatos_plano(uuid,jsonb)')
      )
      select
        exists(select 1 from supabase_migrations.schema_migrations where version='20261109130000') as migration,
        ((select count(*)=3 and bool_and(relrowsecurity) from private_tables)
          and exists(select 1 from pg_catalog.pg_class where oid='storage.objects'::regclass and relrowsecurity)) as rls,
        not exists(select 1 from private_tables t where
          has_table_privilege('anon',t.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          or has_any_column_privilege('anon',t.oid,'SELECT,INSERT,UPDATE,REFERENCES')
          or has_table_privilege('authenticated',t.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          or has_any_column_privilege('authenticated',t.oid,'INSERT,UPDATE,REFERENCES')
          or not has_table_privilege('authenticated',t.oid,'SELECT')) as client_privileges,
        ((select count(*)=3 from private_policies) and
          (select count(*)=3 from private_policies where cmd='SELECT'
            and roles=array['authenticated']::name[] and position('auth.uid()' in qual)>0
            and (tablename,policyname) in (
              ('planos_ensino','planos particulares: usuario le apenas os proprios planos'),
              ('candidatos_avaliacao','dono le candidatos privados'),
              ('avaliacoes','dono le avaliacoes legadas')))) as owner_policies,
        exists(select 1 from review_function p where p.prosecdef
          and p.proconfig @> array['search_path=""']
          and has_function_privilege('authenticated',p.oid,'EXECUTE')
          and not has_function_privilege('anon',p.oid,'EXECUTE')
          and not has_function_privilege('service_role',p.oid,'EXECUTE')) as review_privileges,
        (select count(*)=2 from pg_catalog.pg_trigger where not tgisinternal and tgenabled in ('O','A')
          and (tgrelid,tgname) in (
            ('public.planos_ensino'::regclass,'planos_preserva_dono'),
            ('public.candidatos_avaliacao'::regclass,'candidatos_valida_dono_evento'))) as ownership_triggers,
        exists(select 1 from storage.buckets where id='syllabus_files' and not public
          and file_size_limit between 1 and 10485760
          and allowed_mime_types=array['application/pdf']) as private_bucket,
        ((select count(*)=3 from pg_catalog.pg_policies where schemaname='storage' and tablename='objects')
          and (select count(*)=2 from pg_catalog.pg_policies where schemaname='storage' and tablename='objects'
            and roles=array['authenticated']::name[] and cmd in ('SELECT','INSERT')
            and position('auth.uid()' in coalesce(qual,with_check))>0
            and policyname in ('planos: usuario envia para a propria pasta','planos: usuario le apenas os proprios arquivos'))
          and exists(select 1 from pg_catalog.pg_policies where schemaname='storage' and tablename='objects'
            and policyname='planos: back-end le todos os arquivos' and cmd='SELECT'
            and roles=array['service_role']::name[] and position('syllabus_files' in qual)>0))
          as storage_policies
    """)).mappings().one()
    return {name: bool(value) for name, value in result.items()}
