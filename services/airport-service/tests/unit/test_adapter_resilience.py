"""Prueba del Adapter con sus 3 niveles de resiliencia, usando dobles de
prueba para cache y store durable (sin Redis ni Postgres reales)."""
import pybreaker
import pytest

from app.domain.models import Airport
from app.infrastructure.adapters.api_colombia_adapter import ApiColombiaAdapter, airport_breaker
from app.infrastructure.adapters.redis_cache import InMemoryAirportCache


class FakeDurableStore:
    def __init__(self, seed=None):
        self._airports = seed or []

    def upsert_many(self, airports):
        self._airports = airports

    def get_all(self):
        return self._airports

    def get_by_id(self, airport_id):
        return next((a for a in self._airports if a.id == airport_id), None)


@pytest.fixture(autouse=True)
def reset_breaker():
    airport_breaker.close()
    yield
    airport_breaker.close()


def test_falls_back_to_durable_store_when_circuit_open_and_cache_empty():
    """Nivel 3: si Redis no tiene nada (ni fresco ni stale) y el circuito
    esta abierto, el Adapter sirve desde PostgreSQL en vez de fallar."""
    seeded = [Airport(id="1", external_id="101", iata_code="BOG", name="El Dorado",
                        city="Bogotá", latitude=4.7, longitude=-74.1)]
    cache = InMemoryAirportCache()
    durable_store = FakeDurableStore(seed=seeded)
    adapter = ApiColombiaAdapter(cache=cache, durable_store=durable_store)

    airport_breaker.open()  # forzar circuito abierto, sin llamar a la red real

    result = adapter.get_all()
    assert result == seeded


def test_raises_when_circuit_open_and_nothing_cached_or_stored():
    """Si ni Redis ni Postgres tienen nada, el fallo SI se propaga
    (no se inventa una respuesta vacia silenciosa)."""
    cache = InMemoryAirportCache()
    durable_store = FakeDurableStore(seed=[])
    adapter = ApiColombiaAdapter(cache=cache, durable_store=durable_store)

    airport_breaker.open()

    with pytest.raises(pybreaker.CircuitBreakerError):
        adapter.get_all()
