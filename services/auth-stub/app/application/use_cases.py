"""Casos de uso de identidad. Dependen solo de puertos (dominio), nunca de
SQL, SMTP o JWT. Reglas clave:

* El correo se verifica con un codigo de 6 digitos de un solo uso (vence, tiene
  tope de intentos y se guarda con resumen con clave, no en claro).
* No se revela si un correo ya esta registrado (registro, reenvio y olvido de
  contrasena responden igual exista o no la cuenta).
* Login con bloqueo temporal tras varios fallos y comparacion en tiempo
  constante (tambien cuando el usuario no existe).
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from app.domain.models import (
    PURPOSE_RESET,
    PURPOSE_VERIFY,
    CodeThrottled,
    CodeRecord,
    DomainError,
    EmailDeliveryFailed,
    EmailNotVerified,
    InvalidCode,
    InvalidCredentials,
    InvalidSession,
    SessionTokens,
    TooManyRequests,
    User,
    normalize_email,
    validate_code_format,
    validate_name,
    validate_password,
)
from app.domain.ports import (
    CodeHasherPort,
    CodeRepositoryPort,
    EmailSenderPort,
    PasswordHasherPort,
    SessionRepositoryPort,
    TokenIssuerPort,
    UserRepositoryPort,
)

Clock = Callable[[], datetime]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class IdentityPolicy:
    """Parametros de seguridad (configurables por entorno)."""

    def __init__(self, code_ttl_minutes: int = 10, max_code_attempts: int = 5,
                 resend_cooldown_seconds: int = 60, max_codes_per_hour: int = 5,
                 max_codes_per_hour_global: int = 100, max_failed_logins: int = 5,
                 lock_minutes: int = 15, session_days: int = 14, access_ttl_minutes: int = 30):
        self.code_ttl_minutes = code_ttl_minutes
        self.max_code_attempts = max_code_attempts
        self.resend_cooldown_seconds = resend_cooldown_seconds
        self.max_codes_per_hour = max_codes_per_hour
        self.max_codes_per_hour_global = max_codes_per_hour_global
        self.max_failed_logins = max_failed_logins
        self.lock_minutes = lock_minutes
        self.session_days = session_days
        self.access_ttl_minutes = access_ttl_minutes


class CodeService:
    """Emision y comprobacion de códigos de un solo uso."""

    def __init__(self, codes: CodeRepositoryPort, hasher: CodeHasherPort, sender: EmailSenderPort,
                 policy: IdentityPolicy, clock: Clock = _utcnow):
        self._codes, self._hasher, self._sender = codes, hasher, sender
        self._policy, self._clock = policy, clock

    def issue(self, user: User, purpose: str) -> None:
        now = self._clock()
        last = self._codes.last_created_at(user.id, purpose)
        if last is not None and (now - last).total_seconds() < self._policy.resend_cooldown_seconds:
            raise CodeThrottled("Espera un momento antes de pedir otro código")
        hour_ago = now - timedelta(hours=1)
        if self._codes.count_since(hour_ago, user_id=user.id, purpose=purpose) >= self._policy.max_codes_per_hour:
            raise CodeThrottled("Pediste demasiados códigos. Intenta de nuevo en una hora")
        if self._codes.count_since(hour_ago) >= self._policy.max_codes_per_hour_global:
            raise TooManyRequests("El servicio está recibiendo muchas solicitudes. Intenta más tarde")
        code = f"{secrets.randbelow(10 ** 6):06d}"
        self._codes.create(user.id, purpose, self._hasher.digest(user.id, purpose, code),
                           now + timedelta(minutes=self._policy.code_ttl_minutes), now)
        self._sender.send_code(user.email, user.name, code, purpose, self._policy.code_ttl_minutes)

    def check(self, user: User, purpose: str, code: str) -> None:
        """Valida y consume el código. Todo fallo es InvalidCode (sin pistas)."""
        code = validate_code_format(code)
        record: Optional[CodeRecord] = self._codes.latest_active(user.id, purpose, self._clock())
        if record is None or not self._codes.register_attempt(record.id, self._policy.max_code_attempts):
            raise InvalidCode()
        expected = self._hasher.digest(user.id, purpose, code)
        if not secrets.compare_digest(expected, record.code_hash):
            raise InvalidCode()
        if not self._codes.consume(record.id):
            raise InvalidCode()


class SessionService:
    def __init__(self, sessions: SessionRepositoryPort, tokens: TokenIssuerPort,
                 policy: IdentityPolicy, clock: Clock = _utcnow):
        self._sessions, self._tokens, self._policy, self._clock = sessions, tokens, policy, clock

    def start(self, user: User) -> SessionTokens:
        now = self._clock()
        session_token = secrets.token_urlsafe(32)
        self._sessions.create(user.id, hash_session_token(session_token),
                              now + timedelta(days=self._policy.session_days), now)
        return self.tokens_for(user, session_token)

    def tokens_for(self, user: User, session_token: str) -> SessionTokens:
        return SessionTokens(access_token=self._tokens.issue(user), session_token=session_token,
                             expires_in_minutes=self._policy.access_ttl_minutes,
                             name=user.name, email=user.email)


class Register:
    def __init__(self, users: UserRepositoryPort, passwords: PasswordHasherPort, codes: CodeService,
                 sender: EmailSenderPort):
        self._users, self._passwords, self._codes, self._sender = users, passwords, codes, sender

    def execute(self, email: str, name: str, password: str) -> None:
        email = normalize_email(email)
        name = validate_name(name)
        validate_password(password, email)
        password_hash = self._passwords.hash(password)  # siempre: el tiempo no delata si existia
        existing = self._users.get_by_email(email)
        if existing is not None and existing.is_verified:
            try:
                self._sender.send_existing_account_notice(email, existing.name)
            except EmailDeliveryFailed:
                pass  # no revelar nada al cliente
            return
        if existing is not None:
            self._users.reset_unverified(existing.id, name, password_hash)
            user = User(existing.id, email, name, password_hash)
        else:
            user = User(str(uuid.uuid4()), email, name, password_hash)
            self._users.create(user)
        try:
            self._codes.issue(user, PURPOSE_VERIFY)
        except CodeThrottled:
            pass  # ya tiene un codigo vigente


class VerifyEmail:
    def __init__(self, users: UserRepositoryPort, codes: CodeService, sessions: SessionService,
                 clock: Clock = _utcnow):
        self._users, self._codes, self._sessions, self._clock = users, codes, sessions, clock

    def execute(self, email: str, code: str) -> SessionTokens:
        user = self._users.get_by_email(normalize_email(email))
        if user is None:
            raise InvalidCode()
        self._codes.check(user, PURPOSE_VERIFY, code)
        self._users.mark_verified(user.id, self._clock())
        return self._sessions.start(self._users.get_by_id(user.id) or user)


class ResendCode:
    def __init__(self, users: UserRepositoryPort, codes: CodeService):
        self._users, self._codes = users, codes

    def execute(self, email: str) -> None:
        user = self._users.get_by_email(normalize_email(email))
        if user is None or user.is_verified:
            return
        try:
            self._codes.issue(user, PURPOSE_VERIFY)
        except CodeThrottled:
            return


class Login:
    def __init__(self, users: UserRepositoryPort, passwords: PasswordHasherPort, codes: CodeService,
                 sessions: SessionService, policy: IdentityPolicy, clock: Clock = _utcnow):
        self._users, self._passwords, self._codes = users, passwords, codes
        self._sessions, self._policy, self._clock = sessions, policy, clock
        self._dummy_hash: Optional[str] = None

    def _dummy(self) -> str:
        if self._dummy_hash is None:
            self._dummy_hash = self._passwords.hash(secrets.token_urlsafe(12))
        return self._dummy_hash

    def execute(self, email: str, password: str) -> SessionTokens:
        try:
            email = normalize_email(email)
        except DomainError:
            raise InvalidCredentials()
        user = self._users.get_by_email(email)
        now = self._clock()
        if user is None:
            self._passwords.verify(password or "", self._dummy())
            raise InvalidCredentials()
        if user.locked_until is not None and user.locked_until > now:
            raise TooManyRequests("Cuenta bloqueada temporalmente por intentos fallidos. Intenta más tarde")
        if not self._passwords.verify(password or "", user.password_hash):
            self._users.register_failed_login(
                user.id, now, self._policy.max_failed_logins, now + timedelta(minutes=self._policy.lock_minutes))
            raise InvalidCredentials()
        if not user.is_verified:
            try:
                self._codes.issue(user, PURPOSE_VERIFY)
            except CodeThrottled:
                pass
            raise EmailNotVerified()
        self._users.clear_failed_logins(user.id)
        return self._sessions.start(user)


class RefreshSession:
    def __init__(self, users: UserRepositoryPort, sessions_repo: SessionRepositoryPort,
                 sessions: SessionService, clock: Clock = _utcnow):
        self._users, self._repo, self._sessions, self._clock = users, sessions_repo, sessions, clock

    def execute(self, session_token: Optional[str]) -> SessionTokens:
        if not session_token:
            raise InvalidSession()
        user_id = self._repo.find_user_id(hash_session_token(session_token), self._clock())
        user = self._users.get_by_id(user_id) if user_id else None
        if user is None or not user.is_verified:
            raise InvalidSession()
        return self._sessions.tokens_for(user, session_token)


class Logout:
    def __init__(self, sessions_repo: SessionRepositoryPort):
        self._repo = sessions_repo

    def execute(self, session_token: Optional[str]) -> None:
        if session_token:
            self._repo.revoke(hash_session_token(session_token))


class ForgotPassword:
    def __init__(self, users: UserRepositoryPort, codes: CodeService):
        self._users, self._codes = users, codes

    def execute(self, email: str) -> None:
        user = self._users.get_by_email(normalize_email(email))
        if user is None or not user.is_verified:
            return
        try:
            self._codes.issue(user, PURPOSE_RESET)
        except (CodeThrottled, EmailDeliveryFailed):
            return  # sin pistas sobre la existencia de la cuenta


class ResetPassword:
    def __init__(self, users: UserRepositoryPort, passwords: PasswordHasherPort, codes: CodeService,
                 sessions_repo: SessionRepositoryPort):
        self._users, self._passwords, self._codes, self._sessions = users, passwords, codes, sessions_repo

    def execute(self, email: str, code: str, new_password: str) -> None:
        email = normalize_email(email)
        validate_password(new_password, email)
        user = self._users.get_by_email(email)
        if user is None:
            raise InvalidCode()
        self._codes.check(user, PURPOSE_RESET, code)
        self._users.set_password(user.id, self._passwords.hash(new_password))
        self._users.clear_failed_logins(user.id)
        self._sessions.revoke_all(user.id)
