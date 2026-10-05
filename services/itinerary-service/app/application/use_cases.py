from dataclasses import dataclass, replace
from datetime import date
from uuid import uuid4

from app.domain.exceptions import AirportNotFoundError, ItineraryNotFoundError
from app.domain.models import Itinerary
from app.domain.ports import AirportGateway, ItineraryRepository


@dataclass
class CreateItineraryCommand:
    username: str
    departure_airport_id: str
    arrival_airport_id: str
    travel_date: date
    duration_minutes: int


@dataclass
class UpdateItineraryCommand:
    """Lista blanca de campos modificables (anti mass-assignment). username NO es modificable."""

    departure_airport_id: str | None = None
    arrival_airport_id: str | None = None
    travel_date: date | None = None
    duration_minutes: int | None = None


class ItineraryService:
    def __init__(self, repository: ItineraryRepository, airports: AirportGateway) -> None:
        self._repo = repository
        self._airports = airports

    def create(self, cmd: CreateItineraryCommand) -> Itinerary:
        itinerary = Itinerary(  # valida salida != llegada y duración (RF-006)
            id=str(uuid4()),
            username=cmd.username,
            departure_airport_id=cmd.departure_airport_id,
            arrival_airport_id=cmd.arrival_airport_id,
            travel_date=cmd.travel_date,
            duration_minutes=cmd.duration_minutes,
        )
        self._ensure_airports_exist(itinerary.departure_airport_id, itinerary.arrival_airport_id)  # RF-005
        return self._repo.add(itinerary)

    def get(self, itinerary_id: str, username: str) -> Itinerary:
        return self._get_owned(itinerary_id, username)

    def list(self, username: str) -> list[Itinerary]:
        return self._repo.list_by_username(username)

    def update(self, itinerary_id: str, username: str, cmd: UpdateItineraryCommand) -> Itinerary:
        current = self._get_owned(itinerary_id, username)
        changes = {k: v for k, v in vars(cmd).items() if v is not None}
        updated = replace(current, **changes)  # re-ejecuta validaciones del dominio

        changed_airports = [
            new
            for new, old in (
                (updated.departure_airport_id, current.departure_airport_id),
                (updated.arrival_airport_id, current.arrival_airport_id),
            )
            if new != old
        ]
        self._ensure_airports_exist(*changed_airports)  # RF-008: re-valida solo si cambian
        return self._repo.update(updated)

    def delete(self, itinerary_id: str, username: str) -> None:
        self._get_owned(itinerary_id, username)
        self._repo.delete(itinerary_id)

    def _get_owned(self, itinerary_id: str, username: str) -> Itinerary:
        itinerary = self._repo.get_by_id(itinerary_id)
        # Anti-IDOR: si no es del usuario se responde igual que si no existiera.
        if itinerary is None or itinerary.username != username:
            raise ItineraryNotFoundError()
        return itinerary

    def _ensure_airports_exist(self, *airport_ids: str) -> None:
        for airport_id in airport_ids:
            if not self._airports.exists(airport_id):
                raise AirportNotFoundError()
