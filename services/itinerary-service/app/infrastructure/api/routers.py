from fastapi import APIRouter, Depends, HTTPException, Path, Response

from app.application.use_cases import CreateItineraryCommand, ItineraryService, UpdateItineraryCommand
from app.infrastructure.api.dependencies import current_username, get_service
from app.infrastructure.api.schemas import ItineraryCreate, ItineraryOut, ItineraryUpdate

router = APIRouter(prefix="/itineraries", tags=["itineraries"])

ItineraryId = Path(pattern=r"^[0-9a-fA-F-]{36}$")


@router.post("", response_model=ItineraryOut, status_code=201)
def create_itinerary(
    body: ItineraryCreate,
    username: str = Depends(current_username),
    service: ItineraryService = Depends(get_service),
):
    if body.username != username:
        raise HTTPException(status_code=403, detail="Operación no permitida")
    return service.create(CreateItineraryCommand(**body.model_dump()))


@router.get("", response_model=list[ItineraryOut])
def list_itineraries(
    username: str = Depends(current_username),
    service: ItineraryService = Depends(get_service),
):
    return service.list(username)


@router.get("/{itinerary_id}", response_model=ItineraryOut)
def get_itinerary(
    itinerary_id: str = ItineraryId,
    username: str = Depends(current_username),
    service: ItineraryService = Depends(get_service),
):
    return service.get(itinerary_id, username)


@router.patch("/{itinerary_id}", response_model=ItineraryOut)
def update_itinerary(
    body: ItineraryUpdate,
    itinerary_id: str = ItineraryId,
    username: str = Depends(current_username),
    service: ItineraryService = Depends(get_service),
):
    cmd = UpdateItineraryCommand(**body.model_dump(exclude_unset=True))
    return service.update(itinerary_id, username, cmd)


@router.delete("/{itinerary_id}", status_code=204)
def delete_itinerary(
    itinerary_id: str = ItineraryId,
    username: str = Depends(current_username),
    service: ItineraryService = Depends(get_service),
):
    service.delete(itinerary_id, username)
    return Response(status_code=204)
