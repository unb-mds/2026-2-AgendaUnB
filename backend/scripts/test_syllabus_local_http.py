"""Executa integração HTTP apenas no Supabase descartável de testes.

Lê credenciais locais do CLI em memória e repassa somente ao processo de testes.
Não altera .env, não inicia serviços e não aceita projeto hospedado/remoto.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import tomllib
from urllib.parse import urlsplit

from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--supabase-cli", default="supabase")
    parser.add_argument("--gemini-live", action="store_true", help="Chamada real somente com PDF sintético")
    parser.add_argument("--all-tests", action="store_true")
    parser.add_argument("--report",type=Path,help="Relatório JSON de métricas, sem credenciais")
    args = parser.parse_args()
    try:
        config = tomllib.loads((args.workdir / "supabase/config.toml").read_text(encoding="utf-8"))
        if config.get("project_id") != "agendaunb-s6d02-tests":
            parser.exit(2,"Use exclusivamente o projeto local descartável agendaunb-s6d02-tests.\n")
        status = subprocess.run([args.supabase_cli,"status","--workdir",str(args.workdir),"--output","json"],
                                capture_output=True,text=True,timeout=30)
        if status.returncode:
            parser.exit(2,"Supabase de teste indisponível; inicie os serviços HTTP locais.\n")
        data = json.loads(status.stdout)
        api = urlsplit(data["API_URL"])
        db = make_url(data["DB_URL"])
        if api.hostname not in ("localhost","127.0.0.1") or db.host not in ("localhost","127.0.0.1"):
            parser.exit(2,"A suíte aceita apenas serviços locais.\n")
        if api.port != config["api"]["port"] or db.port != config["db"]["port"]:
            parser.exit(2,"As portas não correspondem à configuração isolada.\n")
        if not data.get("ANON_KEY") or not data.get("SERVICE_ROLE_KEY"):
            parser.exit(2,"Credenciais do ambiente local não disponíveis no CLI.\n")
        env = os.environ.copy()
        env.update({"TEST_SUPABASE_DB_URL":db.set(drivername="postgresql+psycopg").render_as_string(hide_password=False),
                    "TEST_LOCAL_SUPABASE_URL":data["API_URL"],
                    "TEST_LOCAL_SUPABASE_ANON_KEY":data["ANON_KEY"],
                    "TEST_LOCAL_SUPABASE_SERVICE_ROLE_KEY":data["SERVICE_ROLE_KEY"],
                    "TEST_GEMINI_LIVE":"true" if args.gemini_live else "false"})
        env.pop("TEST_SYLLABUS_HTTP_REPORT",None)
        if args.report:
            if args.report.suffix.lower() != ".json":
                parser.exit(2,"O relatório deve ser um arquivo .json.\n")
            args.report = args.report.resolve()
            args.report.parent.mkdir(parents=True,exist_ok=True)
            args.report.write_text(json.dumps({"executed_at":datetime.now(timezone.utc).isoformat(),
                "api_port":api.port,"db_port":db.port,"gemini_live":args.gemini_live,"results":[]},indent=2)+"\n",encoding="utf-8")
            env["TEST_SYLLABUS_HTTP_REPORT"] = str(args.report)
        target = "tests" if args.all_tests else "tests/test_syllabus_http_integration.py"
        print(json.dumps({"local_http_integration":True,"api_port":api.port,"db_port":db.port,
                          "gemini_live":args.gemini_live,"all_tests":args.all_tests}),flush=True)
        exit_code = subprocess.run([sys.executable,"-m","pytest",target,"-q","--tb=short"],cwd=ROOT,env=env).returncode
        if args.report:
            report = json.loads(args.report.read_text(encoding="utf-8"))
            report["pytest_exit_code"] = exit_code
            args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        return exit_code
    except (OSError,ValueError,KeyError,subprocess.TimeoutExpired):
        parser.exit(2,"Não foi possível carregar a configuração local de testes; nenhuma credencial foi exibida.\n")


if __name__ == "__main__":
    raise SystemExit(main())
