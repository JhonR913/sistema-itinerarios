from datetime import datetime, timezone
from typing import Callable, List, Optional

from app.domain.models import Itinerary, DomainEvent, InvalidItineraryError
from app.domain.ports import AirportGatewayPort, ItineraryRepositoryPort
from app.domain.scheduling import check_schedule


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _event_payload(it: Itinerary, owner_email: Optional[str] = None) -> dict:
    payload = {
        "itinerary_id": it.id,
        "nombre_usuario": it.nombre_usuario,
        "origin": it.origin.iata_code,
        "destination": it.destination.iata_code,
        "origin_city": it.origin.city,
        "destination_city": it.destination.city,
        "travel_date": str(it.travel_date),
        "departure_at": it.departure_at.isoformat(),
        "arrival_at": it.arrival_at.isoformat(),
    }
    if owner_email:  # solo si el JWT lo trae; permite enviar recordatorios
        payload["email"] = owner_email
    return payload


class AirportNotFoundError(ValueError):
    pass


class ItineraryNotFoundError(ValueError):
    pass


class CreateItinerary:
    def __init__(self, airport_gateway: AirportGatewayPort,
                 repository: ItineraryRepositoryPort,
                 min_connection_minutes: int = 0,
                 clock: Callable[[], datetime] = _now):
        self._airport_gateway = airport_gateway
        self._repository = repository
        self._min_connection = min_connection_minutes
        self._clock = clock

    def execute(self, nombre_usuario: str, origin_id: str, destination_id: str,
                departure_at: datetime, duration_minutes: int, user_id: str,
                owner_email: Optional[str] = None) -> Itinerary:
        origin = self._airport_gateway.get_airport_snapshot(origin_id)
        if origin is None:
            raise AirportNotFoundError(f"Aeropuerto de salida '{origin_id}' no existe.")

        destination = self._airport_gateway.get_airport_snapshot(destination_id)
        if destination is None:
            raise AirportNotFoundError(f"Aeropuerto de llegada '{destination_id}' no existe.")

        itinerary = Itinerary(
            nombre_usuario=nombre_usuario, origin=origin, destination=destination,
            departure_at=departure_at, duration_minutes=duration_minutes, user_id=user_id,
        )
        if itinerary.departure_at <= self._clock():
            raise InvalidItineraryError("La salida debe ser una fecha y hora futura.")

        event = DomainEvent(
            event_type="ItineraryCreatedEvent",
            aggregate_id=itinerary.id,
            payload=_event_payload(itinerary, owner_email),
        )
        # Itinerario + evento + validacion de agenda en UNA transaccion
        # (Transactional Outbox; el usuario queda bloqueado mientras se valida).
        self._repository.save_with_event(
            itinerary, event,
            schedule_check=lambda existing: check_schedule(itinerary, existing, self._min_connection))
        return itinerary


class GetItinerary:
    def __init__(self, repository: ItineraryRepositoryPort):
        self._repository = repository

    def execute(self, itinerary_id: str, user_id: str) -> Optional[Itinerary]:
        return self._repository.get_by_id(itinerary_id, user_id)


class ListItineraries:
    def __init__(self, repository: ItineraryRepositoryPort):
        self._repository = repository

    def execute(self, user_id: str) -> List[Itinerary]:
        return self._repository.list_by_user(user_id)


class UpdateItinerary:
    def __init__(self, airport_gateway: AirportGatewayPort,
                 repository: ItineraryRepositoryPort,
                 min_connection_minutes: int = 0,
                 clock: Callable[[], datetime] = _now):
        self._airport_gateway = airport_gateway
        self._repository = repository
        self._min_connection = min_connection_minutes
        self._clock = clock

    def execute(self, itinerary_id: str, user_id: str,
                departure_at: Optional[datetime] = None,
                duration_minutes: Optional[int] = None,
                origin_id: Optional[str] = None,
                destination_id: Optional[str] = None) -> Itinerary:
        itinerary = self._repository.get_by_id(itinerary_id, user_id)
        if itinerary is None:
            raise ItineraryNotFoundError(f"Itinerario '{itinerary_id}' no encontrado.")

        if origin_id is not None or destination_id is not None:
            new_origin = itinerary.origin
            new_destination = itinerary.destination
            if origin_id is not None:
                new_origin = self._airport_gateway.get_airport_snapshot(origin_id)
                if new_origin is None:
                    raise AirportNotFoundError(f"Aeropuerto de salida '{origin_id}' no existe.")
            if destination_id is not None:
                new_destination = self._airport_gateway.get_airport_snapshot(destination_id)
                if new_destination is None:
                    raise AirportNotFoundError(f"Aeropuerto de llegada '{destination_id}' no existe.")
            itinerary.update_route(new_origin, new_destination)

        if departure_at is not None:
            itinerary.reschedule(departure_at)
            if itinerary.departure_at <= self._clock():
                raise InvalidItineraryError("La salida debe ser una fecha y hora futura.")
        if duration_minutes is not None:
            if duration_minutes <= 0:
                raise InvalidItineraryError("La duracion debe ser un entero positivo.")
            itinerary.duration_minutes = duration_minutes

        payload = _event_payload(itinerary)
        payload.pop("nombre_usuario")   # el Updated no lleva datos personales
        self._repository.update_with_event(
            itinerary,
            DomainEvent(event_type="ItineraryUpdatedEvent", aggregate_id=itinerary.id, payload=payload),
            schedule_check=lambda existing: check_schedule(itinerary, existing, self._min_connection))
        return itinerary


class DeleteItinerary:
    def __init__(self, repository: ItineraryRepositoryPort):
        self._repository = repository

    def execute(self, itinerary_id: str, user_id: str) -> bool:
        return self._repository.delete_with_event(itinerary_id, user_id, DomainEvent(
            event_type="ItineraryDeletedEvent",
            aggregate_id=itinerary_id,
            payload={"itinerary_id": itinerary_id},
        ))
