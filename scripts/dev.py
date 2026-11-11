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
    env = os.environ.copy()
    env['AGENDA_BACKEND_PORT'] = str(backend)
    from dotenv import find_dotenv, load_dotenv
    load_dotenv(find_dotenv(str(ROOT / '.env')))
    env['CORS_ORIGINS'] = ','.join(filter(None, [os.getenv('CORS_ORIGINS'), f'http://localhost:{frontend}', f'http://127.0.0.1:{frontend}']))
    options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    def interrupted(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, interrupted)
    children = []
    try:
        api = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'src.main:app', '--host', '127.0.0.1', '--port', str(backend)], cwd=ROOT / 'backend', env=env, **options)
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
        sys.path.insert(0, str(ROOT / 'backend'))
        from src.database.connection import engine
        from sqlalchemy import text
        with engine.connect() as connection:
            has_catalog = connection.scalar(text("select exists(select 1 from public.sincronizacoes_catalogo where status='concluida')"))
        if not has_catalog:
            print('[INFO] Primeira carga do catálogo em andamento. A interface será liberada após a publicação completa.', flush=True)
            sync = subprocess.Popen([sys.executable, '-m', 'src.modules.classes.sync', '--period', '2026.2'], cwd=ROOT / 'backend', env=env, **options)
            children.append(sync)
        import shutil
        node = shutil.which('node')
        if node is None:
            raise RuntimeError('Node.js não encontrado.')
        vite = subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', str(frontend), '--strictPort'], cwd=ROOT / 'frontend', env=env, **options)
        children.append(vite)
        print(f'\nFrontend: http://127.0.0.1:{frontend}/plano-de-ensino\nAPI: http://127.0.0.1:{backend}/docs\nCtrl+C encerra esta sessão.\n', flush=True)
        while api.poll() is None and vite.poll() is None:
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
