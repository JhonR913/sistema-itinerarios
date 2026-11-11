"""AirportHttpAdapter: timeout acotado, reintentos y circuit breaker."""
import httpx
import pybreaker
import pytest

from app.infrastructure.adapters import airport_http_adapter as mod
from app.infrastructure.adapters.airport_http_adapter import AirportHttpAdapter, AirportServiceUnavailableError


@pytest.fixture(autouse=True)
def _breaker(monkeypatch):
    mod.airport_breaker.close()
    monkeypatch.setattr(AirportHttpAdapter._fetch.retry, "wait", lambda *_a, **_k: 0)
    yield
    mod.airport_breaker.close()


class Client:
    def __init__(self, handler):
        self.calls = 0
        self._h = handler

    def get(self, url):
        self.calls += 1
        return self._h(url)


def _resp(code, body=None, url="http://x"):
    return httpx.Response(code, json=body, request=httpx.Request("GET", url))


def test_found_and_not_found():
    ok = {"id": "1", "iata_code": "BOG", "name": "El Dorado", "city": "Bogota"}
    adapter = AirportHttpAdapter("http://a", http_client=Client(lambda u: _resp(200, ok)))
    assert adapter.get_airport_snapshot("1").iata_code == "BOG"
    adapter = AirportHttpAdapter("http://a", http_client=Client(lambda u: _resp(404)))
    assert adapter.get_airport_snapshot("zzz") is None


def test_each_logical_call_makes_at_most_two_http_attempts_on_timeout():
    def boom(url):
        raise httpx.ReadTimeout("lento")
    client = Client(boom)
    adapter = AirportHttpAdapter("http://a", http_client=client)
    with pytest.raises(AirportServiceUnavailableError):  # ya en el PRIMER fallo (no 500)
        adapter.get_airport_snapshot("1")
    assert client.calls == 2


def test_breaker_opens_after_repeated_failures_then_fails_fast_without_http():
    def boom(url):
        raise httpx.ConnectError("caido")
    client = Client(boom)
    adapter = AirportHttpAdapter("http://a", http_client=client)
    for _ in range(3):
        with pytest.raises(AirportServiceUnavailableError):
            adapter.get_airport_snapshot("1")
    calls_before = client.calls
    with pytest.raises(AirportServiceUnavailableError):
        adapter.get_airport_snapshot("1")
    assert client.calls == calls_before  # circuito abierto: ni siquiera se intenta la red
