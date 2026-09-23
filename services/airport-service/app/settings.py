"""RNF-SEC-001: nunca hardcodear secretos. Todo viene de variables de
entorno. Ver .env.example para las claves esperadas."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://redis-airport:6379/0"

    class Config:
        env_file = ".env"


settings = Settings()
