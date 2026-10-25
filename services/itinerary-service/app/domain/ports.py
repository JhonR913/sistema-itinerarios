from abc import ABC, abstractmethod
from typing import List, Optional
from .models import Itinerary, AirportSnapshot


class AirportGatewayPort(ABC):
    @abstractmethod
    def get_airport_snapshot(self, airport_id: str) -> Optional[AirportSnapshot]:
        ...


class ItineraryRepositoryPort(ABC):
    @abstractmethod
    def save(self, itinerary: Itinerary) -> None:
        ...

    @abstractmethod
    def update(self, itinerary: Itinerary) -> None:
        ...

    @abstractmethod
    def get_by_id(self, itinerary_id: str, user_id: str) -> Optional[Itinerary]:
        ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[Itinerary]:
        ...

    @abstractmethod
    def delete(self, itinerary_id: str, user_id: str) -> bool:
        ...


class EventPublisherPort(ABC):
    @abstractmethod
    def enqueue(self, event_type: str, payload: dict, aggregate_id: str) -> None:
        ...
