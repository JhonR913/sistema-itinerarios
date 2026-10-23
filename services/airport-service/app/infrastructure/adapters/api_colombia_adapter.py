"""
Adapter (patron Adapter formal, Documento_Arquitectura.docx seccion 4):
traduce el modelo externo de API Colombia al modelo de dominio interno
Airport, e implementa AirportRepositoryPort. Resiliencia en 3 niveles:
  1. Redis (fresco)       -> respuesta inmediata.
  2. API Colombia (vivo)  -> via Circuit Breaker + Retry/Backoff.
  3. Redis (stale) o PostgreSQL (durable) -> si el circuito esta abierto.
"""
from typing import List, Optional

import httpx
import pybreaker
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from app.domain.models import Airport
from app.domain.ports import AirportRepositoryPort, AirportCachePort, AirportDurableStorePort

API_COLOMBIA_BASE_URL = "https://api-colombia.com/api/v1"
CACHE_TTL_SECONDS = 300

airport_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)


def _map_external_to_domain(raw: dict) -> Airport:
    city = raw.get("city") or {}
    return Airport(
        id=str(raw["id"]),
        external_id=str(raw["id"]),
        iata_code=raw.get("iataCode", "N/A"),
        name=raw.get("name", "Desconocido"),
        city=city.get("name", "Desconocida"),
        latitude=float(raw.get("latitude") or 0.0),
        longitude=float(raw.get("longitude") or 0.0),
    )


class ApiColombiaAdapter(AirportRepositoryPort):
    def __init__(self, cache: AirportCachePort, durable_store: AirportDurableStorePort,
                 http_client: Optional[httpx.Client] = None):
        self._cache = cache
        self._durable_store = durable_store
        self._client = http_client or httpx.Client(timeout=3.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=4))
    def _fetch(self, path: str):
        response = self._client.get(f"{API_COLOMBIA_BASE_URL}{path}")
        response.raise_for_status()
        return response.json()

    def get_all(self) -> List[Airport]:
        cache_key = "airports:all"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            raw_list = airport_breaker.call(self._fetch, "/Airport")
        except pybreaker.CircuitBreakerError:
            # Nivel 2 de fallback: Redis stale.
            stale = self._cache.get(cache_key + ":stale")
            if stale is not None:
                return stale
            # Nivel 3 de fallback: PostgreSQL durable. Solo aqui, cuando
            # ya no queda nada en Redis, se consulta la base de datos.
            durable = self._durable_store.get_all()
            if durable:
                return durable
            raise

        airports = [_map_external_to_domain(item) for item in raw_list]
        self._durable_store.upsert_many(airports)
        self._cache.set(cache_key, airports, CACHE_TTL_SECONDS)
        self._cache.set(cache_key + ":stale", airports, CACHE_TTL_SECONDS * 20)
        return airports

    def get_by_id(self, airport_id: str) -> Optional[Airport]:
        for airport in self.get_all():
            if airport.id == airport_id:
                return airport
        return None
