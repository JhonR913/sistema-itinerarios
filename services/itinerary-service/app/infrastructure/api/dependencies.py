from functools import lru_cache

from app.domain.ports import AirportGatewayPort, ItineraryRepositoryPort
from app.infrastructure.adapters.airport_http_adapter import AirportHttpAdapter
from app.infrastructure.adapters.postgres_repository import PostgresItineraryRepository
from app.settings import settings


@lru_cache
def get_airport_gateway() -> AirportGatewayPort:
    return AirportHttpAdapter(settings.airport_service_url, timeout=settings.airport_http_timeout_seconds)


@lru_cache
def get_itinerary_repository() -> ItineraryRepositoryPort:
    return PostgresItineraryRepository(settings.database_url)
