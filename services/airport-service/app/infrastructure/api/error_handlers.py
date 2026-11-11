"""RNF-SEC-008: nunca exponer stack trace al cliente en produccion."""
import logging

import httpx
import pybreaker
from fastapi import Request
from fastapi.responses import JSONResponse
from tenacity import RetryError

logger = logging.getLogger("airport-service")

UPSTREAM_ERRORS = (pybreaker.CircuitBreakerError, httpx.HTTPError, RetryError)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error('{"event":"unhandled_exception","path":"%s","error":"%s"}',
                 request.url.path, repr(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor."},
    )


async def upstream_unavailable_handler(request: Request, exc: Exception) -> JSONResponse:
    """API Colombia caida y sin cache/BD de respaldo: 503 (reintentable),
    no 500 (bug)."""
    logger.error('{"event":"upstream_unavailable","path":"%s","error":"%s"}',
                 request.url.path, type(exc).__name__)
    return JSONResponse(
        status_code=503,
        content={"detail": "Fuente de aeropuertos no disponible, intente mas tarde."},
    )
