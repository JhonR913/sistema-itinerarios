"""Composicion: arma los casos de uso con sus adaptadores concretos."""
from dataclasses import dataclass
from functools import lru_cache

from app.application.use_cases import (
    CodeService, ForgotPassword, IdentityPolicy, Login, Logout, RefreshSession,
    Register, ResendCode, ResetPassword, SessionService, VerifyEmail,
)
from app.infrastructure.adapters.crypto import HmacCodeHasher, ScryptPasswordHasher
from app.infrastructure.adapters.jwt_issuer import JwtTokenIssuer
from app.infrastructure.adapters.postgres_repository import (
    PostgresCodeRepository, PostgresSessionRepository, PostgresUserRepository, make_engine,
)
from app.infrastructure.adapters.smtp_sender import SmtpEmailSender
from app.settings import settings


@dataclass
class Container:
    register: Register
    verify: VerifyEmail
    resend: ResendCode
    login: Login
    refresh: RefreshSession
    logout: Logout
    forgot: ForgotPassword
    reset: ResetPassword
    session_days: int
    cookie_secure: bool


def build_container(users, codes, sessions_repo, sender, passwords, code_hasher, tokens,
                    policy: IdentityPolicy, cookie_secure: bool = False, clock=None) -> Container:
    """Constructor sin I/O propio: las pruebas lo alimentan con repositorios en memoria."""
    extra = {"clock": clock} if clock else {}
    code_service = CodeService(codes, code_hasher, sender, policy, **extra)
    session_service = SessionService(sessions_repo, tokens, policy, **extra)
    return Container(
        register=Register(users, passwords, code_service, sender),
        verify=VerifyEmail(users, code_service, session_service, **extra),
        resend=ResendCode(users, code_service),
        login=Login(users, passwords, code_service, session_service, policy, **extra),
        refresh=RefreshSession(users, sessions_repo, session_service, **extra),
        logout=Logout(sessions_repo),
        forgot=ForgotPassword(users, code_service),
        reset=ResetPassword(users, passwords, code_service, sessions_repo),
        session_days=policy.session_days,
        cookie_secure=cookie_secure,
    )


@lru_cache
def get_container() -> Container:
    engine = make_engine(settings.database_url)
    policy = IdentityPolicy(
        code_ttl_minutes=settings.code_ttl_minutes, max_code_attempts=settings.max_code_attempts,
        resend_cooldown_seconds=settings.resend_cooldown_seconds, max_codes_per_hour=settings.max_codes_per_hour,
        max_codes_per_hour_global=settings.max_codes_per_hour_global, max_failed_logins=settings.max_failed_logins,
        lock_minutes=settings.lock_minutes, session_days=settings.session_days,
        access_ttl_minutes=settings.access_ttl_minutes)
    sender = SmtpEmailSender(settings.smtp_host, settings.smtp_port, settings.smtp_from,
                             settings.smtp_starttls, settings.smtp_user, settings.smtp_password)
    return build_container(
        PostgresUserRepository(engine), PostgresCodeRepository(engine), PostgresSessionRepository(engine),
        sender, ScryptPasswordHasher(), HmacCodeHasher(settings.jwt_secret),
        JwtTokenIssuer(settings.jwt_secret, settings.access_ttl_minutes), policy, settings.cookie_secure)
