from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://itinerary:itinerary@postgres-itinerary:5432/itinerary"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    airport_service_url: str = "http://airport-service:8000"
    jwt_secret: str = "CHANGE_ME_IN_ENV"

    class Config:
        env_file = ".env"


settings = Settings()
