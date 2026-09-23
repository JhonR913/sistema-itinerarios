"""Contratos REST tal como quedaron cerrados en Documento_Arquitectura.docx
seccion 6.1:
  GET /api/airports        -> 200 OK
  GET /api/airports/{id}   -> 200 OK / 404 Not Found
"""
from fastapi import APIRouter, HTTPException

from app.application.use_cases import ListAirports, GetAirportById
from app.infrastructure.adapters.api_colombia_adapter import ApiColombiaAdapter
from app.infrastructure.adapters.redis_cache import RedisAirportCache
from app.settings import settings

router = APIRouter(prefix="/api/airports", tags=["airports"])

_cache = RedisAirportCache(settings.redis_url)
_repository = ApiColombiaAdapter(cache=_cache)


@router.get("")
def list_airports():
    airports = ListAirports(_repository).execute()
    return [a.__dict__ for a in airports]


@router.get("/{airport_id}")
def get_airport(airport_id: str):
    airport = GetAirportById(_repository).execute(airport_id)
    if airport is None:
        raise HTTPException(status_code=404, detail="Aeropuerto no encontrado")
    return airport.__dict__
