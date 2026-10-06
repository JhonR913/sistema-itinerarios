"""Composition root de la capa API: aqui, y solo aqui, se decide que
implementacion concreta de cada puerto se usa. routes.py no debe construir
adaptadores el mismo; los recibe inyectados via Depends()."""
from functools import lru_cache

from app.domain.ports import AirportRepositoryPort, AirportCachePort
from app.infrastructure.adapters.redis_cache import RedisAirportCache
from app.infrastructure.adapters.api_colombia_adapter import ApiColombiaAdapter
from app.settings import settings


@lru_cache
def get_airport_cache() -> AirportCachePort:
    return RedisAirportCache(settings.redis_url)


@lru_cache
def get_airport_repository() -> AirportRepositoryPort:
    return ApiColombiaAdapter(cache=get_airport_cache())
