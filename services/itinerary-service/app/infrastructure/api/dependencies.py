import re
from collections.abc import Iterator
from functools import lru_cache

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.application.use_cases import ItineraryService
from app.domain.ports import AirportGateway
from app.infrastructure import config
from app.infrastructure.adapters.http_airport_gateway import HttpAirportGateway
from app.infrastructure.adapters.sqlalchemy_repository import SqlAlchemyItineraryRepository
from app.infrastructure.api.schemas import USERNAME_PATTERN
from app.infrastructure.db import SessionLocal


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@lru_cache
def get_airport_gateway() -> AirportGateway:
    return HttpAirportGateway(config.AIRPORT_SERVICE_URL, config.AIRPORT_SERVICE_TIMEOUT)


def get_service(
    db: Session = Depends(get_db),
    airports: AirportGateway = Depends(get_airport_gateway),
) -> ItineraryService:
    return ItineraryService(SqlAlchemyItineraryRepository(db), airports)


def current_username(x_user_name: str | None = Header(default=None)) -> str:
    """Identidad del solicitante.

    PLACEHOLDER: en producción debe salir de un token verificado (JWT/API gateway),
    nunca de un header que el cliente pueda falsificar.
    """
    if not x_user_name or not re.fullmatch(USERNAME_PATTERN, x_user_name):
        raise HTTPException(status_code=401, detail="No autenticado")
    return x_user_name
