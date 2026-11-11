import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("itinerary-service")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error('{"event":"unhandled_exception","path":"%s","error":"%s"}',
                 request.url.path, repr(exc))
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor."})


async def database_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    """PostgreSQL caido/inalcanzable: 503 (reintentable), no 500 (bug)."""
    logger.error('{"event":"database_unavailable","path":"%s","error":"%s"}',
                 request.url.path, type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": "Servicio temporalmente no disponible, intente mas tarde."},
                        headers={"Retry-After": "5"})


async def schedule_conflict_handler(request: Request, exc: Exception) -> JSONResponse:
    """Agenda incoherente (traslape / ciudad de origen incorrecta): 409."""
    return JSONResponse(status_code=409, content={
        "detail": str(exc), "code": exc.code,
        "conflicting_itinerary_id": exc.conflicting_itinerary_id})
