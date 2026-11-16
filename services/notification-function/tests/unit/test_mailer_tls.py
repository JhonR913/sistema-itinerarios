import ssl
from unittest.mock import patch

from email.message import EmailMessage

import mailer


def _msg():
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = "a@example.com", "b@example.com", "x"
    m.set_content("hola")
    return m


def test_starttls_verifies_the_server_certificate(monkeypatch):
    monkeypatch.setenv("SMTP_STARTTLS", "1")
    monkeypatch.setenv("SMTP_USER", "u")
    monkeypatch.setenv("SMTP_PASSWORD", "p")
    with patch("mailer.smtplib.SMTP") as smtp_cls:
        smtp = smtp_cls.return_value.__enter__.return_value
        mailer.send(_msg())
    ctx = smtp.starttls.call_args.kwargs["context"]
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True
    smtp.login.assert_called_once_with("u", "p")


def test_without_starttls_nothing_is_negotiated(monkeypatch):
    monkeypatch.delenv("SMTP_STARTTLS", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    with patch("mailer.smtplib.SMTP") as smtp_cls:
        smtp = smtp_cls.return_value.__enter__.return_value
        mailer.send(_msg())
    smtp.starttls.assert_not_called()
    smtp.login.assert_not_called()
