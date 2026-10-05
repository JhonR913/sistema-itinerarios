from abc import ABC, abstractmethod

from app.domain.models import Itinerary


class ItineraryRepository(ABC):
    @abstractmethod
    def add(self, itinerary: Itinerary) -> Itinerary: ...

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
    def exists(self, airport_id: str) -> bool:
        """True si el aeropuerto existe en Airport Service."""
