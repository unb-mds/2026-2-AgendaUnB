"""Testes unitários para o módulo de e-mail / SMTP (src.services.email).

Validam:
- Leitura correta das variáveis de ambiente.
- Levantamento de SmtpConfigError quando variáveis obrigatórias faltam.
- Detecção de porta inválida.
- Que a senha nunca aparece no summary() nem na repr().
- Função smtp_config_status() em cenários de sucesso e falha.
"""

import os
import pytest

from src.services.email import SmtpConfigError, SmtpSettings, smtp_config_status


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_ENV = {
    "SMTP_HOST": "smtp.mailgun.org",
    "SMTP_PORT": "587",
    "SMTP_USER": "postmaster@mg.agendaunb.example",
    "SMTP_PASS": "super-secret-key",
    "SMTP_SENDER_EMAIL": "noreply@agendaunb.example",
    "SMTP_SENDER_NAME": "Agenda UnB",
}


def _with_env(overrides: dict, monkeypatch):
    env = {**VALID_ENV, **overrides}
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


# ---------------------------------------------------------------------------
# SmtpSettings.from_env — casos válidos
# ---------------------------------------------------------------------------


def test_smtp_settings_reads_all_fields(monkeypatch):
    _with_env({}, monkeypatch)
    settings = SmtpSettings.from_env()
    assert settings.host == "smtp.mailgun.org"
    assert settings.port == 587
    assert settings.user == "postmaster@mg.agendaunb.example"
    assert settings.sender_email == "noreply@agendaunb.example"
    assert settings.sender_name == "Agenda UnB"


def test_smtp_settings_default_sender_name(monkeypatch):
    _with_env({"SMTP_SENDER_NAME": None}, monkeypatch)
    # Sem SMTP_SENDER_NAME, usa o default "Agenda UnB".
    settings = SmtpSettings.from_env()
    assert settings.sender_name == "Agenda UnB"


def test_smtp_settings_tls_port_465(monkeypatch):
    _with_env({"SMTP_PORT": "465"}, monkeypatch)
    settings = SmtpSettings.from_env()
    assert settings.is_tls_port() is True


def test_smtp_settings_starttls_port_587(monkeypatch):
    _with_env({}, monkeypatch)
    settings = SmtpSettings.from_env()
    assert settings.is_tls_port() is False


# ---------------------------------------------------------------------------
# SmtpSettings.from_env — casos inválidos
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_key", ["SMTP_HOST", "SMTP_USER", "SMTP_PASS", "SMTP_SENDER_EMAIL"])
def test_smtp_config_error_raised_when_required_key_missing(monkeypatch, missing_key):
    _with_env({missing_key: None}, monkeypatch)
    with pytest.raises(SmtpConfigError) as exc_info:
        SmtpSettings.from_env()
    assert any(missing_key in err or "não configurado" in err for err in exc_info.value.errors)


def test_smtp_config_error_on_invalid_port(monkeypatch):
    _with_env({"SMTP_PORT": "nao-e-numero"}, monkeypatch)
    with pytest.raises(SmtpConfigError) as exc_info:
        SmtpSettings.from_env()
    assert any("SMTP_PORT" in err for err in exc_info.value.errors)


def test_smtp_config_error_on_port_zero(monkeypatch):
    _with_env({"SMTP_PORT": "0"}, monkeypatch)
    with pytest.raises(SmtpConfigError):
        SmtpSettings.from_env()


def test_smtp_config_error_aggregates_multiple_missing_vars(monkeypatch):
    for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("SMTP_SENDER_EMAIL", "x@example.com")
    with pytest.raises(SmtpConfigError) as exc_info:
        SmtpSettings.from_env()
    assert len(exc_info.value.errors) == 3


# ---------------------------------------------------------------------------
# Segurança: a senha nunca deve vazar
# ---------------------------------------------------------------------------


def test_smtp_password_not_in_summary(monkeypatch):
    _with_env({}, monkeypatch)
    settings = SmtpSettings.from_env()
    summary = settings.summary()
    assert "super-secret-key" not in str(summary)
    assert "password" not in summary
    assert "_password" not in summary


def test_smtp_password_not_in_repr(monkeypatch):
    _with_env({}, monkeypatch)
    settings = SmtpSettings.from_env()
    assert "super-secret-key" not in repr(settings)


# ---------------------------------------------------------------------------
# smtp_config_status()
# ---------------------------------------------------------------------------


def test_smtp_config_status_ok(monkeypatch):
    _with_env({}, monkeypatch)
    status = smtp_config_status()
    assert status["ok"] is True
    assert "summary" in status
    assert status["summary"]["host"] == "smtp.mailgun.org"


def test_smtp_config_status_error(monkeypatch):
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    monkeypatch.delenv("SMTP_PASS", raising=False)
    monkeypatch.delenv("SMTP_SENDER_EMAIL", raising=False)
    status = smtp_config_status()
    assert status["ok"] is False
    assert "errors" in status
    assert len(status["errors"]) >= 1


def test_smtp_config_status_with_explicit_env():
    # Versão que passa env explicitamente, sem tocar no os.environ real.
    status = smtp_config_status(env=VALID_ENV)
    assert status["ok"] is True


def test_smtp_config_status_with_missing_in_explicit_env():
    env = {k: v for k, v in VALID_ENV.items() if k != "SMTP_HOST"}
    # Remove também do ambiente real para garantir que não vaza.
    old = os.environ.pop("SMTP_HOST", None)
    try:
        status = smtp_config_status(env=env)
    finally:
        if old is not None:
            os.environ["SMTP_HOST"] = old
    assert status["ok"] is False
