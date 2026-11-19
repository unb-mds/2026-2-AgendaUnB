"""Start and stop the local API and Vite as one development session."""
import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def available_port(preferred):
    for port in range(preferred, preferred + 100):
        try:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', port))
            return port
        except OSError:
            continue
    raise RuntimeError(f'Nenhuma porta disponível a partir de {preferred}')


def stop(child):
    if child.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        os.killpg(child.pid, signal.SIGTERM)
    try:
        child.wait(timeout=5)
    except subprocess.TimeoutExpired:
        child.kill()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend-port', type=int, default=8000)
    parser.add_argument('--frontend-port', type=int, default=5173)
    args = parser.parse_args()
    backend = available_port(args.backend_port)
    frontend = available_port(args.frontend_port)
    if frontend == backend:
        frontend = available_port(frontend + 1)
    for label, requested, actual in [('API', args.backend_port, backend), ('Frontend', args.frontend_port, frontend)]:
        if requested != actual:
            print(f'[INFO] Porta {requested} ocupada. {label} usará {actual}; o serviço existente será preservado.', flush=True)
    base_env = os.environ.copy()
    from dotenv import dotenv_values, load_dotenv
    dotenv_path = ROOT / '.env'
    file_env = {key: value for key, value in dotenv_values(dotenv_path).items() if value is not None}
    load_dotenv(dotenv_path)

    backend_env = {**file_env, **base_env}
    backend_env['AGENDA_BACKEND_PORT'] = str(backend)
    cors_items = [
        item.strip()
        for raw in (backend_env.get('CORS_ORIGINS', ''), f'http://localhost:{frontend}', f'http://127.0.0.1:{frontend}')
        for item in raw.split(',')
        if item.strip()
    ]
    backend_env['CORS_ORIGINS'] = ','.join(dict.fromkeys(cors_items))

    frontend_env = base_env.copy()
    for secret_key in (
        'GEMINI_API_KEY',
        'DATABASE_URL',
        'SUPABASE_SERVICE_ROLE_KEY',
        'GOOGLE_TOKEN_ENCRYPTION_KEY',
        'GOOGLE_CALENDAR_CLIENT_SECRET',
        'SUPABASE_AUTH_EXTERNAL_GOOGLE_SECRET',
        'SMTP_PASS',
    ):
        frontend_env.pop(secret_key, None)
    frontend_env['AGENDA_BACKEND_PORT'] = str(backend)

    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, interrupted)
    children = []
    try:
        sys.path.insert(0, str(ROOT / 'backend'))
        from sqlalchemy import text
        from src.database.connection import engine
        from src.modules.syllabus.privacy import privacy_checks
        from src.modules.syllabus.processing_config import ProcessingConfig
        from src.modules.syllabus.worker import worker_ready_to_spawn

        try:
            with engine.connect() as connection:
                has_catalog = bool(connection.scalar(text("select exists(select 1 from public.sincronizacoes_catalogo where status='concluida')")))
                privacy_ok = all(privacy_checks(connection).values())
        finally:
            engine.dispose()

        should_start_worker = worker_ready_to_spawn() and privacy_ok
        api_env = backend_env.copy()
        if should_start_worker:
            api_env['SYLLABUS_DAEMON_ACTIVE'] = 'true'

        api = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'src.main:app', '--host', '127.0.0.1', '--port', str(backend)], cwd=ROOT / 'backend', env=api_env, **options)
        children.append(api)
        deadline = time.monotonic() + 30
        while True:
            if api.poll() is not None:
                raise RuntimeError('A API encerrou durante a inicialização.')
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{backend}/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError('A API não respondeu em 30 segundos.')
                time.sleep(.25)
        # A primeira leitura exige uma publicação; carregue fora do ciclo HTTP.
        if not has_catalog:
            print('[INFO] Primeira carga do catálogo em andamento. A interface será liberada após a publicação completa.', flush=True)
            sync = subprocess.Popen([sys.executable, '-m', 'src.modules.classes.sync', '--period', '2026.2'], cwd=ROOT / 'backend', env=backend_env, **options)
            children.append(sync)

        worker = None
        if should_start_worker:
            cfg = ProcessingConfig.from_env()
            print(f'[INFO] Iniciando worker de planos (Gemini: {cfg.model}) em modo contínuo...', flush=True)
            worker = subprocess.Popen(
                [sys.executable, '-m', 'src.modules.syllabus.worker'],
                cwd=ROOT / 'backend',
                env=backend_env,
                stdin=subprocess.DEVNULL,
                **options,
            )
            children.append(worker)
            worker_status = f'ativo ({cfg.model})'
        else:
            print('[INFO] Worker de planos (Gemini) inativo nesta sessão.', flush=True)
            worker_status = 'inativo'

        import shutil
        node = shutil.which('node')
        if node is None:
            raise RuntimeError('Node.js não encontrado.')
        vite = subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(frontend), '--strictPort'], cwd=ROOT / 'frontend', env=frontend_env, **options)
        children.append(vite)
        print(
            f'\nFrontend: http://127.0.0.1:{frontend}/plano-de-ensino\n'
            f'API: http://127.0.0.1:{backend}/docs\n'
            f'Worker Gemini: {worker_status}\n'
            f'Ctrl+C encerra esta sessão.\n',
            flush=True,
        )
        while api.poll() is None and vite.poll() is None and (worker is None or worker.poll() is None):
            time.sleep(.25)
        raise RuntimeError('Um dos serviços encerrou. A sessão será finalizada.')
    except KeyboardInterrupt:
        return 0
    except RuntimeError as error:
        print(f'[ERRO] {error}', file=sys.stderr)
        return 1
    finally:
        for child in reversed(children):
            stop(child)


if __name__ == '__main__':
    raise SystemExit(main())
