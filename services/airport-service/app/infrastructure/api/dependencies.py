from functools import lru_cache

from app.domain.ports import AirportRepositoryPort, AirportCachePort, AirportDurableStorePort
from app.infrastructure.adapters.redis_cache import RedisAirportCache
from app.infrastructure.adapters.postgres_airport_store import PostgresAirportStore
from app.infrastructure.adapters.api_colombia_adapter import ApiColombiaAdapter
from app.settings import settings


@lru_cache
def get_airport_cache() -> AirportCachePort:
    return RedisAirportCache(settings.redis_url)


@lru_cache
def get_airport_durable_store() -> AirportDurableStorePort:
    return PostgresAirportStore(settings.database_url)


@lru_cache
def get_airport_repository() -> AirportRepositoryPort:
    return ApiColombiaAdapter(cache=get_airport_cache(), durable_store=get_airport_durable_store())
