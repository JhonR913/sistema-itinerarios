from fastapi import APIRouter, Depends, HTTPException

from app.application.use_cases import (
    CreateItinerary, GetItinerary, ListItineraries, UpdateItinerary, DeleteItinerary,
    AirportNotFoundError, ItineraryNotFoundError,
)
from app.domain.models import InvalidItineraryError
from app.domain.ports import AirportGatewayPort, ItineraryRepositoryPort, EventPublisherPort
from app.infrastructure.adapters.airport_http_adapter import AirportServiceUnavailableError
from app.infrastructure.api.dependencies import (
    get_airport_gateway, get_itinerary_repository, get_event_publisher,
)
from app.infrastructure.api.schemas import CreateItineraryRequest, UpdateItineraryRequest
from app.infrastructure.api.security import get_current_user_id

router = APIRouter(prefix="/api/itineraries", tags=["itineraries"])


@router.post("", status_code=201)
def create_itinerary(
    body: CreateItineraryRequest,
    user_id: str = Depends(get_current_user_id),
    airport_gateway: AirportGatewayPort = Depends(get_airport_gateway),
    repository: ItineraryRepositoryPort = Depends(get_itinerary_repository),
    event_publisher: EventPublisherPort = Depends(get_event_publisher),
):
    try:
        itinerary = CreateItinerary(airport_gateway, repository, event_publisher).execute(
            nombre_usuario=body.nombre_usuario,
            origin_id=body.origin_airport_id,
            destination_id=body.destination_airport_id,
            travel_date=body.travel_date,
            duration_minutes=body.duration_minutes,
            user_id=user_id,
        )
    except (AirportNotFoundError, InvalidItineraryError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AirportServiceUnavailableError:
        raise HTTPException(status_code=502, detail="Airport Service no disponible, intente mas tarde")
    return {"id": itinerary.id}


@router.get("")
def list_itineraries(
    user_id: str = Depends(get_current_user_id),
    repository: ItineraryRepositoryPort = Depends(get_itinerary_repository),
):
    itineraries = ListItineraries(repository).execute(user_id)
    return [_to_dict(i) for i in itineraries]


@router.get("/{itinerary_id}")
def get_itinerary(
    itinerary_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: ItineraryRepositoryPort = Depends(get_itinerary_repository),
):
    itinerary = GetItinerary(repository).execute(itinerary_id, user_id)
    if itinerary is None:
        raise HTTPException(status_code=404, detail="Itinerario no encontrado")
    return _to_dict(itinerary)


@router.put("/{itinerary_id}")
def update_itinerary(
    itinerary_id: str,
    body: UpdateItineraryRequest,
    user_id: str = Depends(get_current_user_id),
    airport_gateway: AirportGatewayPort = Depends(get_airport_gateway),
    repository: ItineraryRepositoryPort = Depends(get_itinerary_repository),
):
    try:
        itinerary = UpdateItinerary(airport_gateway, repository).execute(
            itinerary_id=itinerary_id,
            user_id=user_id,
            travel_date=body.travel_date,
            duration_minutes=body.duration_minutes,
            origin_id=body.origin_airport_id,
            destination_id=body.destination_airport_id,
        )
    except ItineraryNotFoundError:
        raise HTTPException(status_code=404, detail="Itinerario no encontrado")
    except (AirportNotFoundError, InvalidItineraryError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except AirportServiceUnavailableError:
        raise HTTPException(status_code=502, detail="Airport Service no disponible, intente mas tarde")
    return _to_dict(itinerary)


@router.delete("/{itinerary_id}", status_code=204)
def delete_itinerary(
    itinerary_id: str,
    user_id: str = Depends(get_current_user_id),
    repository: ItineraryRepositoryPort = Depends(get_itinerary_repository),
):
    deleted = DeleteItinerary(repository).execute(itinerary_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Itinerario no encontrado")


def _to_dict(itinerary) -> dict:
    return {
        "id": itinerary.id,
        "nombre_usuario": itinerary.nombre_usuario,
        "origin": itinerary.origin.__dict__,
        "destination": itinerary.destination.__dict__,
        "travel_date": str(itinerary.travel_date),
        "duration_minutes": itinerary.duration_minutes,
    }
