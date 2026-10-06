from datetime import date

import pytest

from app.application.use_cases import CreateItineraryCommand, ItineraryService, UpdateItineraryCommand
from app.domain.exceptions import AirportNotFoundError, ItineraryNotFoundError, SameAirportError
from app.domain.events import ItineraryCreatedEvent
from app.domain.models import AirportSnapshot
from app.domain.ports import AirportGateway, ItineraryRepository


class FakeRepo(ItineraryRepository):
    def __init__(self):
        self.data = {}
        self.events = []

    def add(self, i, event):
        self.data[i.id] = i
        self.events.append(event)
        return i

    def get_by_id(self, id):
        return self.data.get(id)

    def list_by_username(self, username):
        return [i for i in self.data.values() if i.username == username]

    def update(self, i):
        self.data[i.id] = i
        return i

    def delete(self, id):
        self.data.pop(id, None)


class FakeAirports(AirportGateway):
    def __init__(self, known):
        self.known = set(known)
        self.calls = []

    def find(self, airport_id):
        self.calls.append(airport_id)
        if airport_id not in self.known:
            return None
        return AirportSnapshot(iata_code=f"A{airport_id}", name=f"Aeropuerto {airport_id}", city=f"Ciudad {airport_id}")


def make(known=("3", "9", "2")):
    airports = FakeAirports(known)
    return ItineraryService(FakeRepo(), airports), airports


def make_with_repo(known=("3", "9", "2")):
    repo = FakeRepo()
    return ItineraryService(repo, FakeAirports(known)), repo


def cmd(dep="3", arr="9", user="ana"):
    return CreateItineraryCommand(user, dep, arr, date(2026, 12, 1), 60)


def test_create_ok():
    service, _ = make()
    assert service.create(cmd()).username == "ana"


def test_same_airport_rejected():
    service, _ = make()
    with pytest.raises(SameAirportError):
        service.create(cmd(dep="3", arr="3"))


def test_unknown_airport_rejected():
    service, _ = make()
    with pytest.raises(AirportNotFoundError):
        service.create(cmd(arr="999"))


def test_idor_other_user_gets_not_found():
    service, _ = make()
    it = service.create(cmd())
    with pytest.raises(ItineraryNotFoundError):
        service.get(it.id, "luis")
    with pytest.raises(ItineraryNotFoundError):
        service.delete(it.id, "luis")
    with pytest.raises(ItineraryNotFoundError):
        service.update(it.id, "luis", UpdateItineraryCommand(duration_minutes=5))


def test_list_only_returns_own():
    service, _ = make()
    service.create(cmd(user="ana"))
    service.create(cmd(user="luis"))
    assert [i.username for i in service.list("ana")] == ["ana"]


def test_update_revalidates_only_changed_airports():
    service, airports = make()
    it = service.create(cmd())
    airports.calls.clear()
    service.update(it.id, "ana", UpdateItineraryCommand(arrival_airport_id="2"))
    assert airports.calls == ["2"]


def test_update_without_airport_change_does_not_call_gateway():
    service, airports = make()
    it = service.create(cmd())
    airports.calls.clear()
    service.update(it.id, "ana", UpdateItineraryCommand(duration_minutes=90))
    assert airports.calls == []


def test_update_to_same_airport_rejected():
    service, _ = make()
    it = service.create(cmd())
    with pytest.raises(SameAirportError):
        service.update(it.id, "ana", UpdateItineraryCommand(arrival_airport_id="3"))


def test_delete():
    service, _ = make()
    it = service.create(cmd())
    service.delete(it.id, "ana")
    with pytest.raises(ItineraryNotFoundError):
        service.get(it.id, "ana")


# --- US-004: snapshot inmutable (ADR-006, RN-007) y evento de creación (RF-010, RN-006) ---

def test_create_stores_airport_snapshots():
    service, _ = make()
    it = service.create(cmd())
    assert it.departure_snapshot == AirportSnapshot("A3", "Aeropuerto 3", "Ciudad 3")
    assert it.arrival_snapshot == AirportSnapshot("A9", "Aeropuerto 9", "Ciudad 9")


def test_create_emits_exactly_one_created_event():
    service, repo = make_with_repo()
    it = service.create(cmd())
    assert len(repo.events) == 1
    event = repo.events[0]
    assert isinstance(event, ItineraryCreatedEvent)
    assert event.itinerary_id == it.id and event.username == "ana"
    assert event.to_payload()["origen"]["iata_code"] == "A3"


def test_rejected_create_emits_no_event():
    service, repo = make_with_repo()
    with pytest.raises(AirportNotFoundError):
        service.create(cmd(arr="999"))
    with pytest.raises(SameAirportError):
        service.create(cmd(dep="3", arr="3"))
    assert repo.events == []


def test_update_refreshes_snapshot_only_for_changed_airport():
    service, repo = make_with_repo()
    it = service.create(cmd())
    updated = service.update(it.id, "ana", UpdateItineraryCommand(arrival_airport_id="2"))
    assert updated.arrival_snapshot.iata_code == "A2"
    assert updated.departure_snapshot.iata_code == "A3"
    assert len(repo.events) == 1  # actualizar NO genera un nuevo evento de creación
