"""Execute: python -m src.modules.classes.sync --period 2026.2"""

import argparse

import json

import re

from datetime import datetime, timezone

from uuid import UUID

from sqlalchemy import text, update

from sqlalchemy.orm import Session

from sqlalchemy.exc import DBAPIError

from src.database.connection import engine

from src.database.models import CatalogSync, ClassOffering

from src.modules.classes.followw import CatalogError, FollowwClient, normalize



LOCK = 708071





def synchronize(connection, periods, client=None):

    if not periods or any(not re.fullmatch(r"20\d{2}\.[12]", p) for p in periods):

        raise CatalogError("periodo_nao_suportado")

    periods = list(dict.fromkeys(periods))

    if not connection.scalar(text("select pg_try_advisory_lock(:key)"), {"key": LOCK}):

        raise CatalogError("sincronizacao_em_andamento")

    connection.commit()

    client = client or FollowwClient()

    try:

        with Session(connection) as db:

            db.execute(update(CatalogSync).where(CatalogSync.status == "executando").values(

                status="falha", completed_at=datetime.now(timezone.utc), error_code="execucao_interrompida"))

            run = CatalogSync(periods=periods)

            db.add(run)

            db.flush()

            run_id = run.id

            db.commit()

            try:

                units = client.get("/public/classrooms/units")

                if not units or any(not isinstance(u.get("id"), int) or not u.get("name") for u in units) or len({u["id"] for u in units}) != len(units):

                    raise CatalogError("unidades_invalidas")

                units = [{k: u.get(k) for k in ("id", "code", "name")} for u in units]

                print(f"[catalogo] {len(units)} unidades; períodos: {periods}", flush=True)

                offers, rejected, coverage = [], [], []

                for period in periods:

                    for unit in units:

                        print(f"[catalogo] {period}: unidade {unit['id']} ({len(coverage)+1}/{len(units)*len(periods)})", flush=True)

                        live = client.get("/public/classrooms", unit=unit["id"], semester=period)

                        enrichment = "ok"

                        try:

                            subjects = client.get("/public/subjects", unit=unit["id"], semester=period)

                        except CatalogError:

                            subjects, enrichment = [], "indisponivel"

                        rows, issues = normalize(live, subjects, unit, period)

                        offers.extend(rows)

                        rejected.extend(issues)

                        coverage.append({"unit": unit["id"], "period": period, "read": len(live), "enrichment": enrichment})

                run.units, run.coverage = units, coverage

                run.offerings_read = len(offers)

                # Todas as mutaÃ§Ãµes e o marcador de publicaÃ§Ã£o usam a mesma transaÃ§Ã£o.

                db.execute(text("select pg_advisory_xact_lock(708072)"))

                for offer in offers:

                    try:

                        with db.begin_nested():

                            result = db.execute(text("select public.registrar_oferta_catalogo(cast(:p as jsonb))"),

                                                {"p": json.dumps(offer)}).scalar_one()

                            record = db.get(ClassOffering, UUID(result["id"]))

                            record.publication_id = run_id

                        run.created += result["acao"] == "criada"

                        run.updated += result["acao"] == "atualizada"

                    except DBAPIError as error:

                        if getattr(error.orig, "sqlstate", None) not in {"22023", "55000", "23505", "23514"}:

                            raise

                        rejected.append({"code": "identidade_rejeitada", "subject_code": offer["codigo"],

                                         "unit": offer["unidade"], "period": f"{offer['ano']}.{offer['semestre']}",

                                         "number": offer["turma"]})

                run.rejected = list(rejected)

                run.status, run.completed_at = "concluida", datetime.now(timezone.utc)

                db.commit()

                return {"id": str(run_id), "units": len(units), "periods": periods, "offers": len(offers), "rejected": len(rejected), "coverage": coverage}

            except Exception as error:

                db.rollback()

                run = db.get(CatalogSync, run_id)

                run.status, run.completed_at = "falha", datetime.now(timezone.utc)

                run.error_code = str(error)[:60] if isinstance(error, CatalogError) else "sincronizacao_falhou"

                db.commit()

                raise CatalogError(run.error_code) from None

    finally:

        connection.rollback()

        connection.execute(text("select pg_advisory_unlock(:key)"), {"key": LOCK})

        connection.commit()





def main():

    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("--period", action="append", default=None)

    args = parser.parse_args()

    with engine.connect() as connection:

        print(json.dumps(synchronize(connection, args.period or ["2026.2"]), ensure_ascii=False))





if __name__ == "__main__":

    main()

