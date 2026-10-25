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


class AirportDurableStorePort(ABC):
    """Almacen durable (PostgreSQL): segunda linea de resiliencia por
    debajo de la cache Redis. Separado de AirportRepositoryPort porque
    tiene una responsabilidad distinta (persistencia, no traduccion del
    modelo externo)."""

    @abstractmethod
    def upsert_many(self, airports: List[Airport]) -> None:
        ...

    @abstractmethod
    def get_all(self) -> List[Airport]:
        ...

    @abstractmethod
    def get_by_id(self, airport_id: str) -> Optional[Airport]:
        ...
