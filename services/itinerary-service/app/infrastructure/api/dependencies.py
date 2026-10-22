from functools import lru_cache

from app.domain.ports import AirportGatewayPort, ItineraryRepositoryPort, EventPublisherPort
from app.infrastructure.adapters.airport_http_adapter import AirportHttpAdapter
from app.infrastructure.adapters.postgres_repository import PostgresItineraryRepository
from app.infrastructure.adapters.outbox_publisher import OutboxEventPublisher
from app.settings import settings


@lru_cache
def get_airport_gateway() -> AirportGatewayPort:
    return AirportHttpAdapter(settings.airport_service_url)


@lru_cache
def get_itinerary_repository() -> ItineraryRepositoryPort:
    return PostgresItineraryRepository(settings.database_url)


@lru_cache
def get_event_publisher() -> EventPublisherPort:
    return OutboxEventPublisher(settings.database_url)
