from collections.abc import Iterable
import logging
import os
import re
from urllib.parse import quote, urlsplit

import httpx
from fastapi import Depends, HTTPException

from src.middlewares.auth import CurrentUser, get_current_user

logger = logging.getLogger("agenda_unb.storage")


class SupabaseStorageService:
    """Acessa o bucket privado somente após a API autenticar o usuário."""

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        bucket_name: str = "syllabus_files",
    ):
        self.supabase_url = (
            supabase_url if supabase_url is not None else os.getenv("SUPABASE_URL", "")
        ).rstrip("/")
        self.supabase_key = (
            supabase_key if supabase_key is not None else os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        )
        self.bucket_name = bucket_name

    def _headers(self) -> dict[str, str]:
        if not self.supabase_url or not self.supabase_key:
            raise HTTPException(status_code=503, detail="Armazenamento Supabase não configurado no backend.")
        return {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }

    def _object_url(self, path: str) -> str:
        return f"{self.supabase_url}/storage/v1/object/{quote(self.bucket_name, safe='')}/{quote(path, safe='/')}"

    def normalize_path(self, raw_path: str | None) -> str:
        if not raw_path:
            return ""
        cleaned = raw_path.strip()
        if not cleaned:
            return ""
        if cleaned.startswith(("http://", "https://")):
            parsed_path = urlsplit(cleaned).path
            marker = f"/{self.bucket_name}/"
            if marker not in parsed_path:
                return ""
            cleaned = parsed_path.split(marker, 1)[1]
        cleaned = cleaned.lstrip("/")
        prefix = f"{self.bucket_name}/"
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
        return re.sub(r"/+", "/", cleaned).strip("/")

    @staticmethod
    def _is_not_found(response: httpx.Response) -> bool:
        if response.status_code == 404:
            return True
        if response.status_code == 400:
            try:
                body = response.json()
                return str(body.get("statusCode", "")) == "404"
            except (ValueError, TypeError, AttributeError):
                return False
        return False

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

    def delete_file_if_present(self, path: str) -> bool:
        """Remove um objeto do Storage de forma idempotente (200/204/404 -> True)."""
        object_key = self.normalize_path(path)
        if not object_key:
            return True
        try:
            response = httpx.delete(self._object_url(object_key), headers=self._headers(), timeout=10.0)
        except (httpx.RequestError, HTTPException) as exc:
            logger.warning("Falha ao remover objeto do Storage (%s).", type(exc).__name__)
            return False
        if response.status_code in (200, 204) or self._is_not_found(response):
            return True
        logger.warning("Storage recusou remoção (HTTP %s).", response.status_code)
        return False

    def list_prefix(self, prefix: str, *, page_size: int = 100) -> list[str]:
        """Lista objetos no bucket privado sob o prefixo informado."""
        clean_prefix = self.normalize_path(prefix)
        headers = {**self._headers(), "Content-Type": "application/json"}
        list_url = f"{self.supabase_url}/storage/v1/object/list/{quote(self.bucket_name, safe='')}"
        results: list[str] = []
        offset = 0
        while True:
            payload = {
                "prefix": clean_prefix,
                "limit": page_size,
                "offset": offset,
                "sortBy": {"column": "name", "order": "asc"},
            }
            try:
                response = httpx.post(list_url, headers=headers, json=payload, timeout=10.0)
            except httpx.RequestError as exc:
                logger.warning("Falha ao listar objetos no Storage (%s).", type(exc).__name__)
                raise HTTPException(
                    status_code=503,
                    detail="Não foi possível verificar arquivos no armazenamento.",
                ) from exc
            if response.status_code != 200:
                logger.warning("Storage recusou listagem (HTTP %s).", response.status_code)
                raise HTTPException(
                    status_code=503,
                    detail="Não foi possível verificar arquivos no armazenamento.",
                )
            try:
                items = response.json()
            except ValueError as exc:
                logger.warning("Resposta inválida do Storage na listagem (%s).", type(exc).__name__)
                raise HTTPException(
                    status_code=503,
                    detail="Não foi possível verificar arquivos no armazenamento.",
                ) from exc
            if not isinstance(items, list):
                raise HTTPException(
                    status_code=503,
                    detail="Não foi possível verificar arquivos no armazenamento.",
                )
            for item in items:
                if not isinstance(item, dict) or item.get("id") is None:
                    continue
                name = str(item.get("name") or "").lstrip("/")
                if not name:
                    continue
                if clean_prefix and not name.startswith(f"{clean_prefix}/"):
                    results.append(f"{clean_prefix}/{name}")
                else:
                    results.append(name)
            if len(items) < page_size:
                break
            offset += page_size
        return results

    def delete_objects_strict(self, paths: Iterable[str]) -> int:
        """Remove objetos no Storage; trata 404 como idempotente e aborta com 503 em falha."""
        headers = self._headers()
        unique_paths = list(dict.fromkeys(p for p in (self.normalize_path(raw) for raw in paths) if p))
        removed = 0
        for object_key in unique_paths:
            try:
                response = httpx.delete(self._object_url(object_key), headers=headers, timeout=10.0)
            except httpx.RequestError as exc:
                logger.warning("Falha ao excluir objeto do Storage (%s).", type(exc).__name__)
                raise HTTPException(
                    status_code=503,
                    detail="Não foi possível remover arquivos do armazenamento.",
                ) from exc
            if response.status_code in (200, 204):
                removed += 1
            elif self._is_not_found(response):
                continue
            else:
                logger.warning("Storage recusou exclusão (HTTP %s).", response.status_code)
                raise HTTPException(
                    status_code=503,
                    detail="Não foi possível remover arquivos do armazenamento.",
                )
        return removed

    def download_file(self, path: str, *, max_bytes: int = 10 * 1024 * 1024) -> bytes:
        """Lê um objeto privado, com limite de memória, somente no servidor."""
        headers = self._headers()
        url = self._object_url(path)
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


def get_storage_service(current_user: CurrentUser = Depends(get_current_user)) -> SupabaseStorageService:
    return SupabaseStorageService()
