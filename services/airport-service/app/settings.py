from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://redis-airport:6379/0"
    database_url: str = "postgresql://airport:airport@postgres-airport:5432/airport"

    class Config:
        env_file = ".env"


settings = Settings()
