import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    AirportNotFoundError,
    AirportServiceUnavailableError,
    InvalidItineraryError,
    ItineraryNotFoundError,
    SameAirportError,
)
from app.infrastructure.adapters.sqlalchemy_repository import Base
from app.infrastructure.api.routers import router
from app.infrastructure.db import engine

logger = logging.getLogger(__name__)

app = FastAPI(title="Itinerary Service")
app.include_router(router)

Base.metadata.create_all(engine)  # solo desarrollo; luego migrar a Alembic

_ERRORS: dict[type[Exception], tuple[int, str]] = {
    SameAirportError: (422, "El aeropuerto de salida no puede ser igual al de llegada"),
    InvalidItineraryError: (422, "Datos de itinerario inválidos"),
    AirportNotFoundError: (422, "Alguno de los aeropuertos no existe"),
    ItineraryNotFoundError: (404, "Itinerario no encontrado"),
    AirportServiceUnavailableError: (503, "Servicio de aeropuertos no disponible"),
}


def _register(exc_type: type[Exception], status: int, message: str) -> None:
    @app.exception_handler(exc_type)
    async def _handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(status_code=status, content={"detail": message})


for _exc, (_status, _msg) in _ERRORS.items():
    _register(_exc, _status, _msg)


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado", exc_info=exc)  # detalle solo a logs
    return JSONResponse(status_code=500, content={"detail": "Error interno"})


@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}
