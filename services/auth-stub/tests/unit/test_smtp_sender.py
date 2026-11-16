from unittest.mock import MagicMock, patch

import pytest

from app.domain.models import EmailDeliveryFailed
from app.infrastructure.adapters.smtp_sender import SmtpEmailSender


def _sender(**kw):
    return SmtpEmailSender("smtp.example.com", 587, "app@example.com", **kw)


def test_sends_code_with_starttls_and_login():
    with patch("app.infrastructure.adapters.smtp_sender.smtplib.SMTP") as smtp_cls:
        smtp = smtp_cls.return_value.__enter__.return_value
        _sender(starttls=True, user="u", password="p").send_code("ana@example.com", "Ana", "123456", "verify", 10)
    smtp.starttls.assert_called_once()
    smtp.login.assert_called_once_with("u", "p")
    msg = smtp.send_message.call_args[0][0]
    assert msg["To"] == "ana@example.com" and "123456" in msg["Subject"] and "123456" in msg.get_content()


def test_dev_mode_has_no_tls_nor_login():
    with patch("app.infrastructure.adapters.smtp_sender.smtplib.SMTP") as smtp_cls:
        smtp = smtp_cls.return_value.__enter__.return_value
        _sender().send_code("ana@example.com", "Ana", "123456", "reset", 10)
    smtp.starttls.assert_not_called()
    smtp.login.assert_not_called()
    assert "contraseña" in smtp.send_message.call_args[0][0]["Subject"]


def test_smtp_errors_become_domain_error_without_leaking_credentials(caplog):
    import smtplib
    with patch("app.infrastructure.adapters.smtp_sender.smtplib.SMTP") as smtp_cls:
        smtp_cls.return_value.__enter__.return_value.login.side_effect = smtplib.SMTPAuthenticationError(535, b"bad")
        with pytest.raises(EmailDeliveryFailed):
            _sender(user="u", password="secreta-123").send_code("a@b.co", "A", "123456", "verify", 10)
    assert "secreta-123" not in caplog.text and "123456" not in caplog.text


def test_connection_refused_is_domain_error():
    with patch("app.infrastructure.adapters.smtp_sender.smtplib.SMTP", side_effect=ConnectionRefusedError):
        with pytest.raises(EmailDeliveryFailed):
            _sender().send_existing_account_notice("a@b.co", "A")


def test_header_injection_in_name_cannot_add_headers():
    with patch("app.infrastructure.adapters.smtp_sender.smtplib.SMTP") as smtp_cls:
        smtp = smtp_cls.return_value.__enter__.return_value
        _sender().send_code("a@b.co", "Ana\nBcc: x@evil.com", "123456", "verify", 10)
    assert smtp.send_message.call_args[0][0]["Bcc"] is None
