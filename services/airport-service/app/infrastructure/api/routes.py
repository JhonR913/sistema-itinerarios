"""Contratos REST tal como quedaron cerrados en Documento_Arquitectura.docx
seccion 6.1:
  GET /api/airports        -> 200 OK
  GET /api/airports/{id}   -> 200 OK / 404 Not Found

Esta capa SOLO traduce HTTP <-> casos de uso. La eleccion de que
adaptador concreto usar vive en dependencies.py (composition root),
no aqui.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.application.use_cases import ListAirports, GetAirportById
from app.domain.ports import AirportRepositoryPort
from app.infrastructure.api.dependencies import get_airport_repository

router = APIRouter(prefix="/api/airports", tags=["airports"])


@router.get("")
def list_airports(repository: AirportRepositoryPort = Depends(get_airport_repository)):
    airports = ListAirports(repository).execute()
    return [a.__dict__ for a in airports]


@router.get("/{airport_id}")
def get_airport(airport_id: str, repository: AirportRepositoryPort = Depends(get_airport_repository)):
    airport = GetAirportById(repository).execute(airport_id)
    if airport is None:
        raise HTTPException(status_code=404, detail="Aeropuerto no encontrado")
    return airport.__dict__
