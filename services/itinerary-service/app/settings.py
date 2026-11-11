
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    airport_service_url: str = "http://airport-service:8000"
    airport_http_timeout_seconds: float = 2.0
    jwt_secret: str
    # Margen minimo entre aterrizar y volver a salir (0 = pueden ser consecutivos).
    min_connection_minutes: int = 0

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
