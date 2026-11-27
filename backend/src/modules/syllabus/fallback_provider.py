"""Fallback REST OpenAI-compatible com endpoints fixos e modelos gratuitos."""
import json
import re
import time

import httpx

from src.modules.syllabus.gemini import SYSTEM_INSTRUCTION
from src.modules.syllabus.extraction import validate_candidates
from src.modules.syllabus.processing_config import ProcessingConfig, ProcessingError

FALLBACK_PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "llama-3.3-70b-versatile"),
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions", "openrouter/free"),
    "mistral": ("https://api.mistral.ai/v1/chat/completions", "mistral-small-latest"),
}


class OpenAICompatibleFallbackProvider:
    """Top-level/picklable provider, sem URLs externas configuráveis."""

    def __init__(self, config: ProcessingConfig, *, transport=None):
        if config.fallback_provider not in FALLBACK_PROVIDERS:
            raise ValueError("Provedor de contingência não permitido.")
        endpoint, default_model = FALLBACK_PROVIDERS[config.fallback_provider]
        self.endpoint = endpoint
        self.model = config.fallback_model or default_model
        self.api_key = config.fallback_api_key
        self.provider = config.fallback_provider
        self.terms_ready = config.provider_terms_ready
        self.timeout = config.fallback_timeout_seconds
        self.transport = transport
        self.provider_name = config.fallback_provider
        self.model_name = self.model

    def extract(self, pages):
        if not self.terms_ready:
            raise ProcessingError("falha_ia", reason="missing_terms")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {"role": "user", "content": json.dumps({"paginas": [vars(p) for p in pages]}, ensure_ascii=False)},
            ],
            "temperature": 0,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
        }
        started = time.monotonic()
        try:
            with httpx.Client(timeout=self.timeout, follow_redirects=False, transport=self.transport) as client:
                with client.stream("POST", self.endpoint,
                                   headers={"Authorization": f"Bearer {self.api_key}",
                                            "Content-Type": "application/json"},
                                   content=json.dumps(payload, ensure_ascii=False).encode()) as response:
                    if response.status_code != 200:
                        status = response.status_code
                        raise ProcessingError("falha_ia", retryable=status == 429 or status >= 500,
                                              rate_limited=status == 429,
                                              reason=f"fallback_http_{status}")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 256000:
                            raise ProcessingError("falha_ia", reason="fallback_response_too_large")
                        if time.monotonic() - started > self.timeout:
                            raise ProcessingError("tempo_esgotado", retryable=True, reason="fallback_timeout")
            data = json.loads(body)
            content = data["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content:
                raise ValueError("empty response")
            return content
        except ProcessingError:
            raise
        except httpx.TimeoutException:
            raise ProcessingError("tempo_esgotado", retryable=True, reason="fallback_timeout") from None
        except httpx.RequestError:
            raise ProcessingError("falha_ia", retryable=True, reason="fallback_request_error") from None
        except (ValueError, KeyError, TypeError, IndexError):
            raise ProcessingError("falha_ia", reason="fallback_invalid_response") from None


class FallbackRoutingProvider:
    """Executa Gemini primeiro e usa fallback apenas em falhas remotas elegíveis."""

    def __init__(self, primary, fallback=None):
        self.primary = primary
        self.fallback = fallback
        self.provider_name = "google"
        self.model_name = getattr(primary, "model_name", "")
        self.deadline = None
        self.fallback_used = False
        self.primary_error_reason = ""
        self.validation_context = {}

    def set_deadline(self, deadline):
        self.deadline = deadline

    def set_validation_context(self, **context):
        self.validation_context = context

    def extract(self, pages):
        try:
            result = self.primary.extract(pages)
            validate_candidates(result, pages, **self.validation_context)
            self.provider_name = "google"
            self.model_name = getattr(self.primary, "model_name", "")
            self.fallback_used = False
            return result
        except ProcessingError as primary_error:
            if self.fallback is None or primary_error.reason in (
                "missing_key_or_terms", "missing_terms", "payload_too_large"
            ) or primary_error.code not in ("falha_ia", "tempo_esgotado"):
                raise
            if self.deadline is not None:
                remaining = self.deadline - time.monotonic()
                if remaining < 2:
                    raise ProcessingError("tempo_esgotado", retryable=True, reason="fallback_budget_exhausted") from None
                self.fallback.timeout = min(self.fallback.timeout, remaining)
            self.primary_error_reason = primary_error.reason if re.fullmatch(
                r"[a-z0-9_]{1,40}", primary_error.reason or ""
            ) else "remote_failure"
            try:
                result = self.fallback.extract(pages)
                validate_candidates(result, pages, **self.validation_context)
                self.provider_name = getattr(self.fallback, "provider_name", "fallback")
                self.model_name = getattr(self.fallback, "model_name", "")
                self.fallback_used = True
                return result
            except ProcessingError as fallback_error:
                raise ProcessingError(
                    fallback_error.code,
                    retryable=primary_error.retryable or fallback_error.retryable,
                    rate_limited=primary_error.rate_limited or fallback_error.rate_limited,
                    reason="fallback_" + (fallback_error.reason or "failed"),
                ) from None
