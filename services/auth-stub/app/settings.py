from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    jwt_secret: str

    # Correo (desarrollo: Mailpit sin TLS; produccion: p. ej. smtp.gmail.com:587 + STARTTLS).
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_from: str = "itinerarios@localhost"
    smtp_starttls: bool = False
    smtp_user: str = ""
    smtp_password: str = ""

    # La cookie de sesion solo viaja por HTTPS cuando esto es true (produccion tras Cloudflare).
    cookie_secure: bool = False
    session_days: int = 14
    access_ttl_minutes: int = 30

    code_ttl_minutes: int = 10
    max_code_attempts: int = 5
    resend_cooldown_seconds: int = 60
    max_codes_per_hour: int = 5
    # Tope global de correos de codigo por hora: protege la cuota del SMTP y a terceros.
    max_codes_per_hour_global: int = 100
    max_failed_logins: int = 5
    lock_minutes: int = 15

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_long_enough(cls, value: str) -> str:
        # HS256 exige >= 32 bytes (RFC 7518 3.2); un secreto corto es forzable.
        if len(value) < 32:
            raise ValueError("JWT_SECRET debe tener al menos 32 caracteres")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
