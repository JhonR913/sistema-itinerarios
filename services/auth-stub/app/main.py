import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.models import DomainError
from app.infrastructure.api.routes import router

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","msg":"%(message)s"}')
logger = logging.getLogger("auth")

app = FastAPI(title="Identity Service", version="2.0.0")
app.include_router(router)


@app.exception_handler(DomainError)
async def domain_error_handler(_request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status, content={"detail": exc.message, "code": exc.code})


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    # Solo ruta y estado: nunca cuerpo, correo ni cookies.
    logger.info('{"trace_id":"%s","path":"%s","status":%d,"duration_ms":%d}',
                trace_id, request.url.path, response.status_code, duration_ms)
    response.headers["X-Trace-Id"] = trace_id
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/health")
def health():
    return {"status": "ok"}
