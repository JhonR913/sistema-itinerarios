"""Regla de agenda: el viajero no puede estar en dos lugares a la vez.
Escenario base (el del enunciado): Bogota -> Valledupar, sale 6:00 y llega 8:00."""
from datetime import datetime, timezone

import pytest

from app.application.use_cases import CreateItinerary, UpdateItinerary, DeleteItinerary
from app.domain.models import InvalidItineraryError
from app.domain.scheduling import ScheduleConflictError
from tests.unit.test_use_cases import (
    BOG, MDE, VUP, TUN, FakeAirportGateway, FakeRepository, at,
)

GATEWAY = FakeAirportGateway([BOG, MDE, VUP, TUN])


def _fly(repo, origin, destination, departure, minutes=120, user="u1", min_conn=0):
    return CreateItinerary(GATEWAY, repo, min_conn).execute(
        nombre_usuario="jhon", origin_id=origin, destination_id=destination,
        departure_at=departure, duration_minutes=minutes, user_id=user)


@pytest.fixture
def repo():
    r = FakeRepository()
    _fly(r, "1", "4", at(30, 6))          # BOG -> VUP, 6:00 - 8:00
    return r


def test_overlapping_flight_from_other_city_is_rejected(repo):
    with pytest.raises(ScheduleConflictError) as e:          # Tunja a las 7: estas en el aire
        _fly(repo, "5", "1", at(30, 7))
    assert e.value.code == "OVERLAP"
    assert len(repo.saved) == 1 and len(repo.events) == 1    # no se guardo nada


def test_overlap_even_from_same_origin(repo):
    with pytest.raises(ScheduleConflictError) as e:
        _fly(repo, "1", "2", at(30, 7))
    assert e.value.code == "OVERLAP"


def test_after_landing_must_depart_from_arrival_city(repo):
    with pytest.raises(ScheduleConflictError) as e:          # 9:00 desde Tunja: no estas alli
        _fly(repo, "5", "1", at(30, 9))
    assert e.value.code == "ORIGIN_MISMATCH"
    assert "Valledupar" in str(e.value)


def test_can_depart_from_arrival_city_exactly_at_arrival_time(repo):
    _fly(repo, "4", "1", at(30, 8))                          # VUP 8:00 -> permitido
    assert len(repo.saved) == 2


def test_can_depart_from_arrival_city_on_a_later_day(repo):
    _fly(repo, "4", "2", at(33, 15))
    assert len(repo.saved) == 2


def test_before_first_flight_must_end_where_next_one_starts(repo):
    with pytest.raises(ScheduleConflictError) as e:          # termina en MDE pero el siguiente sale de BOG
        _fly(repo, "5", "2", at(29, 10))
    assert e.value.code == "NEXT_MISMATCH"
    _fly(repo, "5", "1", at(29, 10))                         # Tunja -> Bogota si encadena
    assert len(repo.saved) == 2


def test_min_connection_margin_is_enforced():
    r = FakeRepository()
    _fly(r, "1", "4", at(30, 6), min_conn=60)
    with pytest.raises(ScheduleConflictError) as e:
        _fly(r, "4", "1", at(30, 8), min_conn=60)             # 8:00 sin margen de 60 min
    assert e.value.code == "OVERLAP"
    _fly(r, "4", "1", at(30, 9), min_conn=60)


def test_other_users_do_not_interfere(repo):
    _fly(repo, "5", "1", at(30, 7), user="u2")
    assert len(repo.saved) == 2


def test_past_departure_is_rejected():
    with pytest.raises(InvalidItineraryError):
        _fly(FakeRepository(), "1", "2", at(-1, 6))


def test_naive_datetime_is_rejected():
    with pytest.raises(InvalidItineraryError):
        _fly(FakeRepository(), "1", "2", datetime(2099, 1, 1, 6, 0))


def test_departure_is_normalized_to_utc_and_arrival_computed(repo):
    it = repo.saved[0]
    assert it.departure_at.tzinfo == timezone.utc
    assert (it.arrival_at - it.departure_at).total_seconds() == 120 * 60


def test_update_cannot_move_flight_into_conflict(repo):
    _fly(repo, "4", "1", at(30, 9))                          # VUP -> BOG 9:00
    second = repo.saved[1]
    with pytest.raises(ScheduleConflictError) as e:
        UpdateItinerary(GATEWAY, repo).execute(second.id, "u1", departure_at=at(30, 7))
    assert e.value.code == "OVERLAP"


def test_update_does_not_conflict_with_itself(repo):
    first = repo.saved[0]
    UpdateItinerary(GATEWAY, repo).execute(first.id, "u1", duration_minutes=100)
    UpdateItinerary(GATEWAY, repo).execute(first.id, "u1", departure_at=at(30, 5))


def test_update_changing_destination_breaks_next_connection(repo):
    _fly(repo, "4", "1", at(31, 9))                          # VUP -> BOG el dia siguiente
    with pytest.raises(ScheduleConflictError) as e:
        UpdateItinerary(GATEWAY, repo).execute(repo.saved[0].id, "u1", destination_id="2")
    assert e.value.code == "NEXT_MISMATCH"


def test_api_returns_409_with_code_and_conflicting_id():
    from fastapi.testclient import TestClient
    from app.infrastructure.api.dependencies import get_airport_gateway, get_itinerary_repository
    from app.main import app
    from tests.unit.test_api import _auth
    repo = FakeRepository()
    app.dependency_overrides[get_airport_gateway] = lambda: GATEWAY
    app.dependency_overrides[get_itinerary_repository] = lambda: repo
    try:
        c = TestClient(app)
        body = {"nombre_usuario": "jhon", "origin_airport_id": "1", "destination_airport_id": "4",
                "departure_at": at(30, 6).isoformat(), "duration_minutes": 120}
        first = c.post("/api/itineraries", json=body, headers=_auth())
        assert first.status_code == 201
        clash = c.post("/api/itineraries", headers=_auth(), json={
            **body, "origin_airport_id": "5", "destination_airport_id": "1",
            "departure_at": at(30, 7).isoformat()})
        assert clash.status_code == 409
        data = clash.json()
        assert data["code"] == "OVERLAP" and data["conflicting_itinerary_id"] == first.json()["id"]
        listed = c.get("/api/itineraries", headers=_auth()).json()
        assert listed[0]["arrival_at"] and listed[0]["departure_at"]
        assert c.post("/api/itineraries", headers=_auth(), json={
            **body, "departure_at": "2030-01-01T06:00:00"}).status_code == 422   # sin zona
    finally:
        app.dependency_overrides.clear()
