"""RNF-005: logs estructurados en JSON con correlation ID (Nivel 1)."""
import logging
import time
import uuid

from fastapi import FastAPI, Request

from app.infrastructure.api.routes import router
from app.infrastructure.api.error_handlers import unhandled_exception_handler

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","msg":"%(message)s"}')
logger = logging.getLogger("airport-service")

app = FastAPI(title="Airport Service", version="1.0.0")
app.include_router(router)
app.add_exception_handler(Exception, unhandled_exception_handler)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    logger.info('{"trace_id":"%s","path":"%s","status":%d,"duration_ms":%d}',
                trace_id, request.url.path, response.status_code, duration_ms)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/health")
def health():
    return {"status": "ok"}
