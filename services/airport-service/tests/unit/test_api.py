"""Capa HTTP de Airport Service con un repositorio fake."""
import httpx
import pybreaker
import pytest
from fastapi.testclient import TestClient

from app.domain.models import Airport
from app.domain.ports import AirportRepositoryPort
from app.infrastructure.api.dependencies import get_airport_repository
from app.main import app

BOG = Airport(id="1", external_id="1", iata_code="BOG", name="El Dorado",
              city="Bogotá", latitude=4.7, longitude=-74.1)


class Repo(AirportRepositoryPort):
    def get_all(self):
        return [BOG]

    def get_by_id(self, airport_id):
        return BOG if airport_id == "1" else None


class BrokenRepo(AirportRepositoryPort):
    def __init__(self, exc):
        self._exc = exc

    def get_all(self):
        raise self._exc

    def get_by_id(self, airport_id):
        raise self._exc


@pytest.fixture(autouse=True)
def _clean():
    yield
    app.dependency_overrides.clear()


def _client(repo):
    app.dependency_overrides[get_airport_repository] = lambda: repo
    return TestClient(app, raise_server_exceptions=False)


def test_list_and_detail():
    client = _client(Repo())
    assert client.get("/api/airports").json()[0]["iata_code"] == "BOG"
    assert client.get("/api/airports/1").json()["id"] == "1"
    assert client.get("/api/airports/zzz").status_code == 404


@pytest.mark.parametrize("exc", [pybreaker.CircuitBreakerError("open"), httpx.ConnectError("x")])
def test_upstream_unavailable_is_503_not_500(exc):
    r = _client(BrokenRepo(exc)).get("/api/airports")
    assert r.status_code == 503
    assert "Traceback" not in r.text


def test_unexpected_error_is_500_without_leaking_details():
    r = _client(BrokenRepo(RuntimeError("secreto interno"))).get("/api/airports")
    assert r.status_code == 500
    assert "secreto interno" not in r.text
