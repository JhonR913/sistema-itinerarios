from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.application.use_cases import (
    CreateItinerary, GetItinerary, ListItineraries, UpdateItinerary, DeleteItinerary,
    AirportNotFoundError, ItineraryNotFoundError,
)
from app.domain.models import InvalidItineraryError
from app.domain.scheduling import ScheduleConflictError
from app.settings import settings
from app.domain.ports import AirportGatewayPort, ItineraryRepositoryPort
from app.infrastructure.adapters.airport_http_adapter import AirportServiceUnavailableError
from app.infrastructure.api.dependencies import get_airport_gateway, get_itinerary_repository
from app.infrastructure.api.schemas import CreateItineraryRequest, UpdateItineraryRequest
from app.infrastructure.api.security import AuthenticatedUser, get_current_user, get_current_user_id

router = APIRouter(prefix="/api/itineraries", tags=["itineraries"])


def _require_uuid(itinerary_id: str) -> str:
    """Un id que no es UUID no puede existir: 404 en vez de un 500 por
    'invalid input syntax for type uuid' de PostgreSQL."""
    try:
        return str(UUID(itinerary_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="Itinerario no encontrado")


@router.post("", status_code=201)
def create_itinerary(
    body: CreateItineraryRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    airport_gateway: AirportGatewayPort = Depends(get_airport_gateway),
    repository: ItineraryRepositoryPort = Depends(get_itinerary_repository),
):
    try:
        itinerary = CreateItinerary(airport_gateway, repository, settings.min_connection_minutes).execute(
            nombre_usuario=body.nombre_usuario,
            origin_id=body.origin_airport_id,
            destination_id=body.destination_airport_id,
            departure_at=body.departure_at,
            duration_minutes=body.duration_minutes,
            user_id=user.user_id,
            owner_email=user.email,
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
    itinerary = GetItinerary(repository).execute(_require_uuid(itinerary_id), user_id)
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
        itinerary = UpdateItinerary(airport_gateway, repository, settings.min_connection_minutes).execute(
            itinerary_id=_require_uuid(itinerary_id),
            user_id=user_id,
            departure_at=body.departure_at,
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
    deleted = DeleteItinerary(repository).execute(_require_uuid(itinerary_id), user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Itinerario no encontrado")


def _to_dict(itinerary) -> dict:
    return {
        "id": itinerary.id,
        "nombre_usuario": itinerary.nombre_usuario,
        "origin": itinerary.origin.__dict__,
        "destination": itinerary.destination.__dict__,
        "travel_date": str(itinerary.travel_date),
        "departure_at": itinerary.departure_at.isoformat(),
        "arrival_at": itinerary.arrival_at.isoformat(),
        "duration_minutes": itinerary.duration_minutes,
    }
