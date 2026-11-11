"""Read-only preflight for the tables and columns used by the API."""
import sys

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from src.database.models import Base


def missing_schema(connection):
    inspector = inspect(connection)
    missing = []
    for table in Base.metadata.sorted_tables:
        if not inspector.has_table(table.name):
            missing.append(table.name)
            continue
        columns = {column["name"] for column in inspector.get_columns(table.name)}
        missing.extend(
            f"{table.name}.{column.name}"
            for column in table.columns
            if column.name not in columns
        )
    return missing


def main():
    from src.database.connection import engine

    try:
        with engine.connect() as connection:
            missing = missing_schema(connection)
    except SQLAlchemyError:
        print("Banco inacessível. Confira DATABASE_URL e inicie o Supabase local.", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    if missing:
        print("Schema incompatível com a API: " + ", ".join(missing), file=sys.stderr)
        print("Revise as migrações pendentes. No ambiente local, execute make db-migrate.", file=sys.stderr)
        return 1
    print("Schema compatível com as tabelas e colunas usadas pela API.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
