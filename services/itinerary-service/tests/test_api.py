import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"  # antes de importar la app

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.infrastructure.adapters.http_airport_gateway import HttpAirportGateway  # noqa: E402
from app.infrastructure.adapters.sqlalchemy_repository import Base  # noqa: E402
from app.infrastructure.api import dependencies  # noqa: E402
from app.main import app  # noqa: E402

KNOWN = {"3", "9", "2"}


def _airport_handler(request: httpx.Request) -> httpx.Response:
    airport_id = request.url.path.rsplit("/", 1)[-1]
    return httpx.Response(200 if airport_id in KNOWN else 404, json={})


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False)

    def get_db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    gateway = HttpAirportGateway("http://airports.test", client=httpx.Client(transport=httpx.MockTransport(_airport_handler)))
    app.dependency_overrides[dependencies.get_db] = get_db
    app.dependency_overrides[dependencies.get_airport_gateway] = lambda: gateway
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


ANA = {"X-User-Name": "ana"}
LUIS = {"X-User-Name": "luis"}
BODY = {"username": "ana", "departure_airport_id": "3", "arrival_airport_id": "9",
        "travel_date": "2026-12-01", "duration_minutes": 75}


def test_full_crud(client):
    created = client.post("/itineraries", json=BODY, headers=ANA)
    assert created.status_code == 201
    iid = created.json()["id"]

    assert client.get(f"/itineraries/{iid}", headers=ANA).json()["duration_minutes"] == 75
    assert len(client.get("/itineraries", headers=ANA).json()) == 1

    upd = client.patch(f"/itineraries/{iid}", json={"arrival_airport_id": "2", "duration_minutes": 90}, headers=ANA)
    assert upd.status_code == 200 and upd.json()["arrival_airport_id"] == "2"

    assert client.delete(f"/itineraries/{iid}", headers=ANA).status_code == 204
    assert client.get(f"/itineraries/{iid}", headers=ANA).status_code == 404


def test_same_airport_is_422(client):
    r = client.post("/itineraries", json={**BODY, "arrival_airport_id": "3"}, headers=ANA)
    assert r.status_code == 422


def test_unknown_airport_is_422(client):
    r = client.post("/itineraries", json={**BODY, "arrival_airport_id": "999"}, headers=ANA)
    assert r.status_code == 422


def test_requires_identity(client):
    assert client.get("/itineraries").status_code == 401


def test_cannot_create_for_other_user(client):
    assert client.post("/itineraries", json=BODY, headers=LUIS).status_code == 403


def test_idor_is_404(client):
    iid = client.post("/itineraries", json=BODY, headers=ANA).json()["id"]
    assert client.get(f"/itineraries/{iid}", headers=LUIS).status_code == 404
    assert client.patch(f"/itineraries/{iid}", json={"duration_minutes": 1}, headers=LUIS).status_code == 404
    assert client.delete(f"/itineraries/{iid}", headers=LUIS).status_code == 404
    assert client.get("/itineraries", headers=LUIS).json() == []


def test_mass_assignment_blocked(client):
    iid = client.post("/itineraries", json=BODY, headers=ANA).json()["id"]
    r = client.patch(f"/itineraries/{iid}", json={"username": "luis"}, headers=ANA)
    assert r.status_code == 422
    assert client.get(f"/itineraries/{iid}", headers=ANA).json()["username"] == "ana"


def test_empty_patch_is_422(client):
    iid = client.post("/itineraries", json=BODY, headers=ANA).json()["id"]
    assert client.patch(f"/itineraries/{iid}", json={}, headers=ANA).status_code == 422


def test_airport_service_down_is_503_without_details(client):
    def boom(request):
        raise httpx.ConnectError("secret-host:1234")

    gateway = HttpAirportGateway("http://x", client=httpx.Client(transport=httpx.MockTransport(boom)))
    app.dependency_overrides[dependencies.get_airport_gateway] = lambda: gateway
    r = client.post("/itineraries", json=BODY, headers=ANA)
    assert r.status_code == 503 and "secret-host" not in r.text
