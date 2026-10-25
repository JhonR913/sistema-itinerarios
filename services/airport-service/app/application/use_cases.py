"""Casos de uso (RF-001, RF-002 en Documento_Requerimientos.docx).
No conocen FastAPI, Redis ni httpx: solo los puertos."""
from typing import List, Optional
from app.domain.models import Airport
from app.domain.ports import AirportRepositoryPort


class ListAirports:
    def __init__(self, repository: AirportRepositoryPort):
        self._repository = repository

    def execute(self) -> List[Airport]:
        return self._repository.get_all()


class GetAirportById:
    def __init__(self, repository: AirportRepositoryPort):
        self._repository = repository

    def execute(self, airport_id: str) -> Optional[Airport]:
        return self._repository.get_by_id(airport_id)
