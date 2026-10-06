import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"  # antes de importar la app

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.infrastructure.adapters.http_airport_gateway import HttpAirportGateway  # noqa: E402
from app.infrastructure.adapters.sqlalchemy_repository import Base, OutboxModel  # noqa: E402
from app.infrastructure.api import dependencies  # noqa: E402
from app.main import app  # noqa: E402

KNOWN = {"3", "9", "2"}


def _airport_handler(request: httpx.Request) -> httpx.Response:
    airport_id = request.url.path.rsplit("/", 1)[-1]
    if airport_id not in KNOWN:
        return httpx.Response(404, json={})
    return httpx.Response(200, json={"id": airport_id, "iata_code": f"A{airport_id}",
                                     "name": f"Aeropuerto {airport_id}", "city": f"Ciudad {airport_id}"})


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
    test_client = TestClient(app, raise_server_exceptions=False)
    test_client.session_factory = Session  # para inspeccionar la tabla outbox en las pruebas
    yield test_client
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


def _outbox_rows(client):
    with client.session_factory() as db:
        return db.query(OutboxModel).all()


def test_create_returns_snapshots_and_writes_pending_outbox_event(client):
    r = client.post("/itineraries", json=BODY, headers=ANA)
    assert r.status_code == 201
    body = r.json()
    assert body["departure_snapshot"] == {"iata_code": "A3", "name": "Aeropuerto 3", "city": "Ciudad 3"}
    assert body["arrival_snapshot"]["iata_code"] == "A9"

    rows = _outbox_rows(client)
    assert len(rows) == 1
    assert rows[0].status == "PENDING" and rows[0].event_type == "ItineraryCreatedEvent"
    assert rows[0].aggregate_id == body["id"]
    assert rows[0].payload["nombre_usuario"] == "ana" and rows[0].payload["origen"]["iata_code"] == "A3"


def test_failed_create_leaves_no_outbox_row(client):
    assert client.post("/itineraries", json={**BODY, "arrival_airport_id": "999"}, headers=ANA).status_code == 422
    assert client.post("/itineraries", json={**BODY, "arrival_airport_id": "3"}, headers=ANA).status_code == 422
    assert _outbox_rows(client) == []


def test_update_and_delete_do_not_add_outbox_events(client):
    iid = client.post("/itineraries", json=BODY, headers=ANA).json()["id"]
    client.patch(f"/itineraries/{iid}", json={"duration_minutes": 90}, headers=ANA)
    client.delete(f"/itineraries/{iid}", headers=ANA)
    assert len(_outbox_rows(client)) == 1


def test_update_refreshes_snapshot_in_response(client):
    iid = client.post("/itineraries", json=BODY, headers=ANA).json()["id"]
    r = client.patch(f"/itineraries/{iid}", json={"arrival_airport_id": "2"}, headers=ANA)
    assert r.json()["arrival_snapshot"]["iata_code"] == "A2"
    assert client.get(f"/itineraries/{iid}", headers=ANA).json()["arrival_snapshot"]["iata_code"] == "A2"
