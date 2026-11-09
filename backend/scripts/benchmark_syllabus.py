"""Avaliação reproduzível, exclusivamente com corpus sintético versionado.

Não aceita caminhos de PDFs reais. --live permite chamadas de baixo custo ao Gemini.
Sem --live, usa respostas de referência para testar apenas a infraestrutura local.
"""
import argparse
import json
import sys
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.database.models import AssessmentCandidate, Base, Profile, Syllabus
from src.modules.syllabus.extraction import VERSION, normalize
from src.modules.syllabus.gemini import GeminiProvider
from src.modules.syllabus.processing_config import ProcessingConfig
from src.modules.syllabus.processing_task import run_isolated
from src.modules.syllabus.worker import SyllabusWorker
from syllabus_samples import cases, make_pdf


class SyntheticStorage:
    def __init__(self, content):
        self.content = content

    def download_file(self, path):
        return self.content


class ReferenceProvider:
    def __init__(self, case):
        self.case = case

    def extract(self, pages):
        candidates = []
        for expected in self.case["expected"]:
            item = dict(expected)
            page = pages[item["pagina_origem"] - 1].texto
            item["trecho_origem"] = next(line for line in page.splitlines() if item["titulo"] in line)
            item["campos_ambiguos"] = [] if item["data_sugerida"] else ["data"]
            candidates.append(item)
        return json.dumps({"candidatos": candidates})


def metrics(expected, actual):
    correct = 0
    omissions = 0
    invented = 0
    incorrect = 0
    used = set()
    for reference in expected:
        match = next((i for i, item in enumerate(actual) if i not in used and
                      normalize(reference["titulo"]) in normalize(item.titulo) and
                      item.pagina_origem == reference["pagina_origem"]), None)
        if match is None:
            omissions += 1
            continue
        used.add(match)
        item = actual[match]
        actual_date = item.data_sugerida.isoformat() if item.data_sugerida else None
        actual_time = item.hora_sugerida.strftime("%H:%M") if item.hora_sugerida else None
        if actual_date is not None and actual_date != reference["data_sugerida"]:
            invented += 1
        if item.tipo == reference["tipo"] and actual_date == reference["data_sugerida"] and actual_time == reference["hora_sugerida"]:
            correct += 1
        else:
            incorrect += 1
    extras = len(actual) - len(used)
    invented += sum(actual[i].data_sugerida is not None for i in range(len(actual)) if i not in used)
    return dict(expected=len(expected), correct=correct, omissions=omissions,
                incorrect=incorrect, extras=extras, invented_dates_persisted=invented)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = replace(ProcessingConfig.from_env(), retry_delay_seconds=0)
    if args.live and not config.api_key:
        parser.exit(2, "GEMINI_API_KEY ausente; nenhum acesso ao registro do Windows será feito.\n")
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    report = dict(executed_at=datetime.now(timezone.utc).isoformat(),
                  processing_version=VERSION, attempt_timeout_seconds=config.attempt_timeout_seconds,
                  mode="gemini_live_synthetic" if args.live else "reference_offline",
                  provider="google" if args.live else "reference", model=config.model if args.live else None,
                  target_seconds=20, max_file_cost_usd=str(config.max_file_cost_usd), cases=[])
    for case in cases():
        started = time.monotonic()
        content = make_pdf(case["pages"])
        owner, sid = uuid4(), uuid4()
        with sessions() as db:
            db.add(Profile(id=owner, papel="student"))
            db.add(Syllabus(id=sid, user_id=owner, file_name=case["id"] + ".pdf",
                            file_path=f"syllabus_files/{owner}/{sid}.pdf", file_size=len(content)))
            db.commit()
        provider = GeminiProvider(config) if args.live else ReferenceProvider(case)
        observations = []
        def observe_task(*params):
            result = run_isolated(*params)
            observations.append(result.extraction.unsupported_dates)
            return result
        worker = SyllabusWorker(sessions, SyntheticStorage(content), provider, config, runner=observe_task)
        for _ in range(config.max_attempts + 1):
            if not worker.run_once():
                break
        elapsed = round(time.monotonic() - started, 3)
        with sessions() as db:
            job = db.get(Syllabus, sid)
            actual = list(db.scalars(select(AssessmentCandidate).where(
                AssessmentCandidate.plano_id == sid, AssessmentCandidate.execucao == job.execucao_atual)))
            measurement = dict(id=case["id"], pages=len(case["pages"]), status=job.status,
                               error_code=job.erro_codigo, attempts=job.execucao_atual,
                               cost_reserved_usd=str(job.cost_reserved_usd), total_seconds=elapsed,
                               unsupported_dates_blocked=sum(observations),
                               candidates=[dict(titulo=item.titulo, tipo=item.tipo,
                                                data=item.data_sugerida.isoformat() if item.data_sugerida else None,
                                                hora=item.hora_sugerida.strftime("%H:%M") if item.hora_sugerida else None,
                                                pagina=item.pagina_origem) for item in actual],
                               under_20_seconds=elapsed < 20, **metrics(case["expected"], actual))
            report["cases"].append(measurement)
    report["totals"] = {name: sum(item[name] for item in report["cases"]) for name in
                        ["expected", "correct", "omissions", "incorrect", "extras", "invented_dates_persisted", "unsupported_dates_blocked"]}
    report["totals"]["failed_files"] = sum(item["status"] != "concluido" for item in report["cases"])
    report["totals"]["over_20_seconds"] = sum(not item["under_20_seconds"] for item in report["cases"])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True))
    engine.dispose()


if __name__ == "__main__":
    main()
