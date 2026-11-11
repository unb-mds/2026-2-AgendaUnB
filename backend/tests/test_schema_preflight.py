from sqlalchemy import create_engine, text

from src.database.check_schema import missing_schema
from src.database.models import Base


def test_current_schema_is_compatible():
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        with engine.connect() as connection:
            assert missing_schema(connection) == []
    finally:
        engine.dispose()


def test_detects_pre_s7_personal_events_schema():
    engine = create_engine("sqlite://")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE eventos_pessoais RENAME COLUMN origem_versao_id TO coluna_legada"
            ))
            assert missing_schema(connection) == ["eventos_pessoais.origem_versao_id"]
    finally:
        engine.dispose()


def test_reports_missing_tables_without_querying_them():
    engine = create_engine("sqlite://")
    try:
        with engine.connect() as connection:
            assert set(missing_schema(connection)) == set(Base.metadata.tables)
    finally:
        engine.dispose()
