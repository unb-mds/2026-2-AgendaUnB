"""Pré-requisitos do worker; não substituem a suíte comportamental de RLS."""
import os
import sys
from collections.abc import Mapping
from decimal import Decimal

from sqlalchemy import text

from src.modules.syllabus.processing_config import ProcessingConfig


def privacy_checks(connection) -> dict[str, bool]:
    if connection.dialect.name != "postgresql":
        return {"postgresql": False}
    result = connection.execute(text("""
      with private_tables as (
        select c.oid, c.relname, c.relrowsecurity
        from pg_catalog.pg_class c join pg_catalog.pg_namespace n on n.oid=c.relnamespace
        where n.nspname='public' and c.relname in ('planos_ensino','avaliacoes')
      ), private_policies as (
        select * from pg_catalog.pg_policies
        where schemaname='public' and tablename in ('planos_ensino','avaliacoes')
          and permissive='PERMISSIVE'
      ), review_function as (
        select p.* from pg_catalog.pg_proc p
        where p.oid=to_regprocedure('public.revisar_candidatos_plano(uuid,jsonb)')
      )
      select
        exists(select 1 from supabase_migrations.schema_migrations where version='20261110120000') as migration,
        ((select count(*)=2 and bool_and(relrowsecurity) from private_tables)
          and exists(select 1 from pg_catalog.pg_class where oid='storage.objects'::regclass and relrowsecurity)) as rls,
        not exists(select 1 from private_tables t where
          has_table_privilege('anon',t.oid,'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          or has_any_column_privilege('anon',t.oid,'SELECT,INSERT,UPDATE,REFERENCES')
          or has_table_privilege('authenticated',t.oid,'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
          or has_any_column_privilege('authenticated',t.oid,'INSERT,UPDATE,REFERENCES')
          or not has_table_privilege('authenticated',t.oid,'SELECT')) as client_privileges,
        ((select count(*)=3 from private_policies) and
          (select count(*)=2 from private_policies where cmd='SELECT'
            and roles=array['authenticated']::name[] and position('auth.uid()' in qual)>0
            and (tablename,policyname) in (
              ('planos_ensino','planos particulares: usuario le apenas os proprios planos'),
              ('avaliacoes','dono le avaliacoes legadas')))
          and exists(select 1 from private_policies where tablename='avaliacoes'
            and policyname='leitura de candidatos de versoes compartilhadas'
            and cmd='SELECT' and roles=array['authenticated']::name[]
            and qual='pode_ler_versao(versao_id)')) as owner_policies,
        exists(select 1 from review_function p where p.prosecdef
          and p.proconfig @> array['search_path=""']
          and has_function_privilege('authenticated',p.oid,'EXECUTE')
          and not has_function_privilege('anon',p.oid,'EXECUTE')
          and not has_function_privilege('service_role',p.oid,'EXECUTE')) as review_privileges,
        exists(select 1 from pg_catalog.pg_trigger where not tgisinternal and tgenabled in ('O','A')
          and tgrelid='public.planos_ensino'::regclass and tgname='planos_preserva_dono') as ownership_triggers,
        (to_regclass('public.candidatos_avaliacao') is null and
          exists(select 1 from pg_catalog.pg_constraint where conrelid='public.avaliacoes'::regclass
            and conname='avaliacoes_versao_do_plano' and contype='f')) as canonical_versions,
        exists(select 1 from storage.buckets where id='syllabus_files' and not public
          and file_size_limit between 1 and 10485760
          and allowed_mime_types=array['application/pdf']) as private_bucket,
        ((select count(*)=2 from pg_catalog.pg_policies where schemaname='storage' and tablename='objects' and permissive='PERMISSIVE')
          and (select count(*)=1 from pg_catalog.pg_policies where schemaname='storage' and tablename='objects' and permissive='PERMISSIVE'
            and roles=array['authenticated']::name[] and cmd='SELECT'
            and position('auth.uid()' in coalesce(qual,with_check))>0
            and policyname='planos: usuario le apenas os proprios arquivos')
          and exists(select 1 from pg_catalog.pg_policies where schemaname='storage' and tablename='objects' and permissive='PERMISSIVE'
            and policyname='planos: back-end le todos os arquivos' and cmd='SELECT'
            and roles=array['service_role']::name[] and position('syllabus_files' in qual)>0))
          as storage_policies,
        exists(select 1 from pg_catalog.pg_trigger where not tgisinternal and tgenabled in ('O','A')
          and tgrelid='public.planos_ensino'::regclass and tgname='planos_preserva_texto_autorizado') as approved_snapshot_trigger
    """)).mappings().one()
    return {name: bool(value) for name, value in result.items()}


def check_local_syllabus_readiness(
    connection, env: Mapping[str, str] | None = None
) -> tuple[int, list[str]]:
    """Valida políticas RLS e parâmetros locais da extração de planos sem expor segredos."""
    env = os.environ if env is None else env
    worker_enabled = env.get("SYLLABUS_WORKER_ENABLED", "false").lower() == "true"
    privacy_ready = env.get("SYLLABUS_PRIVACY_READY", "false").lower() == "true"
    terms_ready = env.get("SYLLABUS_PROVIDER_TERMS_READY", "false").lower() == "true"
    has_api_key = bool(env.get("GEMINI_API_KEY", "").strip().strip('"').strip("'"))
    has_fallback_key = bool(env.get("SYLLABUS_FALLBACK_API_KEY", "").strip().strip('"').strip("'"))

    checks = privacy_checks(connection)
    if checks.get("postgresql") is False:
        if worker_enabled:
            return 1, ["O worker de planos exige PostgreSQL com migrações e políticas RLS aplicadas."]
        return 0, ["[INFO] Banco não-PostgreSQL configurado; verificação de políticas RLS ignorada."]

    missing = [name for name, passed in checks.items() if not passed]
    if missing:
        return 1, [
            f"Pré-requisitos de privacidade de planos ausentes: {', '.join(missing)}.",
            "Revise as migrações pendentes. No ambiente local, execute make db-migrate.",
        ]

    try:
        model = env.get("GEMINI_MODEL", ProcessingConfig.model).strip()
        if model != ProcessingConfig.model and not all(
            env.get(name)
            for name in ("GEMINI_INPUT_USD_PER_MILLION", "GEMINI_OUTPUT_USD_PER_MILLION")
        ):
            raise ValueError("Ao alterar GEMINI_MODEL, configure os dois preços por milhão de tokens.")
        config = ProcessingConfig(
            model=model,
            api_key=env.get("GEMINI_API_KEY", "").strip().strip('"').strip("'"),
            provider_terms_ready=terms_ready,
            fallback_provider=env.get("SYLLABUS_FALLBACK_PROVIDER", "").strip().lower(),
            fallback_api_key=env.get("SYLLABUS_FALLBACK_API_KEY", "").strip().strip('"').strip("'"),
            fallback_model=env.get("SYLLABUS_FALLBACK_MODEL", "").strip(),
            fallback_timeout_seconds=float(env.get("SYLLABUS_FALLBACK_TIMEOUT_SECONDS", "8")),
            timeout_seconds=float(env.get("SYLLABUS_AI_TIMEOUT_SECONDS", "12")),
            attempt_timeout_seconds=float(env.get("SYLLABUS_ATTEMPT_TIMEOUT_SECONDS", "18")),
            max_attempts=int(env.get("SYLLABUS_MAX_ATTEMPTS", "2")),
            rate_limit_delay_seconds=int(env.get("SYLLABUS_RATE_LIMIT_DELAY_SECONDS", "65")),
            min_interval_seconds=float(env.get("SYLLABUS_MIN_INTERVAL_SECONDS", "4.0")),
            max_file_cost_usd=Decimal(env.get("SYLLABUS_MAX_FILE_COST_USD", "0.06")),
            input_usd_per_million=Decimal(env.get("GEMINI_INPUT_USD_PER_MILLION", "0.30")),
            output_usd_per_million=Decimal(env.get("GEMINI_OUTPUT_USD_PER_MILLION", "2.50")),
        )
    except (ValueError, ArithmeticError) as exc:
        return 1, [f"Configuração de processamento de planos inválida: {exc}"]

    messages = ["Políticas de privacidade e RLS de planos compatíveis."]
    if worker_enabled and privacy_ready and terms_ready and has_api_key:
        messages.append(f"[OK] Extração de planos com Gemini pronta (modelo: {config.model}).")
    elif has_api_key:
        missing_flags = [
            name
            for name, ready in (
                ("SYLLABUS_WORKER_ENABLED", worker_enabled),
                ("SYLLABUS_PRIVACY_READY", privacy_ready),
                ("SYLLABUS_PROVIDER_TERMS_READY", terms_ready),
            )
            if not ready
        ]
        messages.append(
            f"[AVISO] GEMINI_API_KEY definida, mas faltam flags em true no .env: {', '.join(missing_flags)}."
        )
    elif worker_enabled:
        messages.append(
            "[AVISO] SYLLABUS_WORKER_ENABLED=true, mas GEMINI_API_KEY está vazia no .env; worker ficará inativo."
        )
    else:
        messages.append("[INFO] Worker Gemini desativado no .env (modo manual/sem chave).")
    if config.fallback_provider:
        if worker_enabled and privacy_ready and terms_ready and has_api_key and has_fallback_key:
            messages.append(f"[OK] Fallback explícito habilitado (provedor: {config.fallback_provider}, modelo: {config.fallback_model}).")
        elif not has_fallback_key:
            messages.append(f"[INFO] {config.fallback_provider} configurado, mas sem SYLLABUS_FALLBACK_API_KEY; fallback inativo.")
        else:
            messages.append(f"[AVISO] Fallback {config.fallback_provider} aguarda as flags e a chave Gemini do worker.")
    return 0, messages


def main() -> int:
    """Executa o preflight local de privacidade e configuração da extração de planos."""
    from sqlalchemy.exc import SQLAlchemyError
    from src.database.connection import engine

    try:
        with engine.connect() as connection:
            code, messages = check_local_syllabus_readiness(connection)
    except SQLAlchemyError:
        print("Banco inacessível. Confira DATABASE_URL e inicie o Supabase local.", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    stream = sys.stderr if code != 0 else sys.stdout
    for message in messages:
        print(message, file=stream)
    return code


if __name__ == "__main__":
    sys.exit(main())
