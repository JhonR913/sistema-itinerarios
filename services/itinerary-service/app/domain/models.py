from dataclasses import dataclass
from datetime import date

from app.domain.exceptions import InvalidItineraryError, SameAirportError


@dataclass(frozen=True)
class AirportSnapshot:
    """Copia inmutable de los datos mínimos de un aeropuerto al momento de crear/editar
    el itinerario (ADR-006, RN-007). No se actualiza si el aeropuerto cambia en el origen."""

    iata_code: str
    name: str
    city: str


@dataclass
class Itinerary:
    id: str
    username: str
    departure_airport_id: str
    arrival_airport_id: str
    travel_date: date
    duration_minutes: int
    departure_snapshot: AirportSnapshot | None = None
    arrival_snapshot: AirportSnapshot | None = None

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if self.departure_airport_id == self.arrival_airport_id:
            raise SameAirportError("El aeropuerto de salida no puede ser igual al de llegada")
        if self.duration_minutes <= 0:
            raise InvalidItineraryError("La duración debe ser mayor a cero")
