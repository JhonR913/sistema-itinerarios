from abc import ABC, abstractmethod
from typing import Callable, List, Optional
from .models import Itinerary, AirportSnapshot, DomainEvent

ScheduleCheck = Callable[[List[Itinerary]], None]


class AirportGatewayPort(ABC):
    @abstractmethod
    def get_airport_snapshot(self, airport_id: str) -> Optional[AirportSnapshot]:
        ...


class ItineraryRepositoryPort(ABC):
    @abstractmethod
    def save_with_event(self, itinerary: Itinerary, event: DomainEvent,
                        schedule_check: Optional[ScheduleCheck] = None) -> None:
        """Persiste el itinerario y el evento (outbox) de forma ATOMICA:
        o se guardan los dos o no se guarda ninguno (Double Write Problem).
        `schedule_check` recibe los itinerarios del usuario DENTRO de la misma
        transaccion (con el usuario bloqueado) para validar la agenda sin
        carreras entre peticiones concurrentes; si lanza, nada se guarda."""

    @abstractmethod
    def update_with_event(self, itinerary: Itinerary, event: DomainEvent,
                          schedule_check: Optional[ScheduleCheck] = None) -> None:
        """Actualiza el itinerario y registra el evento en la MISMA transaccion."""

    @abstractmethod
    def get_by_id(self, itinerary_id: str, user_id: str) -> Optional[Itinerary]:
        ...

    @abstractmethod
    def list_by_user(self, user_id: str) -> List[Itinerary]:
        ...

    @abstractmethod
    def delete_with_event(self, itinerary_id: str, user_id: str, event: DomainEvent) -> bool:
        """Borra y registra el evento en la misma transaccion. El evento solo
        se guarda si realmente se borro una fila (devuelve False si no)."""
