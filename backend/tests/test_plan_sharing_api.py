"""Testes de contrato HTTP para compartilhamento, versões, procedência e votos (S8-B01 / #77)."""
from datetime import date, datetime, time as dt_time, timezone
from uuid import uuid4

from sqlalchemy import select

from src.database.models import (
    CatalogSync,
    ClassOffering,
    PersonalEvent,
    Profile,
    Subject,
    Syllabus,
    SyllabusCandidate,
    SyllabusVersion,
)
from src.middlewares.auth import CurrentUser


def _seed_offering_and_plan(TestSession, author_id, *, shared=False, status="concluido", with_offering=True):
    offering_id = uuid4()
    syllabus_id = uuid4()
    version_id = uuid4()
    c1_id = uuid4()
    c2_id = uuid4()

    with TestSession() as db:
        if db.get(Profile, author_id) is None:
            db.add(Profile(id=author_id, papel="student", nome_completo="Ana Autora"))
        if with_offering:
            sync = CatalogSync(
                status="concluida",
                units=[{"id": 673, "code": "FCTE", "name": "Faculdade do Gama"}],
                periods=["2026.2"],
            )
            subject = Subject(
                source="followw",
                source_id=f"sub-{offering_id.hex[:8]}",
                code="FGA0138",
                name="Métodos de Desenvolvimento de Software",
                unit="673",
            )
            db.add_all([sync, subject])
            db.flush()
            offering = ClassOffering(
                id=offering_id,
                subject_id=subject.id,
                source="followw",
                source_id=f"off-{offering_id.hex[:8]}",
                class_number="01",
                year=2026,
                semester=2,
                teacher="Prof. Carla",
                schedule="35M34",
                publication_id=sync.id,
            )
            db.add(offering)
            db.flush()

        plan = Syllabus(
            id=syllabus_id,
            user_id=author_id,
            offering_id=offering_id if with_offering else None,
            file_name="plano-privado-autora.pdf",
            file_path=f"syllabus_files/{author_id}/plano.pdf",
            file_size=2048,
            file_type="pdf",
            status=status,
            extracted_events_count=2,
            prepared_pages=[{"pagina": 1, "texto": "Texto privado do autor"}],
        )
        db.add(plan)
        db.flush()

        v1 = SyllabusVersion(
            id=version_id,
            syllabus_id=syllabus_id,
            number=1,
            author_id=author_id,
            author_role="student",
            visibility="compartilhada" if shared else "privada",
            shared_at=datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc) if shared else None,
        )
        db.add(v1)
        db.flush()
        plan.approved_version_id = v1.id

        c1 = SyllabusCandidate(
            id=c1_id,
            syllabus_id=syllabus_id,
            version_id=v1.id,
            order=0,
            title="Prova 1",
            kind="prova",
            starts_at=datetime(2026, 11, 20, 13, 0, tzinfo=timezone.utc),
            data_sugerida=date(2026, 11, 20),
            hora_sugerida=dt_time(10, 0),
            ambiguous=False,
            source_page=2,
            source_excerpt="Prova 1 em 20/11 às 10h.",
            status="pendente",
        )
        c2 = SyllabusCandidate(
            id=c2_id,
            syllabus_id=syllabus_id,
            version_id=v1.id,
            order=1,
            title="Entrega Final",
            kind="trabalho",
            starts_at=None,
            data_sugerida=date(2026, 12, 5),
            ambiguous=True,
            campos_ambiguos=["hora"],
            source_page=4,
            source_excerpt="Entrega final em 05/12.",
            status="pendente",
        )
        db.add_all([c1, c2])
        db.commit()

    return {
        "offering_id": offering_id if with_offering else None,
        "syllabus_id": syllabus_id,
        "version_id": version_id,
        "candidates": [c1_id, c2_id],
    }


def _ensure_profile(TestSession, user_id, role, name):
    with TestSession() as db:
        profile = db.get(Profile, user_id)
        if profile is None:
            db.add(Profile(id=user_id, papel=role, nome_completo=name))
        else:
            profile.papel = role
            profile.nome_completo = name
        db.commit()


def test_two_followers_read_and_import_to_independent_private_agendas_while_outsider_and_visitor_are_refused(api):
    """Critério 1: Dois seguidores leem e importam para agendas independentes; visitante e sem vínculo são recusados; vínculo autodeclarado."""
    client, TestSession, authenticated_user, _ = api
    ana_id = authenticated_user["value"].id
    bruno_id = uuid4()
    carla_id = uuid4()
    outsider_id = uuid4()

    _ensure_profile(TestSession, ana_id, "student", "Ana Autora")
    _ensure_profile(TestSession, bruno_id, "student", "Bruno Seguidor")
    _ensure_profile(TestSession, carla_id, "student", "Carla Seguidora")
    _ensure_profile(TestSession, outsider_id, "student", "Diego Sem Vínculo")

    seeded = _seed_offering_and_plan(TestSession, ana_id, shared=False)
    oid = seeded["offering_id"]
    sid = seeded["syllabus_id"]
    v1_id = seeded["version_id"]
    c1_id, _ = seeded["candidates"]

    # Autora compartilha voluntariamente a versão revisada
    shared_res = client.put(f"/api/v1/syllabus/{sid}/versions/{v1_id}/sharing")
    assert shared_res.status_code == 200
    assert shared_res.json()["visibility"] == "compartilhada"
    assert shared_res.json()["membershipType"] == "autodeclarado"
    assert "autodeclarado" in shared_res.json()["sharedContentNotice"].lower()
    assert "pdf original é descartado" in shared_res.json()["sharedContentNotice"].lower()

    # Usuário autenticado sem vínculo com a turma é recusado na leitura e na importação
    authenticated_user["value"] = CurrentUser(id=outsider_id, role="student")
    assert client.get(f"/api/v1/class-offerings/{oid}/shared-plans").status_code == 403
    assert client.get(f"/api/v1/syllabus/{sid}/versions/{v1_id}").status_code == 404
    assert client.get(f"/api/v1/syllabus/{sid}").status_code == 404
    assert client.post(
        f"/api/v1/syllabus/{sid}/confirm",
        headers={"Idempotency-Key": "outsider-import-01"},
        json={"versionId": str(v1_id), "candidates": [{"candidateId": str(c1_id)}]},
    ).status_code == 404

    # Seguidor 1 (Bruno) segue a turma, lê a versão compartilhada e importa para sua agenda privada
    authenticated_user["value"] = CurrentUser(id=bruno_id, role="student")
    assert client.put(f"/api/v1/me/class-offerings/{oid}").status_code == 204
    bruno_list = client.get(f"/api/v1/class-offerings/{oid}/shared-plans")
    assert bruno_list.status_code == 200
    assert bruno_list.json()["membership_type"] == "autodeclarado"
    assert "autodeclarado" in bruno_list.json()["shared_content_notice"].lower()
    assert bruno_list.json()["total"] == 1
    assert bruno_list.json()["items"][0]["id"] == str(v1_id)

    # Detalhe do plano para seguidor nunca expõe nome/caminho/tamanho do arquivo ou texto bruto privado da autora
    bruno_detail = client.get(f"/api/v1/syllabus/{sid}")
    assert bruno_detail.status_code == 200
    assert bruno_detail.json()["fileName"] is None
    assert bruno_detail.json()["filePath"] is None
    assert bruno_detail.json()["fileSize"] is None
    assert bruno_detail.json()["preparedTextAvailable"] is False
    assert client.get(f"/api/v1/syllabus/{sid}/text").status_code == 404

    bruno_import = client.post(
        f"/api/v1/syllabus/{sid}/confirm",
        headers={"Idempotency-Key": "bruno-import-v1-001"},
        json={
            "versionId": str(v1_id),
            "candidates": [{"candidateId": str(c1_id), "title": "Prova 1 (Agenda Bruno)"}],
        },
    )
    assert bruno_import.status_code == 200
    bruno_event_id = bruno_import.json()["events"][0]["id"]

    # Seguidora 2 (Carla) segue a mesma turma e importa de forma independente para sua própria agenda
    authenticated_user["value"] = CurrentUser(id=carla_id, role="student")
    assert client.put(f"/api/v1/me/class-offerings/{oid}").status_code == 204
    carla_import = client.post(
        f"/api/v1/syllabus/{sid}/confirm",
        headers={"Idempotency-Key": "carla-import-v1-001"},
        json={
            "versionId": str(v1_id),
            "candidates": [{"candidateId": str(c1_id), "title": "Prova 1 (Agenda Carla)"}],
        },
    )
    assert carla_import.status_code == 200
    carla_event_id = carla_import.json()["events"][0]["id"]
    assert carla_event_id != bruno_event_id

    carla_agenda = client.get("/api/v1/me/events").json()
    assert len(carla_agenda) == 1
    assert carla_agenda[0]["title"] == "Prova 1 (Agenda Carla)"

    authenticated_user["value"] = CurrentUser(id=bruno_id, role="student")
    bruno_agenda = client.get("/api/v1/me/events").json()
    assert len(bruno_agenda) == 1
    assert bruno_agenda[0]["title"] == "Prova 1 (Agenda Bruno)"


def test_repeated_vote_keeps_count_allows_correction_and_new_version_preserves_imported_events(api):
    """Critério 2: Voto repetido mantém a contagem, permite corrigir o próprio voto sem alterar datas e revisão preserva eventos importados."""
    client, TestSession, authenticated_user, _ = api
    ana_id = authenticated_user["value"].id
    bruno_id = uuid4()
    carla_id = uuid4()
    prof_id = uuid4()

    _ensure_profile(TestSession, ana_id, "student", "Ana Autora")
    _ensure_profile(TestSession, bruno_id, "student", "Bruno Seguidor")
    _ensure_profile(TestSession, carla_id, "student", "Carla Seguidora")
    _ensure_profile(TestSession, prof_id, "professor", "Prof. Henrique")

    seeded = _seed_offering_and_plan(TestSession, ana_id, shared=True)
    oid = seeded["offering_id"]
    sid = seeded["syllabus_id"]
    v1_id = seeded["version_id"]
    c1_id, _ = seeded["candidates"]

    for uid in (bruno_id, carla_id, prof_id):
        authenticated_user["value"] = CurrentUser(id=uid, role="professor" if uid == prof_id else "student")
        assert client.put(f"/api/v1/me/class-offerings/{oid}").status_code == 204

    # Bruno importa a Prova 1 da versão 1
    authenticated_user["value"] = CurrentUser(id=bruno_id, role="student")
    imp = client.post(
        f"/api/v1/syllabus/{sid}/confirm",
        headers={"Idempotency-Key": "bruno-vote-import-01"},
        json={"versionId": str(v1_id), "candidates": [{"candidateId": str(c1_id)}]},
    )
    assert imp.status_code == 200
    original_event = imp.json()["events"][0]

    # Bruno vota "confirm" duas vezes no mesmo candidato -> contagem permanece 1
    v1_vote = client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}/candidates/{c1_id}/vote",
        json={"value": "confirm"},
    )
    assert v1_vote.status_code == 200
    assert (v1_vote.json()["confirmCount"], v1_vote.json()["contestCount"], v1_vote.json()["divergent"]) == (1, 0, False)

    v1_repeat = client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}/candidates/{c1_id}/vote",
        json={"value": "confirm"},
    )
    assert (v1_repeat.json()["confirmCount"], v1_repeat.json()["contestCount"]) == (1, 0)

    # Carla vota "confirm" -> confirmCount = 2
    authenticated_user["value"] = CurrentUser(id=carla_id, role="student")
    carla_vote = client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}/candidates/{c1_id}/vote",
        json={"value": "confirm"},
    )
    assert (carla_vote.json()["confirmCount"], carla_vote.json()["contestCount"]) == (2, 0)

    # Bruno corrige o próprio voto para "contest" -> confirmCount = 1, contestCount = 1, divergent = True
    authenticated_user["value"] = CurrentUser(id=bruno_id, role="student")
    corrected = client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}/candidates/{c1_id}/vote",
        json={"value": "contest"},
    )
    assert corrected.status_code == 200
    assert (
        corrected.json()["confirmCount"],
        corrected.json()["contestCount"],
        corrected.json()["divergent"],
        corrected.json()["myVote"],
    ) == (1, 1, True, "contesta")

    # Resumo da versão mostra divergência e apenas o voto da própria conta consultante
    authenticated_user["value"] = CurrentUser(id=carla_id, role="student")
    summary = client.get(f"/api/v1/syllabus/{sid}/versions/{v1_id}/votes")
    assert summary.status_code == 200
    assert summary.json()["divergent"] is True
    assert summary.json()["myVote"] == "confirma"
    c1_summary = next(item for item in summary.json()["items"] if item["candidateId"] == str(c1_id))
    assert (c1_summary["confirmCount"], c1_summary["contestCount"], c1_summary["divergent"], c1_summary["myVote"]) == (
        1, 1, True, "confirma",
    )

    # Divergência de votos nunca altera automaticamente a data do candidato na versão
    ver_detail = client.get(f"/api/v1/syllabus/{sid}/versions/{v1_id}").json()
    c1_detail = next(c for c in ver_detail["candidates"] if c["id"] == str(c1_id))
    assert c1_detail["suggestedDate"] == "2026-11-20"

    # Professor cria e publica uma nova versão revisada (v2) com outra data para a Prova 1
    authenticated_user["value"] = CurrentUser(id=prof_id, role="professor")
    rev = client.post(
        f"/api/v1/syllabus/{sid}/versions",
        json={
            "sourceVersionId": str(v1_id),
            "share": True,
            "candidates": [
                {
                    "candidateId": str(c1_id),
                    "title": "Prova 1 Reagendada",
                    "type": "prova",
                    "startsAt": "2026-11-27T13:00:00Z",
                }
            ],
        },
    )
    assert rev.status_code == 201
    assert rev.json()["number"] == 2
    assert rev.json()["visibility"] == "compartilhada"

    # O evento já importado por Bruno permanece intacto na agenda pessoal dele
    authenticated_user["value"] = CurrentUser(id=bruno_id, role="student")
    bruno_events = client.get("/api/v1/me/events").json()
    assert len(bruno_events) == 1
    assert bruno_events[0]["id"] == original_event["id"]
    assert bruno_events[0]["title"] == "Prova 1"
    assert bruno_events[0]["starts_at"] == original_event["starts_at"]


def test_withdrawing_version_blocks_new_access_votes_and_imports_while_preserving_copies_and_revisions(api):
    """Critério 3: Retirar a versão impede novos acessos/votos/importações e preserva cópias importadas e revisões derivadas."""
    client, TestSession, authenticated_user, _ = api
    ana_id = authenticated_user["value"].id
    bruno_id = uuid4()
    carla_id = uuid4()
    prof_id = uuid4()

    _ensure_profile(TestSession, ana_id, "student", "Ana Autora")
    _ensure_profile(TestSession, bruno_id, "student", "Bruno Seguidor")
    _ensure_profile(TestSession, carla_id, "student", "Carla Seguidora")
    _ensure_profile(TestSession, prof_id, "professor", "Prof. Henrique")

    seeded = _seed_offering_and_plan(TestSession, ana_id, shared=True)
    oid = seeded["offering_id"]
    sid = seeded["syllabus_id"]
    v1_id = seeded["version_id"]
    c1_id, _ = seeded["candidates"]

    for uid in (bruno_id, carla_id, prof_id):
        authenticated_user["value"] = CurrentUser(id=uid, role="professor" if uid == prof_id else "student")
        assert client.put(f"/api/v1/me/class-offerings/{oid}").status_code == 204

    # Bruno importa da v1 antes da retirada
    authenticated_user["value"] = CurrentUser(id=bruno_id, role="student")
    imp = client.post(
        f"/api/v1/syllabus/{sid}/confirm",
        headers={"Idempotency-Key": "bruno-before-withdraw-01"},
        json={"versionId": str(v1_id), "candidates": [{"candidateId": str(c1_id)}]},
    )
    assert imp.status_code == 200

    # Professor cria e publica uma revisão derivada v2 antes da retirada da v1
    authenticated_user["value"] = CurrentUser(id=prof_id, role="professor")
    rev = client.post(
        f"/api/v1/syllabus/{sid}/versions",
        json={"sourceVersionId": str(v1_id), "share": True},
    )
    assert rev.status_code == 201
    v2_id = rev.json()["id"]

    # Nem seguidor nem professor podem retirar versão de autoria da Ana
    for actor_id, role in ((bruno_id, "student"), (prof_id, "professor")):
        authenticated_user["value"] = CurrentUser(id=actor_id, role=role)
        assert client.delete(f"/api/v1/syllabus/{sid}/versions/{v1_id}/sharing").status_code == 403

    # Autora retira o compartilhamento da v1
    authenticated_user["value"] = CurrentUser(id=ana_id, role="student")
    withdrawn = client.delete(f"/api/v1/syllabus/{sid}/versions/{v1_id}/sharing")
    assert withdrawn.status_code == 200
    assert withdrawn.json()["visibility"] == "privada"
    assert withdrawn.json()["withdrawnAt"] is not None

    # Carla (seguidora) fica impedida de ler, votar ou importar a v1 retirada
    authenticated_user["value"] = CurrentUser(id=carla_id, role="student")
    assert client.get(f"/api/v1/syllabus/{sid}/versions/{v1_id}").status_code == 404
    assert client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}/candidates/{c1_id}/vote",
        json={"value": "confirm"},
    ).status_code == 404
    assert client.post(
        f"/api/v1/syllabus/{sid}/confirm",
        headers={"Idempotency-Key": "carla-after-withdraw-01"},
        json={"versionId": str(v1_id), "candidates": [{"candidateId": str(c1_id)}]},
    ).status_code == 404

    # A revisão derivada v2 do professor permanece disponível para a turma
    shared_items = client.get(f"/api/v1/class-offerings/{oid}/shared-plans").json()["items"]
    assert [item["id"] for item in shared_items] == [v2_id]

    # E a cópia já importada por Bruno continua na agenda pessoal dele
    authenticated_user["value"] = CurrentUser(id=bruno_id, role="student")
    assert len(client.get("/api/v1/me/events").json()) == 1


def test_author_professor_and_admin_revision_permissions_provenance_inheritance_and_private_isolation(api):
    """Critério 4: Edição por autor/professor/admin, publicação pelo autor, retirada por autor/admin, preservação da versão anterior e isolamento privado diante de professor/admin."""
    client, TestSession, authenticated_user, _ = api
    ana_id = authenticated_user["value"].id
    bruno_id = uuid4()
    prof_id = uuid4()
    admin_id = uuid4()

    _ensure_profile(TestSession, ana_id, "student", "Ana Autora")
    _ensure_profile(TestSession, bruno_id, "student", "Bruno Colega")
    _ensure_profile(TestSession, prof_id, "professor", "Prof. Carlos")
    _ensure_profile(TestSession, admin_id, "admin", "Admin UnB")

    seeded = _seed_offering_and_plan(TestSession, ana_id, shared=False)
    sid = seeded["syllabus_id"]
    v1_id = seeded["version_id"]
    c1_id, _ = seeded["candidates"]

    # 1. Enquanto v1 é privada, papel de professor ou admin NÃO dá acesso ao plano, texto ou versão privada de Ana
    for staff_id, staff_role in ((prof_id, "professor"), (admin_id, "admin")):
        authenticated_user["value"] = CurrentUser(id=staff_id, role=staff_role)
        assert client.get(f"/api/v1/syllabus/{sid}").status_code == 404
        assert client.get(f"/api/v1/syllabus/{sid}/text").status_code == 404
        assert client.get(f"/api/v1/syllabus/{sid}/versions").status_code == 404
        assert client.get(f"/api/v1/syllabus/{sid}/versions/{v1_id}").status_code == 404
        assert client.put(f"/api/v1/syllabus/{sid}/versions/{v1_id}/sharing").status_code == 403
        assert client.post(
            f"/api/v1/syllabus/{sid}/versions",
            json={"sourceVersionId": str(v1_id)},
        ).status_code == 404

    # 2. Autora edita sua versão privada v1 e depois publica voluntariamente
    authenticated_user["value"] = CurrentUser(id=ana_id, role="student")
    edited_private = client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}",
        json={
            "candidates": [
                {
                    "candidateId": str(c1_id),
                    "title": "Prova 1 (Revisada pela Autora)",
                    "type": "prova",
                    "startsAt": "2026-11-20T13:00:00Z",
                }
            ]
        },
    )
    assert edited_private.status_code == 200
    assert edited_private.json()["candidates"][0]["title"] == "Prova 1 (Revisada pela Autora)"

    published_v1 = client.put(f"/api/v1/syllabus/{sid}/versions/{v1_id}/sharing")
    assert published_v1.status_code == 200
    assert published_v1.json()["visibility"] == "compartilhada"

    # Depois de compartilhada, a v1 torna-se imutável (edição direta retorna 409)
    assert client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}",
        json={"candidates": [{"title": "Tentativa direta", "type": "prova"}]},
    ).status_code == 409

    # 3. Outro estudante (Bruno) não pode criar revisão sobre versão de outra pessoa (403)
    authenticated_user["value"] = CurrentUser(id=bruno_id, role="student")
    assert client.post(
        f"/api/v1/syllabus/{sid}/versions",
        json={"sourceVersionId": str(v1_id)},
    ).status_code == 403

    # 4. Admin valida procedência institucional com evidência pública oficial
    authenticated_user["value"] = CurrentUser(id=prof_id, role="professor")
    assert client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}/provenance",
        json={"institutionalSourceUrl": "https://fga.unb.br/planos/mds.pdf"},
    ).status_code == 403

    authenticated_user["value"] = CurrentUser(id=admin_id, role="admin")
    assert client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}/provenance",
        json={"institutionalSourceUrl": "javascript:alert(1)"},
    ).status_code == 422
    prov = client.put(
        f"/api/v1/syllabus/{sid}/versions/{v1_id}/provenance",
        json={"institutionalSourceUrl": "https://fga.unb.br/planos/mds.pdf"},
    )
    assert prov.status_code == 200
    assert prov.json()["institutionalProvenance"] is True
    assert prov.json()["institutionalSourceUrl"] == "https://fga.unb.br/planos/mds.pdf"

    # 5. Professor revisa v1 (criando v2 privada, ajustando e publicando diretamente), herdando procedência institucional
    authenticated_user["value"] = CurrentUser(id=prof_id, role="professor")
    rev_prof = client.post(
        f"/api/v1/syllabus/{sid}/versions",
        json={"sourceVersionId": str(v1_id)},
    )
    assert rev_prof.status_code == 201
    v2_id = rev_prof.json()["id"]
    assert rev_prof.json()["number"] == 2
    assert rev_prof.json()["authorRole"] == "professor"
    assert rev_prof.json()["visibility"] == "privada"
    assert rev_prof.json()["institutionalProvenance"] is True
    assert rev_prof.json()["institutionalSourceUrl"] == "https://fga.unb.br/planos/mds.pdf"

    # O rascunho privado v2 do professor não é visível para a dona original (Ana) antes do compartilhamento
    authenticated_user["value"] = CurrentUser(id=ana_id, role="student")
    assert client.get(f"/api/v1/syllabus/{sid}/versions/{v2_id}").status_code == 404

    authenticated_user["value"] = CurrentUser(id=prof_id, role="professor")
    assert client.put(
        f"/api/v1/syllabus/{sid}/versions/{v2_id}",
        json={"candidates": [{"title": "Prova 1 (Revisão Docente)", "type": "prova", "startsAt": "2026-11-21T13:00:00Z"}]},
    ).status_code == 200
    assert client.put(f"/api/v1/syllabus/{sid}/versions/{v2_id}/sharing").status_code == 200

    # A versão anterior v1 permanece preservada com seu título original
    authenticated_user["value"] = CurrentUser(id=ana_id, role="student")
    v1_check = client.get(f"/api/v1/syllabus/{sid}/versions/{v1_id}").json()
    assert v1_check["candidates"][0]["title"] == "Prova 1 (Revisada pela Autora)"

    # 6. Admin cria e publica diretamente a revisão v3 (também herda procedência)
    authenticated_user["value"] = CurrentUser(id=admin_id, role="admin")
    rev_admin = client.post(
        f"/api/v1/syllabus/{sid}/versions",
        json={
            "sourceVersionId": str(v2_id),
            "share": True,
            "candidates": [{"title": "Prova 1 (Revisão Admin)", "type": "prova", "startsAt": "2026-11-22T13:00:00Z"}],
        },
    )
    assert rev_admin.status_code == 201
    assert rev_admin.json()["number"] == 3
    assert rev_admin.json()["authorRole"] == "admin"
    assert rev_admin.json()["visibility"] == "compartilhada"
    assert rev_admin.json()["institutionalProvenance"] is True

    # 7. Autora estudante cria revisão v4: revisões estudantis NÃO herdam procedência institucional automaticamente
    authenticated_user["value"] = CurrentUser(id=ana_id, role="student")
    rev_student = client.post(
        f"/api/v1/syllabus/{sid}/versions",
        json={"sourceVersionId": str(v1_id), "share": True},
    )
    assert rev_student.status_code == 201
    assert rev_student.json()["number"] == 4
    assert rev_student.json()["authorRole"] == "student"
    assert rev_student.json()["institutionalProvenance"] is False
    assert rev_student.json()["institutionalSourceUrl"] is None

    # 8. Admin pode retirar o compartilhamento de versão de terceiro
    authenticated_user["value"] = CurrentUser(id=admin_id, role="admin")
    admin_withdraw = client.delete(f"/api/v1/syllabus/{sid}/versions/{v2_id}/sharing")
    assert admin_withdraw.status_code == 200
    assert admin_withdraw.json()["visibility"] == "privada"
