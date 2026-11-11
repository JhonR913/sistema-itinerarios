"""Pruebas de la capa HTTP con FastAPI TestClient y dependencias
sustituidas por dobles: sin red, sin PostgreSQL."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
import jwt

from app.domain.models import AirportSnapshot
from app.infrastructure.adapters.airport_http_adapter import AirportServiceUnavailableError
from app.infrastructure.api.dependencies import get_airport_gateway, get_itinerary_repository
from app.main import app
from app.settings import settings
from tests.unit.test_use_cases import BOG, MDE, DEP, at, FakeAirportGateway, FakeRepository


class DownGateway(FakeAirportGateway):
    def get_airport_snapshot(self, airport_id):
        raise AirportServiceUnavailableError("circuito abierto")


def _token(sub="owner-1", secret=None, exp_delta=timedelta(minutes=5), with_exp=True, email=None):
    payload = {"sub": sub}
    if email:
        payload["email"] = email
    if with_exp:
        payload["exp"] = datetime.now(timezone.utc) + exp_delta
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm="HS256")


def _auth(**kw):
    return {"Authorization": f"Bearer {_token(**kw)}"}


BODY = {"nombre_usuario": "jhon", "origin_airport_id": "1",
        "destination_airport_id": "2", "departure_at": DEP.isoformat(), "duration_minutes": 90}


@pytest.fixture
def repo():
    return FakeRepository()


@pytest.fixture
def client(repo):
    app.dependency_overrides[get_airport_gateway] = lambda: FakeAirportGateway([BOG, MDE])
    app.dependency_overrides[get_itinerary_repository] = lambda: repo
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def test_requires_bearer_token(client):
    assert client.get("/api/itineraries").status_code in (401, 403)


def test_rejects_token_signed_with_wrong_secret(client):
    r = client.get("/api/itineraries", headers=_auth(secret="otro-secreto-distinto-xxxxxxxxxxxx"))
    assert r.status_code == 401


def test_rejects_expired_token(client):
    r = client.get("/api/itineraries", headers=_auth(exp_delta=timedelta(minutes=-5)))
    assert r.status_code == 401


def test_rejects_token_without_exp(client):
    assert client.get("/api/itineraries", headers=_auth(with_exp=False)).status_code == 401


def test_create_returns_201_and_persists_event(client, repo):
    r = client.post("/api/itineraries", json=BODY, headers=_auth())
    assert r.status_code == 201
    assert len(repo.saved) == 1 and len(repo.events) == 1
    assert r.json()["id"] == repo.saved[0].id


def test_create_unknown_airport_is_422_and_nothing_persisted(client, repo):
    r = client.post("/api/itineraries", json={**BODY, "destination_airport_id": "999"}, headers=_auth())
    assert r.status_code == 422
    assert repo.saved == [] and repo.events == []


def test_create_same_origin_and_destination_is_422(client):
    r = client.post("/api/itineraries", json={**BODY, "destination_airport_id": "1"}, headers=_auth())
    assert r.status_code == 422


def test_create_invalid_body_is_422(client):
    r = client.post("/api/itineraries", json={**BODY, "duration_minutes": 0}, headers=_auth())
    assert r.status_code == 422


def test_create_returns_502_when_airport_service_down(repo):
    app.dependency_overrides[get_airport_gateway] = lambda: DownGateway([])
    app.dependency_overrides[get_itinerary_repository] = lambda: repo
    try:
        r = TestClient(app).post("/api/itineraries", json=BODY, headers=_auth())
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 502
    assert repo.saved == []


def test_get_other_users_itinerary_is_404_anti_idor(client):
    created = client.post("/api/itineraries", json=BODY, headers=_auth(sub="owner-1")).json()
    assert client.get(f"/api/itineraries/{created['id']}", headers=_auth(sub="owner-1")).status_code == 200
    assert client.get(f"/api/itineraries/{created['id']}", headers=_auth(sub="attacker")).status_code == 404


def test_non_uuid_id_is_404_not_500(client):
    for method in ("get", "delete"):
        r = getattr(client, method)("/api/itineraries/not-a-uuid", headers=_auth())
        assert r.status_code == 404
    r = client.put("/api/itineraries/not-a-uuid", json={"duration_minutes": 10}, headers=_auth())
    assert r.status_code == 404


def test_update_and_delete_flow(client):
    created = client.post("/api/itineraries", json=BODY, headers=_auth()).json()
    url = f"/api/itineraries/{created['id']}"
    r = client.put(url, json={"duration_minutes": 120, "user_id": "hacker"}, headers=_auth())
    assert r.status_code == 200 and r.json()["duration_minutes"] == 120
    assert client.delete(url, headers=_auth(sub="attacker")).status_code == 404
    assert client.delete(url, headers=_auth()).status_code == 204
    assert client.get(url, headers=_auth()).status_code == 404


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_email_claim_from_jwt_reaches_the_created_event(client, repo):
    client.post("/api/itineraries", json=BODY, headers=_auth(email="jhon@example.com"))
    assert repo.events[0].payload["email"] == "jhon@example.com"


def test_update_and_delete_through_api_register_events(client, repo):
    created = client.post("/api/itineraries", json=BODY, headers=_auth()).json()
    url = f"/api/itineraries/{created['id']}"
    client.put(url, json={"departure_at": at(45, 8).isoformat()}, headers=_auth())
    client.delete(url, headers=_auth())
    assert [e.event_type for e in repo.events] == [
        "ItineraryCreatedEvent", "ItineraryUpdatedEvent", "ItineraryDeletedEvent"]


def test_database_down_is_503_with_retry_after_not_500(repo):
    from sqlalchemy.exc import OperationalError

    class DbDownRepo(FakeRepository):
        def list_by_user(self, user_id):
            raise OperationalError("SELECT", {}, Exception("connection refused"))

    app.dependency_overrides[get_itinerary_repository] = lambda: DbDownRepo()
    try:
        r = TestClient(app, raise_server_exceptions=False).get("/api/itineraries", headers=_auth())
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 503 and r.headers["retry-after"] == "5"
    assert "connection refused" not in r.text
