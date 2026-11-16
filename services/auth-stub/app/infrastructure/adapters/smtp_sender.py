"""Envia los correos de identidad por SMTP. En desarrollo apunta a Mailpit
(sin TLS ni autenticacion); en produccion a Gmail (smtp.gmail.com:587 con
STARTTLS y contrasena de aplicacion). Las credenciales vienen del entorno."""
import logging
from typing import Optional
import smtplib
import ssl
from email.message import EmailMessage

from app.domain.models import PURPOSE_RESET, EmailDeliveryFailed
from app.domain.ports import EmailSenderPort

logger = logging.getLogger("auth")

_SIGNATURE = "\nSistema de Itinerarios Personales\n"


class SmtpEmailSender(EmailSenderPort):
    def __init__(self, host: str, port: int, sender: str, starttls: bool = False,
                 user: str = "", password: Optional[str] = None, timeout: float = 10.0):
        self._host, self._port, self._sender = host, port, sender
        self._starttls, self._user, self._password, self._timeout = starttls, user, password, timeout

    def send_code(self, to: str, name: str, code: str, purpose: str, ttl_minutes: int) -> None:
        if purpose == PURPOSE_RESET:
            subject = f"Código para cambiar tu contraseña: {code}"
            intro = "Recibimos una solicitud para cambiar tu contraseña."
        else:
            subject = f"Tu código de verificación: {code}"
            intro = "Gracias por registrarte. Usa este código para verificar tu correo."
        body = (f"Hola {name},\n\n{intro}\n\n    Código: {code}\n\n"
                f"Vence en {ttl_minutes} minutos y solo sirve una vez. "
                "Si no fuiste tú, ignora este mensaje: nadie puede entrar sin el código.\n" + _SIGNATURE)
        self._deliver(to, subject, body)

    def send_existing_account_notice(self, to: str, name: str) -> None:
        body = (f"Hola {name},\n\nAlguien intentó registrar este correo, pero ya tienes una cuenta. "
                "Si fuiste tú, inicia sesión (o usa \"Olvidé mi contraseña\"). Si no, ignora este mensaje.\n" + _SIGNATURE)
        self._deliver(to, "Ya tienes una cuenta en Itinerarios", body)

    def _deliver(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()  # rechaza saltos de linea en cabeceras (anti header-injection)
        msg["From"], msg["To"], msg["Subject"] = self._sender, to, subject
        msg.set_content(body)
        try:
            with smtplib.SMTP(self._host, self._port, timeout=self._timeout) as smtp:
                if self._starttls:
                    smtp.starttls(context=ssl.create_default_context())
                if self._user:
                    smtp.login(self._user, self._password or "")
                smtp.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:
            logger.error("fallo SMTP (%s): %s", type(exc).__name__, exc)  # sin credenciales ni cuerpo
            raise EmailDeliveryFailed() from exc
