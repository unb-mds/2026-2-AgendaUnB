"""Worker no PostgreSQL local migrado; não comprova as políticas pendentes S6-D02."""
import json
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from src.database.models import AssessmentCandidate, Syllabus
from src.modules.syllabus.processing_config import ProcessingConfig
from src.modules.syllabus.worker import SyllabusWorker
from syllabus_samples import make_pdf
from test_moderation_database import database


def test_worker_postgres_constraints_and_candidate_array(database):
    connection, users = database
    sessions = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
    sid = uuid4()
    owner = UUID(users["student"])
    with sessions() as db:
        db.add(Syllabus(id=sid, user_id=owner, file_name="sintetico.pdf",
                        file_path=f"syllabus_files/{owner}/{sid}.pdf"))
        db.commit()

    class Storage:
        def download_file(self, path):
            return make_pdf(["Prova sintetica - data a definir."])

    class Provider:
        def extract(self, pages):
            return json.dumps({"candidatos": [{"titulo": "Prova sintetica", "tipo": "prova",
                "data_sugerida": None, "hora_sugerida": None, "campos_ambiguos": ["data"],
                "pagina_origem": 1, "trecho_origem": "Prova sintetica - data a definir."}]})

    worker = SyllabusWorker(sessions, Storage(), Provider(), ProcessingConfig())
    assert worker.run_once()
    with sessions() as db:
        plan = db.get(Syllabus, sid)
        assert plan.status == "concluido" and plan.extracted_events_count == 1
        candidate = db.scalar(select(AssessmentCandidate).where(AssessmentCandidate.plano_id == sid))
        assert candidate.campos_ambiguos == ["data"]
        assert candidate.evento_pessoal_id is None and candidate.status == "pendente"
