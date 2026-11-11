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


# --- Fallos transitorios (circuito AUN cerrado) -----------------------------
import httpx  # noqa: E402

from app.infrastructure.adapters.api_colombia_adapter import _map_external_to_domain  # noqa: E402


class FailingClient:
    def get(self, url):
        raise httpx.ConnectError("sin red")


def _no_wait(monkeypatch):
    monkeypatch.setattr(ApiColombiaAdapter._fetch.retry, "wait", lambda *_a, **_k: 0)


def test_first_upstream_failure_already_falls_back_to_durable_store(monkeypatch):
    """Antes solo se usaba el respaldo con el circuito abierto; las primeras
    fallas devolvian error aunque hubiera datos en PostgreSQL."""
    _no_wait(monkeypatch)
    seeded = [Airport(id="1", external_id="1", iata_code="BOG", name="El Dorado",
                      city="Bogotá", latitude=4.7, longitude=-74.1)]
    adapter = ApiColombiaAdapter(cache=InMemoryAirportCache(), durable_store=FakeDurableStore(seeded),
                                 http_client=FailingClient())
    assert adapter.get_all() == seeded
    assert airport_breaker.current_state == "closed"  # solo 1 falla registrada


def test_upstream_failure_with_no_fallback_propagates_error(monkeypatch):
    _no_wait(monkeypatch)
    adapter = ApiColombiaAdapter(cache=InMemoryAirportCache(), durable_store=FakeDurableStore([]),
                                 http_client=FailingClient())
    with pytest.raises(Exception):
        adapter.get_all()


class OkClient:
    def __init__(self, payload):
        self._payload = payload

    def get(self, url):
        self.url = url
        return httpx.Response(200, json=self._payload, request=httpx.Request("GET", url))


def test_success_populates_cache_and_durable_store_and_uses_configured_base_url():
    raw = [{"id": 1, "iataCode": "BOG", "name": "El Dorado", "city": {"name": "Bogotá"},
            "latitude": 4.7, "longitude": -74.1}]
    client = OkClient(raw)
    cache, store = InMemoryAirportCache(), FakeDurableStore([])
    adapter = ApiColombiaAdapter(cache=cache, durable_store=store, http_client=client,
                                 base_url="http://mock-upstream/api/v1/")
    result = adapter.get_all()
    assert client.url == "http://mock-upstream/api/v1/Airport"
    assert result[0].iata_code == "BOG"
    assert store.get_all() == result
    assert cache.get("airports:all") == result
    assert adapter.get_by_id("1").name == "El Dorado"
    assert adapter.get_by_id("nope") is None


def test_null_fields_from_upstream_do_not_break_mapping():
    airport = _map_external_to_domain({"id": 5, "iataCode": None, "name": None, "city": None,
                                       "latitude": None, "longitude": None})
    assert airport.iata_code == "N/A" and airport.name == "Desconocido"


def test_malformed_record_is_skipped_not_fatal():
    raw = [{"id": 1, "iataCode": "BOG", "name": "A", "city": {"name": "B"}, "latitude": 1, "longitude": 2},
           {"iataCode": "XXX"},  # sin id
           {"id": 3, "iataCode": "ABCDEFG", "name": "C"}]  # IATA invalido
    adapter = ApiColombiaAdapter(cache=InMemoryAirportCache(), durable_store=FakeDurableStore([]),
                                 http_client=OkClient(raw))
    assert [a.id for a in adapter.get_all()] == ["1"]


# --- PostgreSQL caido (Sprint 9) ----------------------------------------------
from sqlalchemy.exc import OperationalError  # noqa: E402


class BrokenStore(FakeDurableStore):
    def upsert_many(self, airports):
        raise OperationalError("INSERT", {}, Exception("db caida"))

    def get_all(self):
        raise OperationalError("SELECT", {}, Exception("db caida"))


def test_valid_upstream_response_is_served_even_if_postgres_is_down():
    raw = [{"id": 1, "iataCode": "BOG", "name": "A", "city": {"name": "B"}, "latitude": 1, "longitude": 2}]
    cache = InMemoryAirportCache()
    adapter = ApiColombiaAdapter(cache=cache, durable_store=BrokenStore(), http_client=OkClient(raw))
    assert [a.id for a in adapter.get_all()] == ["1"]
    assert cache.get("airports:all") is not None  # y se sigue cacheando


def test_upstream_down_and_postgres_down_propagates_the_original_error(monkeypatch):
    _no_wait(monkeypatch)
    adapter = ApiColombiaAdapter(cache=InMemoryAirportCache(), durable_store=BrokenStore(),
                                 http_client=FailingClient())
    with pytest.raises(Exception) as err:
        adapter.get_all()
    assert not isinstance(err.value, OperationalError)  # el error es del upstream (-> 503), no de la BD
