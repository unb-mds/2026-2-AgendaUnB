import os
from uuid import uuid4
from unittest.mock import create_autospec

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
# O limitador conta por processo; a suíte inteira parte do mesmo cliente de teste.
os.environ["RATE_LIMIT_PER_MINUTE"] = "0"
os.environ["RATE_LIMIT_WRITE_PER_MINUTE"] = "0"

from src.database.connection import get_db
from src.database.models import Base, Campus, Category, PersonalEvent, PublicEvent
from src.main import app
from src.middlewares.auth import CurrentUser, get_current_user
from src.services.storage import SupabaseStorageService, get_storage_service


@pytest.fixture
def api():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        with TestSession() as session:
            yield session

    authenticated_user = {"value": CurrentUser(id=uuid4(), role="student")}
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: authenticated_user["value"]
    # Testes unitários não usam o Supabase real configurado no .env local.
    storage = create_autospec(SupabaseStorageService, instance=True)
    storage.upload_file.side_effect = lambda path, **kwargs: f"syllabus_files/{path}"
    storage.delete_file.return_value = True
    app.dependency_overrides[get_storage_service] = lambda: storage

    with TestClient(app) as client:
        with TestSession() as session:
            campus = Campus(id=uuid4(), nome="Darcy Ribeiro (Plano Piloto)")
            category = Category(id=uuid4(), nome="Cultura")
            session.add_all([campus, category])
            session.commit()
            ids = {"campus": campus.id, "category": category.id}
        yield client, TestSession, authenticated_user, ids

    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()

@pytest.fixture
def published_offering(api):
    from datetime import datetime, timezone
    from uuid import UUID
    from src.database.models import CatalogSync, Subject, ClassOffering
    with api[1]() as db:
        run = CatalogSync(status="concluida", completed_at=datetime.now(timezone.utc), periods=["2026.2"], units=[])
        db.add(run); db.flush()
        subject = Subject(code="FGA0138", name="Métodos de Desenvolvimento de Software", unit="673")
        db.add(subject); db.flush()
        offer = ClassOffering(id=UUID("70000000-0000-4000-8000-000000000071"), subject_id=subject.id,
            class_number="01", year=2026, semester=2, publication_id=run.id)
        db.add(offer); db.commit()
        return str(offer.id)
