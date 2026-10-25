from datetime import date

import pytest

from app.domain.models import Itinerary, AirportSnapshot, InvalidItineraryError
from app.domain.ports import AirportGatewayPort, ItineraryRepositoryPort, EventPublisherPort
from app.application.use_cases import (
    CreateItinerary, GetItinerary, UpdateItinerary, DeleteItinerary,
    AirportNotFoundError, ItineraryNotFoundError,
)

BOG = AirportSnapshot("1", "BOG", "El Dorado", "Bogotá")
MDE = AirportSnapshot("2", "MDE", "José María Córdova", "Medellín")
CTG = AirportSnapshot("3", "CTG", "Rafael Núñez", "Cartagena")


class FakeAirportGateway(AirportGatewayPort):
    def __init__(self, known):
        self._known = {a.airport_id: a for a in known}

    def get_airport_snapshot(self, airport_id):
        return self._known.get(airport_id)


class FakeRepository(ItineraryRepositoryPort):
    def __init__(self):
        self.saved = []

    def save(self, itinerary):
        self.saved.append(itinerary)

    def update(self, itinerary):
        pass

    def get_by_id(self, itinerary_id, user_id):
        return next((i for i in self.saved if i.id == itinerary_id and i.user_id == user_id), None)

    def list_by_user(self, user_id):
        return [i for i in self.saved if i.user_id == user_id]

    def delete(self, itinerary_id, user_id):
        before = len(self.saved)
        self.saved = [i for i in self.saved if not (i.id == itinerary_id and i.user_id == user_id)]
        return len(self.saved) < before


class FakeEventPublisher(EventPublisherPort):
    def __init__(self):
        self.events = []

    def enqueue(self, event_type, payload, aggregate_id):
        self.events.append((event_type, payload, aggregate_id))


def _create(repo, gateway, publisher, user_id="owner-1", origin="1", destination="2"):
    return CreateItinerary(gateway, repo, publisher).execute(
        nombre_usuario="jhon", origin_id=origin, destination_id=destination,
        travel_date=date(2026, 12, 1), duration_minutes=90, user_id=user_id,
    )


def test_UT004_create_itinerary_happy_path_publishes_event():
    gateway = FakeAirportGateway([BOG, MDE])
    repo, publisher = FakeRepository(), FakeEventPublisher()
    itinerary = _create(repo, gateway, publisher)
    assert len(repo.saved) == 1
    assert len(publisher.events) == 1
    assert publisher.events[0][0] == "ItineraryCreatedEvent"
    assert itinerary.user_id == "owner-1"


def test_UT004b_itinerary_rejects_same_origin_and_destination():
    with pytest.raises(InvalidItineraryError):
        Itinerary(nombre_usuario="jhon", origin=BOG, destination=BOG,
                  travel_date=date(2026, 12, 1), duration_minutes=90, user_id="u1")


def test_UT005_itinerary_rejects_non_positive_duration():
    with pytest.raises(InvalidItineraryError):
        Itinerary(nombre_usuario="jhon", origin=BOG, destination=MDE,
                  travel_date=date(2026, 12, 1), duration_minutes=0, user_id="u1")


def test_UT006_publishes_exactly_one_event_on_success():
    gateway = FakeAirportGateway([BOG, MDE])
    repo, publisher = FakeRepository(), FakeEventPublisher()
    _create(repo, gateway, publisher)
    assert len(publisher.events) == 1


def test_UT007_create_fails_if_origin_airport_missing_no_partial_write():
    gateway = FakeAirportGateway([MDE])
    repo, publisher = FakeRepository(), FakeEventPublisher()
    with pytest.raises(AirportNotFoundError):
        _create(repo, gateway, publisher)
    assert len(repo.saved) == 0
    assert len(publisher.events) == 0


def test_UT008_get_itinerary_enforces_ownership_anti_idor():
    gateway = FakeAirportGateway([BOG, MDE])
    repo, publisher = FakeRepository(), FakeEventPublisher()
    created = _create(repo, gateway, publisher, user_id="owner-1")
    assert GetItinerary(repo).execute(created.id, "owner-1") is not None
    assert GetItinerary(repo).execute(created.id, "attacker-2") is None


def test_UT009_update_revalidates_airports_when_route_changes():
    gateway = FakeAirportGateway([BOG, MDE, CTG])
    repo, publisher = FakeRepository(), FakeEventPublisher()
    created = _create(repo, gateway, publisher, user_id="owner-1")

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
    repo, publisher = FakeRepository(), FakeEventPublisher()
    created = _create(repo, gateway, publisher, user_id="owner-1")
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
    repo, publisher = FakeRepository(), FakeEventPublisher()
    created = _create(repo, gateway, publisher, user_id="owner-1")

    assert DeleteItinerary(repo).execute(created.id, "attacker-2") is False
    assert DeleteItinerary(repo).execute(created.id, "owner-1") is True


def test_update_raises_not_found_for_unknown_itinerary():
    gateway = FakeAirportGateway([BOG, MDE])
    repo = FakeRepository()
    with pytest.raises(ItineraryNotFoundError):
        UpdateItinerary(gateway, repo).execute(itinerary_id="no-existe", user_id="owner-1", duration_minutes=60)
