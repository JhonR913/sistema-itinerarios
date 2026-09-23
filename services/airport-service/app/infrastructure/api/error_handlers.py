"""RNF-SEC-008: nunca exponer stack trace al cliente en produccion."""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("airport-service")


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error('{"event":"unhandled_exception","path":"%s","error":"%s"}',
                 request.url.path, repr(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor."},
    )
