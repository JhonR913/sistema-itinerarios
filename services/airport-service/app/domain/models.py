"""Dominio puro (sin imports de FastAPI, httpx, redis).
Modelo Airport tal como quedo definido en Documento_Arquitectura.docx,
seccion 7.1, y en el Diagrama de Clases (Documento_Diseno_y_Diagramas.docx)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    id: str
    external_id: str
    iata_code: str
    name: str
    city: str
    latitude: float
    longitude: float

    def __post_init__(self):
        if not self.iata_code or len(self.iata_code) not in (3, 4):
            raise ValueError("iata_code invalido")
