from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # RNF-SEC-001: mismo secreto que validan los demas servicios, nunca
    # hardcodeado; debe coincidir con JWT_SECRET de itinerary-service.
    jwt_secret: str = "CHANGE_ME_IN_ENV"

    class Config:
        env_file = ".env"


settings = Settings()
