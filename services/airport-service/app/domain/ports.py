"""Puertos: contratos que el dominio define. La infraestructura los
implementa. Ver Documento_Arquitectura.docx seccion 4 (Patron Adapter)."""
from abc import ABC, abstractmethod
from typing import List, Optional
from .models import Airport


class AirportRepositoryPort(ABC):
    """Target del patron Adapter."""

    @abstractmethod
    def get_all(self) -> List[Airport]:
        ...

    @abstractmethod
    def get_by_id(self, airport_id: str) -> Optional[Airport]:
        ...


class AirportCachePort(ABC):
    @abstractmethod
    def get(self, key: str):
        ...

    @abstractmethod
    def set(self, key: str, value, ttl_seconds: int) -> None:
        ...
