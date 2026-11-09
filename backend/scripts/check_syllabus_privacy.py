"""Verifica pré-requisitos no banco de TESTE local, sem habilitar o worker."""
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.modules.syllabus.privacy import privacy_checks


def main():
    url = os.getenv("TEST_SUPABASE_DB_URL")
    if not url:
        print(json.dumps({"ready": False, "error": "TEST_SUPABASE_DB_URL ausente"}))
        return 2
    engine = None
    try:
        if make_url(url).host not in ("localhost", "127.0.0.1"):
            print(json.dumps({"ready": False, "error": "Apenas banco de teste local"}))
            return 2
        engine = create_engine(url)
        with engine.connect() as connection:
            checks = privacy_checks(connection)
        ready = all(checks.values())
        print(json.dumps({"ready": ready, "checks": checks}))
        return 0 if ready else 2
    except Exception:
        print(json.dumps({"ready": False, "error": "Falha de conexão ou migrações incompletas"}))
        return 2
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
