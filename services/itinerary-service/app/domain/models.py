from dataclasses import dataclass
from datetime import date

from app.domain.exceptions import InvalidItineraryError, SameAirportError


@dataclass
class Itinerary:
    id: str
    username: str
    departure_airport_id: str
    arrival_airport_id: str
    travel_date: date
    duration_minutes: int

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.departure_airport_id == self.arrival_airport_id:
            raise SameAirportError("El aeropuerto de salida no puede ser igual al de llegada")
        if self.duration_minutes <= 0:
            raise InvalidItineraryError("La duración debe ser mayor a cero")
