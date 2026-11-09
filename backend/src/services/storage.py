import logging
import os
from typing import Dict
import httpx
from fastapi import HTTPException

logger = logging.getLogger("agenda_unb.storage")


class SupabaseStorageService:
    """Serviço de integração com o Supabase Storage."""

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        bucket_name: str = "syllabus_files",
    ):
        self.supabase_url = (supabase_url or os.getenv("SUPABASE_URL", "")).rstrip("/")
        # Chave de serviço (service_role) tem permissão para ignorar RLS e gravar com segurança
        self.supabase_key = (
            supabase_key
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SERVICE_KEY")
            or os.getenv("SUPABASE_ANON_KEY", "")
        )
        self.bucket_name = bucket_name
        # Armazenamento em memória para ambiente de testes e desenvolvimento desconectado
        self._mock_storage: Dict[str, bytes] = {}

    def upload_file(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/pdf",
        auth_token: str | None = None,
    ) -> str:
        """
        Realiza o upload físico do arquivo no bucket do Supabase Storage.
        Retorna a URI relativa no bucket.
        """
        full_path = f"{self.bucket_name}/{path}"

        if not self.supabase_url:
            logger.info("Supabase URL não configurada. Simulando upload para %s", full_path)
            self._mock_storage[path] = content
            return full_path

        key = self.supabase_key or auth_token
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": content_type,
            "x-upsert": "false",
        }
        if self.supabase_key:
            headers["apikey"] = self.supabase_key

        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{path}"
        try:
            response = httpx.post(url, headers=headers, content=content, timeout=10.0)
        except httpx.RequestError as exc:
            logger.error("Erro de conexão ao enviar arquivo para o Storage")
            raise HTTPException(
                status_code=503,
                detail="Falha na conexão com o serviço de armazenamento (Supabase Storage).",
            ) from exc

        if response.status_code not in (200, 201):
            logger.error("Erro retornado pelo Supabase Storage: HTTP %s", response.status_code)
            raise HTTPException(
                status_code=502,
                detail="Erro ao salvar arquivo no bucket de armazenamento.",
            )

        return full_path

    def delete_file(
        self,
        path: str,
        auth_token: str | None = None,
    ) -> bool:
        """
        Compensação atômica: remove o arquivo do Storage caso o registro em banco falhe.
        """
        if not self.supabase_url:
            self._mock_storage.pop(path, None)
            return True

        key = self.supabase_key or auth_token
        headers = {
            "Authorization": f"Bearer {key}",
        }
        if self.supabase_key:
            headers["apikey"] = self.supabase_key

        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{path}"
        try:
            response = httpx.delete(url, headers=headers, timeout=10.0)
            return response.status_code in (200, 204)
        except Exception:
            logger.warning("Falha na compensação/deleção do arquivo no Storage")
            return False

    def download_file(self, path: str, *, max_bytes: int = 10 * 1024 * 1024) -> bytes:
        """Lê um objeto privado, com limite de memória, somente no servidor."""
        if not self.supabase_url:
            if path not in self._mock_storage:
                raise HTTPException(status_code=503, detail="Arquivo indisponível no armazenamento.")
            return self._mock_storage[path]
        headers = {"Authorization": f"Bearer {self.supabase_key}", "apikey": self.supabase_key}
        url = f"{self.supabase_url}/storage/v1/object/{self.bucket_name}/{path}"
        try:
            with httpx.stream("GET", url, headers=headers, timeout=10.0, follow_redirects=False) as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=503, detail="Arquivo indisponível no armazenamento.")
                content = bytearray()
                for chunk in response.iter_bytes():
                    content.extend(chunk)
                    if len(content) > max_bytes:
                        raise HTTPException(status_code=413, detail="Arquivo excede o limite de processamento.")
                return bytes(content)
        except httpx.RequestError:
            raise HTTPException(status_code=503, detail="Armazenamento indisponível.") from None


def get_storage_service() -> SupabaseStorageService:
    return SupabaseStorageService()

