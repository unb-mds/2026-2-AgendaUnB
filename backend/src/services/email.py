"""Serviço de e-mail transacional via Supabase Auth Admin API.

O envio de e-mails (confirmação e recuperação) é delegado ao Supabase Auth,
que consome as credenciais SMTP configuradas no servidor. Este módulo valida
que as variáveis de ambiente necessárias estão presentes e oferece um cliente
tipado para disparar convites e redefinições a partir do backend quando
necessário (ex.: notificações internas futuras).

Referência: https://supabase.com/docs/reference/python/auth-admin-inviteuserbycremail
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SmtpSettings:
    """Configuração SMTP lida das variáveis de ambiente.

    Estas variáveis são consumidas pelo Supabase Auth (GoTrue) para disparar
    e-mails de confirmação, recuperação e convite. O backend apenas valida
    que estão presentes para detectar configuração incompleta em deploy.
    """

    host: str
    port: int
    user: str
    sender_email: str
    sender_name: str
    # A senha nunca é logada nem devolvida pela API.
    _password: str = field(repr=False)

    # ---------- fábrica ----------

    @classmethod
    def from_env(cls) -> "SmtpSettings":
        """Lê e valida as variáveis de ambiente SMTP.

        Levanta ``SmtpConfigError`` quando alguma variável obrigatória
        está ausente ou com valor inválido.
        """
        host = os.getenv("SMTP_HOST", "").strip()
        port_raw = os.getenv("SMTP_PORT", "587").strip()
        user = os.getenv("SMTP_USER", "").strip()
        password = os.getenv("SMTP_PASS", "").strip()
        sender_email = os.getenv("SMTP_SENDER_EMAIL", "").strip()
        sender_name = os.getenv("SMTP_SENDER_NAME", "Agenda UnB").strip()

        errors: list[str] = []
        if not host:
            errors.append("SMTP_HOST não configurado")
        if not user:
            errors.append("SMTP_USER não configurado")
        if not password:
            errors.append("SMTP_PASS não configurado")
        if not sender_email:
            errors.append("SMTP_SENDER_EMAIL não configurado")

        try:
            port = int(port_raw)
            if port not in range(1, 65536):
                raise ValueError
        except ValueError:
            errors.append(f"SMTP_PORT inválido: {port_raw!r} (esperado 1–65535)")
            port = 587  # valor padrão para não bloquear demais validações

        if errors:
            raise SmtpConfigError(errors)

        return cls(
            host=host,
            port=port,
            user=user,
            sender_email=sender_email,
            sender_name=sender_name,
            _password=password,
        )

    # ---------- consultas ----------

    def is_tls_port(self) -> bool:
        """Retorna True quando a porta sugere TLS implícito (465)."""
        return self.port == 465

    def summary(self) -> dict:
        """Retorna metadados públicos — sem a senha."""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "sender_email": self.sender_email,
            "sender_name": self.sender_name,
            "tls": self.is_tls_port(),
        }


class SmtpConfigError(Exception):
    """Levantada quando variáveis SMTP estão ausentes ou inválidas."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def smtp_config_status(env: dict | None = None) -> dict:
    """Verifica o status da configuração SMTP a partir do ambiente.

    Retorna um dicionário com ``ok`` (bool) e, quando há erros,
    ``errors`` (lista de strings descritivas).  Usado pelo health check
    e pelo CI para validar o ambiente antes de implantar.

    Args:
        env: dicionário de variáveis de ambiente (padrão: ``os.environ``).
    """
    if env is not None:
        # Troca temporariamente o ambiente para facilitar testes unitários.
        import unittest.mock as mock
        with mock.patch.dict(os.environ, env, clear=False):
            return _check_smtp()
    return _check_smtp()


def _check_smtp() -> dict:
    try:
        settings = SmtpSettings.from_env()
        return {"ok": True, "summary": settings.summary()}
    except SmtpConfigError as exc:
        return {"ok": False, "errors": exc.errors}
