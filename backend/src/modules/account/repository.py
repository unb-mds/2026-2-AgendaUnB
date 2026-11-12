"""Acesso às funções de privacidade do banco (S8-D01, #83).

As regras ficam no banco; este módulo só chama as funções. Os erros
previstos chegam como DBAPIError com SQLSTATE e são traduzidos no router.
"""
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

# Data de vigência da versão publicada de cada documento. Ao publicar uma
# nova versão em docs/produto/, atualize aqui: as contas voltam a ser
# convidadas a ler o documento.
CURRENT_LEGAL_VERSIONS = {
    "termos_de_uso": "2026-11-11",
    "politica_de_privacidade": "2026-11-11",
}


def export_account(db: Session, user_id: UUID) -> dict:
    return db.execute(
        text("select public.exportar_dados_da_conta(:u)"), {"u": user_id}
    ).scalar_one()


def list_acceptances(db: Session, user_id: UUID) -> dict[str, str]:
    """Versão mais recente aceita por documento."""
    rows = db.execute(
        text("select documento, max(versao) from public.aceites_termos where user_id = :u group by documento"),
        {"u": user_id},
    ).all()
    return {document: version for document, version in rows}


def accept_document(db: Session, user_id: UUID, document: str, version: str) -> None:
    db.execute(
        text("select public.registrar_aceite_termos(:u, :d, :v)"),
        {"u": user_id, "d": document, "v": version},
    )
    db.commit()


def prepare_deletion(db: Session, user_id: UUID) -> dict:
    result = db.execute(
        text("select public.preparar_exclusao_conta(:u)"), {"u": user_id}
    ).scalar_one()
    db.commit()
    return result


def finish_deletion(db: Session, record_id: str) -> None:
    db.execute(text("select public.concluir_exclusao_conta(:r)"), {"r": record_id})
    db.commit()
