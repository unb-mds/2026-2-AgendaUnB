"""Remoção da conta nos serviços do Supabase que o banco não alcança."""
import logging
import os
from uuid import UUID

import httpx
from fastapi import HTTPException

logger = logging.getLogger("agenda_unb.account")

BUCKET = "syllabus_files"


class SupabaseAccountAdmin:
    """Usa a chave de serviço. Nunca registra corpo de resposta, caminho ou id."""

    def __init__(self, supabase_url: str | None = None, service_key: str | None = None):
        self.supabase_url = (
            supabase_url if supabase_url is not None else os.getenv("SUPABASE_URL", "")
        ).rstrip("/")
        self.service_key = (
            service_key if service_key is not None else os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        )

    def _headers(self) -> dict[str, str]:
        if not self.supabase_url or not self.service_key:
            raise HTTPException(status_code=503, detail="Exclusão de conta não configurada no backend.")
        return {"apikey": self.service_key, "Authorization": f"Bearer {self.service_key}"}

    def delete_files(self, stored_paths: list[str]) -> None:
        """Remove os PDFs da conta. Arquivo que já não existe não é erro."""
        prefix = f"{BUCKET}/"
        names = [path[len(prefix):] if path.startswith(prefix) else path for path in stored_paths]
        if not names:
            return
        try:
            response = httpx.request(
                "DELETE",
                f"{self.supabase_url}/storage/v1/object/{BUCKET}",
                headers=self._headers(),
                json={"prefixes": names},
                timeout=20.0,
            )
        except httpx.RequestError as exc:
            logger.warning("Falha de conexão ao remover arquivos da conta (%s).", type(exc).__name__)
            raise HTTPException(status_code=503, detail="O armazenamento está indisponível. Tente novamente.") from exc
        if response.status_code != 200:
            logger.warning("Storage recusou a remoção dos arquivos da conta (HTTP %s).", response.status_code)
            raise HTTPException(status_code=502, detail="Não foi possível remover seus arquivos. Tente novamente.")

    def delete_user(self, user_id: UUID) -> None:
        """Exclui o usuário no Auth; a cascata do banco apaga os dados da conta."""
        try:
            response = httpx.delete(
                f"{self.supabase_url}/auth/v1/admin/users/{user_id}",
                headers=self._headers(),
                timeout=20.0,
            )
        except httpx.RequestError as exc:
            logger.warning("Falha de conexão ao excluir a conta no Auth (%s).", type(exc).__name__)
            raise HTTPException(status_code=503, detail="A autenticação está indisponível. Tente novamente.") from exc
        # 404: a conta já foi removida em uma tentativa anterior.
        if response.status_code not in (200, 204, 404):
            logger.warning("Auth recusou a exclusão da conta (HTTP %s).", response.status_code)
            raise HTTPException(status_code=502, detail="Não foi possível concluir a exclusão. Tente novamente.")


def get_account_admin() -> SupabaseAccountAdmin:
    return SupabaseAccountAdmin()
