"""Configuração exclusiva do servidor; nada disto é enviado ao Vite."""
import os
from dataclasses import dataclass, field
from decimal import Decimal


ERROR_MESSAGES = {
    "pdf_invalido": "Não foi possível ler o PDF. Envie outro arquivo.",
    "pdf_protegido": "Envie um PDF sem proteção por senha.",
    "pdf_sem_texto": "O PDF não possui texto selecionável. Use o cadastro manual.",
    "limite_paginas": "O documento ultrapassa os limites de processamento.",
    "falha_ia": "Não foi possível extrair as avaliações. Tente outro arquivo ou use o cadastro manual.",
    "tempo_esgotado": "O processamento excedeu o tempo disponível.",
    "erro_interno": "Não foi possível concluir o processamento. Use o cadastro manual.",
}


class ProcessingError(Exception):
    def __init__(self, code: str, *, retryable: bool = False):
        self.code = code
        self.retryable = retryable
        super().__init__(ERROR_MESSAGES[code])


@dataclass(frozen=True)
class ProcessingConfig:
    model: str = "gemini-3.5-flash-lite"
    api_key: str = field(default="", repr=False)
    provider_terms_ready: bool = False
    timeout_seconds: float = 12
    attempt_timeout_seconds: float = 18
    max_attempts: int = 2
    retry_delay_seconds: int = 2
    lease_seconds: int = 90
    max_pages: int = 10
    max_text_bytes: int = 40000
    max_output_tokens: int = 4096
    max_file_cost_usd: Decimal = Decimal("0.06")
    input_usd_per_million: Decimal = Decimal("0.30")
    output_usd_per_million: Decimal = Decimal("2.50")

    def __post_init__(self):
        if not (0 < self.timeout_seconds <= 30 and 1 <= self.max_attempts <= 3):
            raise ValueError("Timeout deve estar em (0, 30] e tentativas entre 1 e 3.")
        if not (0 < self.attempt_timeout_seconds <= 60 and
                self.attempt_timeout_seconds + 5 < self.lease_seconds):
            raise ValueError("Prazo da tentativa deve ser de até 60s e menor que o lease.")
        if not (1 <= self.max_pages <= 10 and 1 <= self.max_text_bytes <= 120000):
            raise ValueError("Limites de páginas ou texto inválidos.")
        if not (128 <= self.max_output_tokens <= 8192 and self.lease_seconds >= 90):
            raise ValueError("Limites de saída ou lease inválidos.")
        if self.retry_delay_seconds < 0 or any(not x.is_finite() or x <= 0 for x in (
            self.max_file_cost_usd, self.input_usd_per_million, self.output_usd_per_million
        )):
            raise ValueError("Orçamento, preços e intervalo de tentativas inválidos.")

    @property
    def attempt_reservation(self) -> Decimal:
        # Um token de texto ocupa pelo menos um byte. Margem cobre prompt,
        # esquema e envelope JSON. Sem ferramentas, mídia ou contexto remoto.
        input_bound = self.max_text_bytes + 16000
        return ((input_bound * self.input_usd_per_million +
                 self.max_output_tokens * self.output_usd_per_million) /
                Decimal(1000000)).quantize(Decimal("0.000001"), rounding="ROUND_UP")

    @classmethod
    def from_env(cls):
        model = os.getenv("GEMINI_MODEL", cls.model)
        if model != cls.model and not all(os.getenv(name) for name in (
            "GEMINI_INPUT_USD_PER_MILLION", "GEMINI_OUTPUT_USD_PER_MILLION"
        )):
            raise ValueError("Ao alterar GEMINI_MODEL, configure os dois preços por milhão de tokens.")
        return cls(
            model=model,
            api_key=os.getenv("GEMINI_API_KEY", ""),
            provider_terms_ready=os.getenv("SYLLABUS_PROVIDER_TERMS_READY", "false").lower() == "true",
            timeout_seconds=float(os.getenv("SYLLABUS_AI_TIMEOUT_SECONDS", "12")),
            attempt_timeout_seconds=float(os.getenv("SYLLABUS_ATTEMPT_TIMEOUT_SECONDS", "18")),
            max_attempts=int(os.getenv("SYLLABUS_MAX_ATTEMPTS", "2")),
            max_file_cost_usd=Decimal(os.getenv("SYLLABUS_MAX_FILE_COST_USD", "0.06")),
            input_usd_per_million=Decimal(os.getenv("GEMINI_INPUT_USD_PER_MILLION", "0.30")),
            output_usd_per_million=Decimal(os.getenv("GEMINI_OUTPUT_USD_PER_MILLION", "2.50")),
        )
