from dataclasses import dataclass
from typing import Any, ClassVar

from app.domain.models import AirportSnapshot, Itinerary


@dataclass(frozen=True)
class ItineraryCreatedEvent:
    """Evento de integración (RF-010, RN-006): se genera exactamente uno por itinerario creado."""

    event_type: ClassVar[str] = "ItineraryCreatedEvent"

    itinerary_id: str
    username: str
    origin: AirportSnapshot
    destination: AirportSnapshot
    travel_date: str  # ISO 8601

    @classmethod
    def from_itinerary(cls, itinerary: Itinerary) -> "ItineraryCreatedEvent":
        assert itinerary.departure_snapshot and itinerary.arrival_snapshot
        return cls(
            itinerary_id=itinerary.id,
            username=itinerary.username,
            origin=itinerary.departure_snapshot,
            destination=itinerary.arrival_snapshot,
            travel_date=itinerary.travel_date.isoformat(),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "itinerary_id": self.itinerary_id,
            "nombre_usuario": self.username,
            "origen": vars(self.origin),
            "destino": vars(self.destination),
            "fecha": self.travel_date,
        }
