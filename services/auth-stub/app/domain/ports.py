from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from .models import CodeRecord, User


class TokenIssuerPort(ABC):
    """Quien implemente esto decide el algoritmo y el secreto.
    El dominio no sabe que es JWT ni HS256."""

    @abstractmethod
    def issue(self, user: User) -> str:
        ...


class PasswordHasherPort(ABC):
    @abstractmethod
    def hash(self, password: str) -> str:
        ...

    @abstractmethod
    def verify(self, password: str, stored_hash: str) -> bool:
        ...


class CodeHasherPort(ABC):
    """Resumen con clave del codigo de 6 digitos (no se guarda en claro)."""

    @abstractmethod
    def digest(self, user_id: str, purpose: str, code: str) -> str:
        ...


class EmailSenderPort(ABC):
    @abstractmethod
    def send_code(self, to: str, name: str, code: str, purpose: str, ttl_minutes: int) -> None:
        """Lanza EmailDeliveryFailed si el correo no pudo entregarse al servidor SMTP."""

    @abstractmethod
    def send_existing_account_notice(self, to: str, name: str) -> None:
        ...


class UserRepositoryPort(ABC):
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        ...

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        ...

    @abstractmethod
    def create(self, user: User) -> None:
        ...

    @abstractmethod
    def reset_unverified(self, user_id: str, name: str, password_hash: str) -> None:
        """Re-registro de un correo aun no verificado: reemplaza nombre y contrasena."""

    @abstractmethod
    def mark_verified(self, user_id: str, now: datetime) -> None:
        ...

    @abstractmethod
    def set_password(self, user_id: str, password_hash: str) -> None:
        ...

    @abstractmethod
    def register_failed_login(self, user_id: str, now: datetime, max_failures: int, lock_until: datetime) -> None:
        ...

    @abstractmethod
    def clear_failed_logins(self, user_id: str) -> None:
        ...


class CodeRepositoryPort(ABC):
    @abstractmethod
    def create(self, user_id: str, purpose: str, code_hash: str, expires_at: datetime, now: datetime) -> None:
        """Crea un codigo nuevo e invalida los anteriores de ese usuario y proposito."""

    @abstractmethod
    def latest_active(self, user_id: str, purpose: str, now: datetime) -> Optional[CodeRecord]:
        ...

    @abstractmethod
    def register_attempt(self, code_id: str, max_attempts: int) -> bool:
        """Cuenta un intento de forma ATOMICA; False si ya se agotaron. Contar antes de
        comparar evita que peticiones paralelas adivinen mas veces del tope."""

    @abstractmethod
    def consume(self, code_id: str) -> bool:
        """Marca el codigo como usado; False si otra peticion ya lo uso (anti doble uso)."""

    @abstractmethod
    def count_since(self, since: datetime, user_id: Optional[str] = None, purpose: Optional[str] = None) -> int:
        ...

    @abstractmethod
    def last_created_at(self, user_id: str, purpose: str) -> Optional[datetime]:
        ...


class SessionRepositoryPort(ABC):
    @abstractmethod
    def create(self, user_id: str, token_hash: str, expires_at: datetime, now: datetime) -> None:
        ...

    @abstractmethod
    def find_user_id(self, token_hash: str, now: datetime) -> Optional[str]:
        ...

    @abstractmethod
    def revoke(self, token_hash: str) -> None:
        ...

    @abstractmethod
    def revoke_all(self, user_id: str) -> None:
        ...
