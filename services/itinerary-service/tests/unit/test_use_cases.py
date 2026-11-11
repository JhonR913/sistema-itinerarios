from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.domain.models import Itinerary, AirportSnapshot, InvalidItineraryError
from app.domain.ports import AirportGatewayPort, ItineraryRepositoryPort
from app.application.use_cases import (
    CreateItinerary, GetItinerary, UpdateItinerary, DeleteItinerary,
    AirportNotFoundError, ItineraryNotFoundError,
)

BOG = AirportSnapshot("1", "BOG", "El Dorado", "Bogotá")
MDE = AirportSnapshot("2", "MDE", "José María Córdova", "Medellín")
CTG = AirportSnapshot("3", "CTG", "Rafael Núñez", "Cartagena")
VUP = AirportSnapshot("4", "VUP", "Alfonso López", "Valledupar")
TUN = AirportSnapshot("5", "TUN", "Tunja Test", "Tunja")
BOGOTA = ZoneInfo("America/Bogota")


def at(days=30, hour=6, minute=0):
    """Instante local (Bogota) `days` dias en el futuro, siempre futuro."""
    base = datetime.now(BOGOTA).date() + timedelta(days=days)
    return datetime(base.year, base.month, base.day, hour, minute, tzinfo=BOGOTA)


DEP = at(30, 6)


class FakeAirportGateway(AirportGatewayPort):
    def __init__(self, known):
        self._known = {a.airport_id: a for a in known}

    def get_airport_snapshot(self, airport_id):
        return self._known.get(airport_id)


class FakeRepository(ItineraryRepositoryPort):
    """Doble en memoria. `events` representa la tabla outbox: se escribe
    junto con `saved`, como hace el repositorio real en una transaccion."""
    def __init__(self):
        self.saved = []
        self.events = []

    def save_with_event(self, itinerary, event, schedule_check=None):
        if schedule_check:
            schedule_check([i for i in self.saved if i.user_id == itinerary.user_id])
        self.saved.append(itinerary)
        self.events.append(event)

    def update_with_event(self, itinerary, event, schedule_check=None):
        if schedule_check:
            schedule_check([i for i in self.saved if i.user_id == itinerary.user_id])
        self.events.append(event)

    def get_by_id(self, itinerary_id, user_id):
        return next((i for i in self.saved if i.id == itinerary_id and i.user_id == user_id), None)

    def list_by_user(self, user_id):
        return [i for i in self.saved if i.user_id == user_id]

    def delete_with_event(self, itinerary_id, user_id, event):
        before = len(self.saved)
        self.saved = [i for i in self.saved if not (i.id == itinerary_id and i.user_id == user_id)]
        deleted = len(self.saved) < before
        if deleted:
            self.events.append(event)
        return deleted


def _create(repo, gateway=None, user_id="owner-1", origin="1", destination="2"):
    return CreateItinerary(gateway, repo).execute(
        nombre_usuario="jhon", origin_id=origin, destination_id=destination,
        departure_at=DEP, duration_minutes=90, user_id=user_id,
    )


def test_UT004_create_itinerary_happy_path_publishes_event():
    gateway = FakeAirportGateway([BOG, MDE])
    repo = FakeRepository()
    itinerary = _create(repo, gateway)
    assert len(repo.saved) == 1
    assert len(repo.events) == 1
    event = repo.events[0]
    assert event.event_type == "ItineraryCreatedEvent"
    assert event.aggregate_id == itinerary.id
    assert event.payload == {
        "itinerary_id": itinerary.id, "nombre_usuario": "jhon",
        "origin": "BOG", "destination": "MDE",
        "origin_city": "Bogotá", "destination_city": "Medellín",
        "travel_date": str(DEP.date()),
        "departure_at": DEP.astimezone(timezone.utc).isoformat(),
        "arrival_at": (DEP + timedelta(minutes=90)).astimezone(timezone.utc).isoformat(),
    }
    assert itinerary.user_id == "owner-1"


def test_UT004b_itinerary_rejects_same_origin_and_destination():
    with pytest.raises(InvalidItineraryError):
        Itinerary(nombre_usuario="jhon", origin=BOG, destination=BOG,
                  departure_at=DEP, duration_minutes=90, user_id="u1")


def test_UT005_itinerary_rejects_non_positive_duration():
    with pytest.raises(InvalidItineraryError):
        Itinerary(nombre_usuario="jhon", origin=BOG, destination=MDE,
                  departure_at=DEP, duration_minutes=0, user_id="u1")


def test_UT006_publishes_exactly_one_event_on_success():
    gateway = FakeAirportGateway([BOG, MDE])
    repo = FakeRepository()
    _create(repo, gateway)
    assert len(repo.events) == 1


def test_UT007_create_fails_if_origin_airport_missing_no_partial_write():
    gateway = FakeAirportGateway([MDE])
    repo = FakeRepository()
    with pytest.raises(AirportNotFoundError):
        _create(repo, gateway)
    assert len(repo.saved) == 0
    assert len(repo.events) == 0


def test_UT008_get_itinerary_enforces_ownership_anti_idor():
    gateway = FakeAirportGateway([BOG, MDE])
    repo = FakeRepository()
    created = _create(repo, gateway, user_id="owner-1")
    assert GetItinerary(repo).execute(created.id, "owner-1") is not None
    assert GetItinerary(repo).execute(created.id, "attacker-2") is None


def test_UT009_update_revalidates_airports_when_route_changes():
    gateway = FakeAirportGateway([BOG, MDE, CTG])
    repo = FakeRepository()
    created = _create(repo, gateway, user_id="owner-1")

    updated = UpdateItinerary(gateway, repo).execute(
        itinerary_id=created.id, user_id="owner-1", destination_id="3",
    )
    assert updated.destination.iata_code == "CTG"

    with pytest.raises(AirportNotFoundError):
        UpdateItinerary(gateway, repo).execute(
            itinerary_id=created.id, user_id="owner-1", destination_id="no-existe",
        )


def test_UT010_update_ignores_fields_outside_whitelist_anti_mass_assignment():
    gateway = FakeAirportGateway([BOG, MDE])
    repo = FakeRepository()
    created = _create(repo, gateway, user_id="owner-1")
    original_user_id = created.user_id
    original_nombre = created.nombre_usuario

    updated = UpdateItinerary(gateway, repo).execute(
        itinerary_id=created.id, user_id="owner-1", duration_minutes=120,
    )
    assert updated.duration_minutes == 120
    assert updated.user_id == original_user_id
    assert updated.nombre_usuario == original_nombre


def test_UT011_delete_returns_false_if_not_owner():
    gateway = FakeAirportGateway([BOG, MDE])
    repo = FakeRepository()
    created = _create(repo, gateway, user_id="owner-1")

    assert DeleteItinerary(repo).execute(created.id, "attacker-2") is False
    assert DeleteItinerary(repo).execute(created.id, "owner-1") is True


def test_update_raises_not_found_for_unknown_itinerary():
    gateway = FakeAirportGateway([BOG, MDE])
    repo = FakeRepository()
    with pytest.raises(ItineraryNotFoundError):
        UpdateItinerary(gateway, repo).execute(itinerary_id="no-existe", user_id="owner-1", duration_minutes=60)


# --- Eventos de actualizacion / borrado / email (Sprint 6) -------------------
def test_created_event_includes_email_only_when_present():
    gateway = FakeAirportGateway([BOG, MDE])
    repo = FakeRepository()
    CreateItinerary(gateway, repo).execute(
        nombre_usuario="jhon", origin_id="1", destination_id="2", departure_at=DEP,
        duration_minutes=90, user_id="u1", owner_email="jhon@example.com")
    CreateItinerary(gateway, repo).execute(
        nombre_usuario="ana", origin_id="1", destination_id="2", departure_at=DEP,
        duration_minutes=90, user_id="u2")
    assert repo.events[0].payload["email"] == "jhon@example.com"
    assert "email" not in repo.events[1].payload


def test_update_emits_updated_event_with_new_route_and_date():
    gateway = FakeAirportGateway([BOG, MDE, CTG])
    repo = FakeRepository()
    created = _create(repo, gateway)
    UpdateItinerary(gateway, repo).execute(
        itinerary_id=created.id, user_id="owner-1", destination_id="3", departure_at=at(40, 9))
    event = repo.events[-1]
    assert event.event_type == "ItineraryUpdatedEvent"
    new_dep = at(40, 9)
    assert event.payload == {
        "itinerary_id": created.id, "origin": "BOG", "destination": "CTG",
        "origin_city": "Bogotá", "destination_city": "Cartagena",
        "travel_date": str(new_dep.date()),
        "departure_at": new_dep.astimezone(timezone.utc).isoformat(),
        "arrival_at": (new_dep + timedelta(minutes=90)).astimezone(timezone.utc).isoformat(),
    }


def test_delete_emits_deleted_event_only_when_something_was_deleted():
    gateway = FakeAirportGateway([BOG, MDE])
    repo = FakeRepository()
    created = _create(repo, gateway)
    n = len(repo.events)
    assert DeleteItinerary(repo).execute(created.id, "attacker") is False
    assert len(repo.events) == n  # sin borrado no hay evento
    assert DeleteItinerary(repo).execute(created.id, "owner-1") is True
    assert repo.events[-1].event_type == "ItineraryDeletedEvent"
    assert repo.events[-1].payload == {"itinerary_id": created.id}
