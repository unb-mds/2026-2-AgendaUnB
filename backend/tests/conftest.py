import os
from uuid import uuid4
from unittest.mock import create_autospec

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

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
