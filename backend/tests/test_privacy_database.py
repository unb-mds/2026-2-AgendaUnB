"""Testes de banco (PostgreSQL/Supabase local) para privacidade, RLS, cascatas e descarte de PDFs."""

from __future__ import annotations

import json
import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from src.modules.syllabus.processing_config import ProcessingConfig, ProcessingError
from src.modules.syllabus.worker import SyllabusWorker
from syllabus_samples import approved_source
from test_security_database import as_backend, assume, database, denied, scalar


def _reject(conn, operation, sqlstate: str) -> None:
    with pytest.raises(DBAPIError) as caught:
        with conn.begin_nested():
            operation()
    assert caught.value.orig.sqlstate == sqlstate


def test_privacy_tables_rls_and_privileges(database):
    conn, users = database

    without_rls = conn.execute(
        text(
            "select c.relname from pg_class c "
            "join pg_namespace n on n.oid = c.relnamespace "
            "where n.nspname = 'public' and c.relname in ('aceites_termos', 'consentimentos', 'exclusoes_conta') "
            "and not c.relrowsecurity order by 1"
        )
    ).scalars().all()
    assert without_rls == []

    # Funções auxiliares e trigger preservam search_path = '' e são restritas a service_role.
    funcs = [
        "revogar_consentimento(uuid,text)",
        "preparar_exclusao_conta(uuid)",
        "concluir_exclusao_conta(uuid,integer)",
        "arquivos_a_descartar()",
        "registrar_descarte_arquivo(uuid)",
    ]
    for sig in funcs:
        assert not scalar(conn, "select has_function_privilege('anon', :sig, 'execute')", {"sig": f"public.{sig}"})
        assert not scalar(conn, "select has_function_privilege('authenticated', :sig, 'execute')", {"sig": f"public.{sig}"})
        assert scalar(conn, "select has_function_privilege('service_role', :sig, 'execute')", {"sig": f"public.{sig}"})

    # Semente de aceites e consentimentos para Ana e Bruno.
    conn.execute(
        text("insert into public.aceites_termos(user_id, documento, versao) values (:u, 'terms', '2026-11-18')"),
        {"u": users["ana"]},
    )
    conn.execute(
        text("insert into public.aceites_termos(user_id, documento, versao) values (:u, 'terms', '2026-11-18')"),
        {"u": users["bruno"]},
    )
    conn.execute(
        text("insert into public.consentimentos(user_id, finalidade) values (:u, 'google_agenda')"),
        {"u": users["ana"]},
    )
    conn.execute(
        text("insert into public.exclusoes_conta(status) values ('iniciada')")
    )

    # Anon não lê nem escreve nenhuma das 3 tabelas.
    assume(conn)
    for table in ("aceites_termos", "consentimentos", "exclusoes_conta"):
        denied(conn, f"select count(*) from public.{table}")

    # Authenticated lê apenas próprios registros; nunca escreve diretamente nem lê exclusoes_conta.
    assume(conn, users["ana"])
    assert scalar(conn, "select count(*) from public.aceites_termos") == 1
    assert scalar(conn, "select count(*) from public.consentimentos") == 1
    denied(conn, "select count(*) from public.exclusoes_conta")
    denied(
        conn,
        "insert into public.aceites_termos(user_id, documento, versao) values (:u, 'privacy', '2026-11-18')",
        {"u": users["ana"]},
    )
    denied(
        conn,
        "insert into public.consentimentos(user_id, finalidade) values (:u, 'google_agenda')",
        {"u": users["ana"]},
    )
    denied(conn, "delete from public.consentimentos where user_id = :u", {"u": users["ana"]})

    # Usuário com e-mail não confirmado não lê nem os próprios registros.
    as_backend(conn)
    unconfirmed = str(uuid4())
    conn.execute(
        text("insert into auth.users(id, email, raw_user_meta_data) values (:id, :email, '{}'::jsonb)"),
        {"id": unconfirmed, "email": f"unconfirmed-{unconfirmed}@unb.br"},
    )
    conn.execute(
        text("insert into public.aceites_termos(user_id, documento, versao) values (:u, 'terms', '2026-11-18')"),
        {"u": unconfirmed},
    )
    assume(conn, unconfirmed)
    assert scalar(conn, "select count(*) from public.aceites_termos") == 0


def test_original_pdf_is_discarded_and_the_plan_remains(database):
    conn, users = database
    done_plan = str(uuid4())
    pending_plan = str(uuid4())
    conn.execute(
        text(
            "insert into public.planos_ensino(id, user_id, tipo, nome_arquivo, caminho_arquivo, status, processado_em) "
            "values (:id, :u, 'particular', 'antigo.pdf', :path, 'concluido', now())"
        ),
        {"id": done_plan, "u": users["ana"], "path": f"syllabus_files/{users['ana']}/{done_plan}.pdf"},
    )
    conn.execute(
        text(
            "insert into public.planos_ensino(id, user_id, tipo, nome_arquivo, caminho_arquivo, status) "
            "values (:id, :u, 'particular', 'pendente.pdf', :path, 'pendente')"
        ),
        {"id": pending_plan, "u": users["ana"], "path": f"syllabus_files/{users['ana']}/{pending_plan}.pdf"},
    )

    to_discard = conn.execute(text("select plano_id from public.arquivos_a_descartar()")).scalars().all()
    assert uuid_list_contains(to_discard, done_plan)
    assert not uuid_list_contains(to_discard, pending_plan)

    assert scalar(conn, "select public.registrar_descarte_arquivo(:p)", {"p": pending_plan}) is False
    assert scalar(conn, "select public.registrar_descarte_arquivo(:p)", {"p": done_plan}) is True

    row = conn.execute(
        text(
            "select caminho_arquivo, arquivo_url, arquivo_descartado_em "
            "from public.planos_ensino where id = :p"
        ),
        {"p": done_plan},
    ).one()
    assert row[0] is None and row[1] is None and row[2] is not None

    # Limpar fonte sem texto_preparado nem arquivo_descartado_em viola check constraint (23514).
    _reject(
        conn,
        lambda: conn.execute(
            text("update public.planos_ensino set caminho_arquivo = null where id = :p"),
            {"p": pending_plan},
        ),
        "23514",
    )


def uuid_list_contains(items, target: str) -> bool:
    return any(str(item) == target for item in items)


def test_account_deletion_end_to_end(database):
    conn, users = database
    ana = users["ana"]
    bruno = users["bruno"]

    # Oferta para vínculo de turma.
    subj_id = scalar(
        conn,
        "insert into public.disciplinas(codigo, nome) values ('FGA0158', 'OO') returning id",
    )
    off_id = scalar(
        conn,
        "insert into public.ofertas_turma(disciplina_id, turma, ano, semestre) "
        "values (:s, '01', 2026, 2) returning id",
        {"s": subj_id},
    )
    conn.execute(
        text("insert into public.vinculos_turma(user_id, oferta_id) values (:u, :o)"),
        {"u": ana, "o": off_id},
    )
    conn.execute(
        text("insert into public.vinculos_turma(user_id, oferta_id) values (:u, :o)"),
        {"u": bruno, "o": off_id},
    )

    # Evento público de Ana (gera notificação via trigger) + salvo + agenda pessoal.
    pub_id = scalar(
        conn,
        "insert into public.eventos(autor_id, titulo, descricao, data_evento, status) "
        "values (:u, 'Evento de Ana', 'Descrição', now() + interval '1 day', 'aprovado') returning id",
        {"u": ana},
    )
    conn.execute(
        text("insert into public.eventos_salvos(user_id, event_id) values (:u, :e)"),
        {"u": ana, "e": pub_id},
    )
    conn.execute(
        text("insert into public.eventos_pessoais(user_id, titulo, data_hora) values (:u, 'Agenda Ana', now())"),
        {"u": ana},
    )

    # Plano concluído e plano em processamento (ambos com versao_aprovada_id preenchida).
    snap = approved_source("Prova 1")
    plan_done = str(uuid4())
    plan_proc = str(uuid4())
    conn.execute(
        text(
            "insert into public.planos_ensino(id, user_id, tipo, nome_arquivo, caminho_arquivo, status, processado_em) "
            "values (:id, :u, 'particular', 'legado.pdf', :path, 'concluido', now())"
        ),
        {"id": plan_done, "u": ana, "path": f"syllabus_files/{ana}/{plan_done}.pdf"},
    )
    conn.execute(
        text(
            "insert into public.planos_ensino(id, user_id, tipo, nome_arquivo, status, texto_preparado, texto_aprovado, hash_texto_aprovado, autorizado_em, enfileirado_em, versao_texto) "
            "values (:id, :u, 'particular', 'proc.pdf', 'pendente', cast(:pages as jsonb), cast(:pages as jsonb), :hash, now(), now(), 1)"
        ),
        {"id": plan_proc, "u": ana, "pages": json.dumps(snap["approved_pages"]), "hash": snap["approved_hash"]},
    )

    ver_shared = scalar(
        conn,
        "update public.versoes_plano set visibilidade = 'compartilhada', compartilhada_em = now() "
        "where plano_id = :p and numero = 1 returning id",
        {"p": plan_done},
    )
    ver_proc = scalar(
        conn,
        "select id from public.versoes_plano where plano_id = :p and numero = 1",
        {"p": plan_proc},
    )
    conn.execute(
        text("update public.planos_ensino set versao_aprovada_id = :v where id = :p"),
        {"v": ver_shared, "p": plan_done},
    )
    conn.execute(
        text(
            "update public.planos_ensino set versao_aprovada_id = :v, status = 'processando', processamento_iniciado_em = now() "
            "where id = :p"
        ),
        {"v": ver_proc, "p": plan_proc},
    )

    cand_id = scalar(
        conn,
        "insert into public.avaliacoes(plano_id, versao_id, titulo) values (:p, :v, 'Prova Compartilhada') returning id",
        {"p": plan_done, "v": ver_shared},
    )

    # Operação de importação da própria Ana + cópia independente importada por Bruno.
    op_ana = scalar(
        conn,
        "insert into public.operacoes_importacao(user_id, chave, versao_id, conteudo_hash) "
        "values (:u, 'operacao-ana-01', :v, repeat('a', 64)) returning id",
        {"u": ana, "v": ver_shared},
    )
    conn.execute(
        text(
            "insert into public.itens_importacao(operacao_id, avaliacao_id, resultado) "
            "values (:op, :c, 'criado')"
        ),
        {"op": op_ana, "c": cand_id},
    )
    conn.execute(
        text(
            "insert into public.eventos_pessoais(user_id, titulo, data_hora, origem_plano_id, origem_avaliacao_id, origem_versao_id, origem_trecho) "
            "values (:u, 'Cópia Bruno', now(), :p, :c, :v, 'Prova 1')"
        ),
        {"u": bruno, "p": plan_done, "c": cand_id, "v": ver_shared},
    )

    # Google Calendar, aceites e consentimentos.
    conn.execute(
        text(
            "insert into public.google_calendar_connections(user_id, google_sub, google_email, granted_scope) "
            "values (:u, :sub, 'ana@unb.br', 'scope')"
        ),
        {"u": ana, "sub": f"sub-{ana}"},
    )
    conn.execute(
        text(
            "insert into public.google_calendar_oauth_states(state_hash, user_id, agenda_email, encrypted_code_verifier, expires_at) "
            "values (repeat('b', 64), :u, 'ana@unb.br', 'enc', now() + interval '5 min')"
        ),
        {"u": ana},
    )
    conn.execute(
        text("insert into public.aceites_termos(user_id, documento, versao) values (:u, 'terms', '2026-11-18')"),
        {"u": ana},
    )
    conn.execute(
        text("insert into public.consentimentos(user_id, finalidade) values (:u, 'google_agenda')"),
        {"u": ana},
    )

    prep = conn.execute(
        text("select exclusao_id, caminhos_arquivos from public.preparar_exclusao_conta(:u)"),
        {"u": ana},
    ).one()
    exclusao_id = prep.exclusao_id
    assert f"syllabus_files/{ana}/{plan_done}.pdf" in list(prep.caminhos_arquivos)

    conn.execute(text("delete from auth.users where id = :u"), {"u": ana})
    conn.execute(
        text("select public.concluir_exclusao_conta(:id, 1)"),
        {"id": exclusao_id},
    )

    # Todos os registros de Ana foram apagados em cascata.
    for table, col in (
        ("profiles", "id"),
        ("eventos_pessoais", "user_id"),
        ("eventos_salvos", "user_id"),
        ("notificacoes", "usuario_id"),
        ("eventos", "autor_id"),
        ("vinculos_turma", "user_id"),
        ("planos_ensino", "user_id"),
        ("versoes_plano", "autor_id"),
        ("operacoes_importacao", "user_id"),
        ("google_calendar_connections", "user_id"),
        ("google_calendar_oauth_states", "user_id"),
        ("aceites_termos", "user_id"),
        ("consentimentos", "user_id"),
    ):
        assert scalar(conn, f"select count(*) from public.{table} where {col} = :u", {"u": ana}) == 0
    assert scalar(conn, "select count(*) from public.avaliacoes where plano_id in (:p1, :p2)", {"p1": plan_done, "p2": plan_proc}) == 0

    # Cópia independente de Bruno permanece preservada com origem_versao_id nulificada.
    bruno_copy = conn.execute(
        text(
            "select titulo, origem_plano_id, origem_avaliacao_id, origem_versao_id, origem_trecho "
            "from public.eventos_pessoais where user_id = :u"
        ),
        {"u": bruno},
    ).one()
    assert bruno_copy[0] == "Cópia Bruno"
    assert str(bruno_copy[1]) == plan_done
    assert str(bruno_copy[2]) == str(cand_id)
    assert bruno_copy[3] is None
    assert bruno_copy[4] == "Prova 1"

    record = conn.execute(
        text(
            "select status, planos_removidos, eventos_pessoais_removidos, eventos_publicos_removidos, arquivos_storage_removidos "
            "from public.exclusoes_conta where id = :id"
        ),
        {"id": exclusao_id},
    ).one()
    assert tuple(record) == ("concluida", 2, 1, 1, 1)


def test_cross_user_version_author_deletion_unblocks_processing_cascade(database):
    conn, users = database
    u1 = users["ana"]
    u2 = users["bruno"]
    snap = approved_source("Prova 1")
    p_u1 = str(uuid4())

    conn.execute(
        text(
            "insert into public.planos_ensino("
            "  id, user_id, tipo, nome_arquivo, status, texto_preparado, texto_aprovado, "
            "  hash_texto_aprovado, autorizado_em, enfileirado_em, versao_texto"
            ") values ("
            "  :id, :u, 'particular', 'proc.pdf', 'pendente', cast(:pages as jsonb), "
            "  cast(:pages as jsonb), :hash, now(), now(), 1"
            ")"
        ),
        {"id": p_u1, "u": u1, "pages": json.dumps(snap["approved_pages"]), "hash": snap["approved_hash"]},
    )
    v_u2 = scalar(
        conn,
        "insert into public.versoes_plano(plano_id, numero, autor_id) values (:p, 2, :u) returning id",
        {"p": p_u1, "u": u2},
    )
    conn.execute(
        text(
            "update public.planos_ensino "
            "set versao_aprovada_id = :v, status = 'processando', processamento_iniciado_em = now() "
            "where id = :p"
        ),
        {"v": v_u2, "p": p_u1},
    )

    # Enquanto u1 e v_u2 existem, alterações explícitas no snapshot em processamento continuam bloqueadas (42501).
    _reject(
        conn,
        lambda: conn.execute(
            text("update public.planos_ensino set versao_aprovada_id = null where id = :p"),
            {"p": p_u1},
        ),
        "42501",
    )
    _reject(
        conn,
        lambda: conn.execute(
            text("update public.planos_ensino set versao_texto = 2 where id = :p"),
            {"p": p_u1},
        ),
        "42501",
    )

    # Ao excluir u2 (autor de v_u2), ON DELETE SET NULL limpa versao_aprovada_id no plano de u1 sem bloquear.
    conn.execute(text("delete from auth.users where id = :u"), {"u": u2})

    row = conn.execute(
        text("select status, versao_aprovada_id from public.planos_ensino where id = :p"),
        {"p": p_u1},
    ).one()
    assert row[0] == "processando"
    assert row[1] is None


def test_last_admin_blocked_and_second_admin_allowed_in_db(database):
    conn, users = database
    conn.execute(
        text("update public.profiles set papel = 'student' where papel = 'admin' and id <> :id"),
        {"id": users["admin"]},
    )
    _reject(
        conn,
        lambda: conn.execute(text("select * from public.preparar_exclusao_conta(:u)"), {"u": users["admin"]}),
        "55000",
    )
    second_admin = str(uuid4())
    conn.execute(
        text("insert into auth.users(id, email, email_confirmed_at, raw_user_meta_data) values (:id, :email, now(), '{}'::jsonb)"),
        {"id": second_admin, "email": f"admin2-{second_admin}@unb.br"},
    )
    conn.execute(text("update public.profiles set papel = 'admin' where id = :id"), {"id": second_admin})
    row = conn.execute(text("select * from public.preparar_exclusao_conta(:u)"), {"u": users["admin"]}).one()
    assert row.exclusao_id is not None


def test_worker_completion_after_account_deletion_on_postgres():
    url = os.getenv("TEST_SUPABASE_DB_URL")
    if not url:
        pytest.skip("TEST_SUPABASE_DB_URL not configured")
    assert make_url(url).host in ("localhost", "127.0.0.1"), "Local database only"

    from sqlalchemy.orm import sessionmaker

    engine = create_engine(url, connect_args={"options": "-c statement_timeout=10000"})
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    owner = str(uuid4())
    snap = approved_source("Prova 1 em 20/11/2026")
    plan_id = str(uuid4())

    with engine.begin() as conn:
        conn.execute(
            text("insert into auth.users(id, email, email_confirmed_at, raw_user_meta_data) values (:id, :email, now(), '{}'::jsonb)"),
            {"id": owner, "email": f"s8d01-worker-{owner}@unb.br"},
        )
        conn.execute(
            text(
                "insert into public.planos_ensino(id, user_id, tipo, nome_arquivo, status, texto_preparado, texto_aprovado, hash_texto_aprovado, autorizado_em, enfileirado_em, versao_texto) "
                "values (:id, :u, 'particular', 'worker.pdf', 'pendente', cast(:pages as jsonb), cast(:pages as jsonb), :hash, now(), now(), 1)"
            ),
            {"id": plan_id, "u": owner, "pages": json.dumps(snap["approved_pages"]), "hash": snap["approved_hash"]},
        )

    exclusao_id = None
    try:
        cfg = ProcessingConfig(
            provider_terms_ready=True,
            api_key="fake",
            model="gemini-test",
            lease_seconds=300,
            max_attempts=3,
            retry_delay_seconds=30,
            rate_limit_delay_seconds=60,
            min_interval_seconds=0,
        )
        worker = SyllabusWorker(Session, None, None, cfg)
        lease = worker.claim()
        assert lease is not None and str(lease.id) == plan_id

        with engine.begin() as conn:
            exclusao_id = conn.execute(
                text("select exclusao_id from public.preparar_exclusao_conta(:u)"),
                {"u": owner},
            ).scalar_one()
            conn.execute(text("delete from auth.users where id = :u"), {"u": owner})
            conn.execute(text("select public.concluir_exclusao_conta(:id, 0)"), {"id": exclusao_id})

        worker.fail(lease, ProcessingError("erro_interno", retryable=True), 15)

        with engine.connect() as conn:
            assert scalar(conn, "select count(*) from public.planos_ensino where id = :p", {"p": plan_id}) == 0
    finally:
        with engine.begin() as conn:
            conn.execute(text("delete from auth.users where id = :u"), {"u": owner})
            if exclusao_id is not None:
                conn.execute(text("delete from public.exclusoes_conta where id = :id"), {"id": exclusao_id})
        engine.dispose()
