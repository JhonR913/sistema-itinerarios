from abc import ABC, abstractmethod

from app.domain.events import ItineraryCreatedEvent
from app.domain.models import AirportSnapshot, Itinerary


class ItineraryRepository(ABC):
    @abstractmethod
    def add(self, itinerary: Itinerary, event: ItineraryCreatedEvent) -> Itinerary:
        """Guarda el itinerario y su evento en Outbox en UNA sola transacción."""

    @abstractmethod
    def get_by_id(self, itinerary_id: str) -> Itinerary | None: ...

    @abstractmethod
    def list_by_username(self, username: str) -> list[Itinerary]: ...

    @abstractmethod
    def update(self, itinerary: Itinerary) -> Itinerary: ...

    @abstractmethod
    def delete(self, itinerary_id: str) -> None: ...


class AirportGateway(ABC):
    @abstractmethod
    def find(self, airport_id: str) -> AirportSnapshot | None:
        """Datos del aeropuerto si existe en Airport Service; None si no existe."""
