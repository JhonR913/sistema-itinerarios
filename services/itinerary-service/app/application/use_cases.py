from datetime import date
from typing import List, Optional

from app.domain.models import Itinerary, AirportSnapshot
from app.domain.ports import AirportGatewayPort, ItineraryRepositoryPort, EventPublisherPort


class AirportNotFoundError(ValueError):
    pass


class ItineraryNotFoundError(ValueError):
    pass


class CreateItinerary:
    def __init__(self, airport_gateway: AirportGatewayPort,
                 repository: ItineraryRepositoryPort,
                 event_publisher: EventPublisherPort):
        self._airport_gateway = airport_gateway
        self._repository = repository
        self._event_publisher = event_publisher

    def execute(self, nombre_usuario: str, origin_id: str, destination_id: str,
                travel_date: date, duration_minutes: int, user_id: str) -> Itinerary:
        origin = self._airport_gateway.get_airport_snapshot(origin_id)
        if origin is None:
            raise AirportNotFoundError(f"Aeropuerto de salida '{origin_id}' no existe.")

        destination = self._airport_gateway.get_airport_snapshot(destination_id)
        if destination is None:
            raise AirportNotFoundError(f"Aeropuerto de llegada '{destination_id}' no existe.")

        itinerary = Itinerary(
            nombre_usuario=nombre_usuario, origin=origin, destination=destination,
            travel_date=travel_date, duration_minutes=duration_minutes, user_id=user_id,
        )

        self._repository.save(itinerary)
        self._event_publisher.enqueue(
            event_type="ItineraryCreatedEvent",
            aggregate_id=itinerary.id,
            payload={
                "itinerary_id": itinerary.id,
                "nombre_usuario": itinerary.nombre_usuario,
                "origin": itinerary.origin.iata_code,
                "destination": itinerary.destination.iata_code,
                "travel_date": str(itinerary.travel_date),
            },
        )
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
                 repository: ItineraryRepositoryPort):
        self._airport_gateway = airport_gateway
        self._repository = repository

    def execute(self, itinerary_id: str, user_id: str,
                travel_date: Optional[date] = None,
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

        if travel_date is not None:
            itinerary.travel_date = travel_date
        if duration_minutes is not None:
            if duration_minutes <= 0:
                from app.domain.models import InvalidItineraryError
                raise InvalidItineraryError("La duracion debe ser un entero positivo.")
            itinerary.duration_minutes = duration_minutes

        self._repository.update(itinerary)
        return itinerary


class DeleteItinerary:
    def __init__(self, repository: ItineraryRepositoryPort):
        self._repository = repository

    def execute(self, itinerary_id: str, user_id: str) -> bool:
        return self._repository.delete(itinerary_id, user_id)
