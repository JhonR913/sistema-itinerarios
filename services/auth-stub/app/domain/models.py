"""Dominio del servicio de identidad: usuarios con correo verificado.

Solo reglas de negocio puras (sin FastAPI, SQL, SMTP ni JWT): validaciones de
correo, nombre y contrasena, y las entidades que viajan entre capas."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128
MAX_EMAIL_LENGTH = 254
MAX_NAME_LENGTH = 120
CODE_LENGTH = 6


class DomainError(Exception):
    """Error de regla de negocio. `code` es estable para que el cliente decida."""

    status = 422

    def __init__(self, message: str, code: str = "INVALID"):
        super().__init__(message)
        self.message = message
        self.code = code


class InvalidCredentials(DomainError):
    status = 401

    def __init__(self):
        super().__init__("Correo o contraseña incorrectos", "INVALID_CREDENTIALS")


class EmailNotVerified(DomainError):
    status = 403

    def __init__(self):
        super().__init__("Debes verificar tu correo con el código que te enviamos", "EMAIL_NOT_VERIFIED")


class InvalidCode(DomainError):
    status = 400

    def __init__(self):
        super().__init__("El código es incorrecto o ya venció", "INVALID_CODE")


class TooManyRequests(DomainError):
    status = 429

    def __init__(self, message: str = "Demasiados intentos. Espera unos minutos e intenta de nuevo"):
        super().__init__(message, "TOO_MANY_REQUESTS")


class CodeThrottled(TooManyRequests):
    """Limite por usuario (espera entre envios, tope por hora). Los flujos que no
    deben revelar si un correo existe lo tragan en silencio."""


class EmailDeliveryFailed(DomainError):
    status = 503

    def __init__(self):
        super().__init__("No pudimos enviar el correo. Intenta de nuevo en unos minutos", "EMAIL_DELIVERY_FAILED")


class InvalidSession(DomainError):
    status = 401

    def __init__(self):
        super().__init__("Sesión no valida o vencida", "INVALID_SESSION")


def is_valid_email(value: str) -> bool:
    """usuario@dominio.tld sin espacios. Sin expresion regular a proposito: el
    patron clasico con dos grupos "cualquier cosa menos @ y espacio" separados por
    un punto tiene backtracking super-lineal (ReDoS)."""
    local, at, domain = value.partition("@")
    if not at or not local or "@" in domain or any(c.isspace() for c in value):
        return False
    return "." in domain[1:-1]   # un punto que no sea el primero ni el ultimo del dominio


def normalize_email(value: str) -> str:
    """Correo en minusculas y sin espacios laterales; lanza DomainError si no es valido."""
    email = (value or "").strip().lower()
    if len(email) > MAX_EMAIL_LENGTH or not is_valid_email(email):
        raise DomainError("El correo no tiene un formato valido", "INVALID_EMAIL")
    return email


def validate_name(value: str) -> str:
    name = " ".join((value or "").split())
    if not name:
        raise DomainError("El nombre no puede estar vacio", "INVALID_NAME")
    if len(name) > MAX_NAME_LENGTH:
        raise DomainError("El nombre es demasiado largo", "INVALID_NAME")
    return name


def validate_password(password: str, email: str = "") -> None:
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise DomainError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres", "WEAK_PASSWORD")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise DomainError("La contraseña es demasiado larga", "WEAK_PASSWORD")
    if password.strip() == "" or len(set(password)) < 4:
        raise DomainError("La contraseña es demasiado simple", "WEAK_PASSWORD")
    if email and password.lower() == email.lower():
        raise DomainError("La contraseña no puede ser tu correo", "WEAK_PASSWORD")


def validate_code_format(code: str) -> str:
    cleaned = (code or "").strip()
    if len(cleaned) != CODE_LENGTH or not cleaned.isdigit():
        raise InvalidCode()
    return cleaned


@dataclass(frozen=True)
class User:
    id: str
    email: str
    name: str
    password_hash: str
    verified_at: Optional[datetime] = None
    failed_logins: int = 0
    locked_until: Optional[datetime] = None

    @property
    def is_verified(self) -> bool:
        return self.verified_at is not None


@dataclass(frozen=True)
class CodeRecord:
    id: str
    user_id: str
    purpose: str
    code_hash: str
    expires_at: datetime
    attempts: int
    consumed: bool


@dataclass(frozen=True)
class SessionTokens:
    """Resultado de autenticar: JWT de acceso (memoria del navegador) y token
    opaco de sesion (cookie httpOnly)."""
    access_token: str
    session_token: str
    expires_in_minutes: int
    name: str
    email: str


PURPOSE_VERIFY = "verify"
PURPOSE_RESET = "reset"
