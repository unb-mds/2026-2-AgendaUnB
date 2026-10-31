import logging
import os
from urllib.parse import quote

import httpx
from fastapi import Depends, HTTPException

from src.middlewares.auth import CurrentUser, get_current_user

logger = logging.getLogger("agenda_unb.storage")


class SupabaseStorageService:
    """Acessa o bucket privado com a sessão do usuário, preservando a RLS."""

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        bucket_name: str = "syllabus_files",
        auth_token: str | None = None,
    ):
        self.supabase_url = (
            supabase_url if supabase_url is not None else os.getenv("SUPABASE_URL", "")
        ).rstrip("/")
        self.supabase_key = (
            supabase_key if supabase_key is not None else os.getenv("SUPABASE_ANON_KEY", "")
        )
        self.bucket_name = bucket_name
        self._auth_token = auth_token

    def _headers(self) -> dict[str, str]:
        if not self.supabase_url or not self.supabase_key:
            raise HTTPException(status_code=503, detail="Armazenamento Supabase não configurado no backend.")
        if not self._auth_token:
            raise HTTPException(status_code=401, detail="Sessão necessária para acessar o armazenamento.")
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self._auth_token}",
        }

    def _object_url(self, path: str) -> str:
        return f"{self.supabase_url}/storage/v1/object/{quote(self.bucket_name, safe='')}/{quote(path, safe='/')}"

    def upload_file(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/pdf",
    ) -> str:
        headers = {**self._headers(), "Content-Type": content_type, "x-upsert": "false"}
        try:
            response = httpx.post(self._object_url(path), headers=headers, content=content, timeout=10.0)
        except httpx.RequestError as exc:
            logger.warning("Falha de conexão no upload ao Storage (%s).", type(exc).__name__)
            raise HTTPException(status_code=503, detail="O armazenamento está indisponível. Tente novamente.") from exc

        if response.status_code not in (200, 201):
            # Storage may wrap a 403 inside an HTTP 400. Never expose its raw body.
            try:
                body = response.json()
                storage_status = int(body.get("statusCode", response.status_code))
            except (ValueError, TypeError, AttributeError):
                storage_status = response.status_code
            logger.warning("Storage recusou upload (HTTP %s, código %s).", response.status_code, storage_status)
            if storage_status == 401:
                raise HTTPException(status_code=401, detail="Sua sessão expirou. Entre novamente para enviar o plano.")
            if storage_status == 403:
                raise HTTPException(status_code=403, detail="O armazenamento não autorizou este envio. Entre novamente; se persistir, contate o suporte.")
            raise HTTPException(status_code=502, detail="Não foi possível salvar o PDF no armazenamento. Tente novamente.")

        return f"{self.bucket_name}/{path}"

    def delete_file(self, path: str) -> bool:
        """Remove o arquivo enviado caso a persistência em banco falhe."""
        try:
            response = httpx.delete(self._object_url(path), headers=self._headers(), timeout=10.0)
        except (httpx.RequestError, HTTPException) as exc:
            logger.warning("Falha na compensação do Storage (%s).", type(exc).__name__)
            return False
        if response.status_code not in (200, 204):
            logger.warning("Storage recusou compensação (HTTP %s).", response.status_code)
            return False
        return True


def get_storage_service(current_user: CurrentUser = Depends(get_current_user)) -> SupabaseStorageService:
    return SupabaseStorageService(auth_token=current_user.access_token)
