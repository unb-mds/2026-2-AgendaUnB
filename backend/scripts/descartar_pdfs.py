"""Remove do Storage os PDFs originais de planos já processados (ADR-003, #83).

Uso, na pasta backend e com o .env do ambiente carregado:

    python -m scripts.descartar_pdfs            # só lista o que seria removido
    python -m scripts.descartar_pdfs --executar # remove e registra o descarte

O plano, os candidatos e a agenda permanecem. Só o arquivo original sai.
Planos pendentes ou em processamento não são tocados. Pode ser repetido:
cada execução retoma de onde a anterior parou.
"""
import argparse
import sys

from sqlalchemy import text

from src.database.connection import SessionLocal
from src.modules.account.services import SupabaseAccountAdmin


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--executar", action="store_true", help="remove de fato (sem isso, apenas lista)")
    parser.add_argument("--lote", type=int, default=100, help="planos por lote (1 a 1000)")
    args = parser.parse_args()

    admin = SupabaseAccountAdmin()
    removed = 0
    with SessionLocal() as db:
        while True:
            batch = db.execute(
                text("select plano_id, caminho_arquivo from public.arquivos_a_descartar(:n)"), {"n": args.lote}
            ).all()
            if not batch:
                break
            if not args.executar:
                total = db.execute(text(
                    "select count(*) from public.planos_ensino "
                    "where caminho_arquivo is not null and status in ('concluido', 'falha')"
                )).scalar_one()
                print(f"{total} arquivo(s) seriam removidos. Rode com --executar para remover.")
                return 0
            admin.delete_files([path for _, path in batch])
            for plan_id, _ in batch:
                db.execute(text("select public.registrar_descarte_arquivo(:p)"), {"p": plan_id})
            db.commit()
            removed += len(batch)
            print(f"{removed} arquivo(s) removidos...")
    print(f"Concluído: {removed} arquivo(s) removidos." if args.executar else "Nenhum arquivo a remover.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
