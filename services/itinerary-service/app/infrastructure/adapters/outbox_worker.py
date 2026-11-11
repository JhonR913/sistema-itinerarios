"""Relay del patron Transactional Outbox.

Lee eventos PENDING de la tabla `outbox` y los publica en RabbitMQ con
publisher confirms. Solo marca PUBLISHED cuando el broker confirma.
Garantia: at-least-once (un fallo entre el confirm y el UPDATE puede
reenviar el mensaje; el consumidor es idempotente).

- FOR UPDATE SKIP LOCKED: se pueden ejecutar varias replicas del relay sin
  publicar el mismo evento dos veces a la vez.
- Reintentos con tope (MAX_ATTEMPTS): pasado el tope el evento queda FAILED
  y deja de bloquear la cola; el error queda en `last_error`.
- Reconexion automatica con backoff si RabbitMQ o PostgreSQL no estan listos.
"""
import json
import logging
import os
import time
from typing import Optional

import pika
from pika.exceptions import AMQPError
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("outbox-worker")

QUEUE_NAME = "itinerary.events"
DLX_NAME = "itinerary.dlx"
DLQ_NAME = "itinerary.events.dlq"
BATCH_SIZE = 20
MAX_ATTEMPTS = 10

_SELECT_PENDING = text("""
    SELECT id, event_type, payload FROM outbox
    WHERE status = 'PENDING'
    ORDER BY id
    LIMIT 1
    FOR UPDATE SKIP LOCKED
""")
_MARK_PUBLISHED = text(
    "UPDATE outbox SET status = 'PUBLISHED', published_at = now(), attempts = attempts + 1, last_error = NULL WHERE id = :id"
)
_MARK_FAILED_ATTEMPT = text("""
    UPDATE outbox SET attempts = attempts + 1, last_error = :error,
        status = CASE WHEN attempts + 1 >= :max_attempts THEN 'FAILED' ELSE 'PENDING' END
    WHERE id = :id
""")


def declare_topology(channel) -> None:
    """Misma topologia que declara el consumidor (argumentos identicos, si
    no RabbitMQ responde PRECONDITION_FAILED)."""
    channel.exchange_declare(exchange=DLX_NAME, exchange_type="direct", durable=True)
    channel.queue_declare(queue=DLQ_NAME, durable=True)
    channel.queue_bind(queue=DLQ_NAME, exchange=DLX_NAME, routing_key=DLQ_NAME)
    channel.queue_declare(
        queue=QUEUE_NAME, durable=True,
        arguments={"x-dead-letter-exchange": DLX_NAME, "x-dead-letter-routing-key": DLQ_NAME},
    )


def _body(payload) -> bytes:
    return (payload if isinstance(payload, str) else json.dumps(payload)).encode("utf-8")


def relay_once(engine, channel, batch_size: int = BATCH_SIZE) -> int:
    """Publica hasta `batch_size` eventos, UNA transaccion por evento (un
    fallo del broker a mitad de lote no revierte lo ya confirmado).
    Devuelve cuantos eventos se publicaron."""
    published = 0
    for _ in range(batch_size):
        with engine.begin() as conn:
            row = conn.execute(_SELECT_PENDING).mappings().first()
            if row is None:
                break
            try:
                body = _body(row["payload"])
            except (TypeError, ValueError) as exc:  # payload no serializable: no es culpa del broker
                _register_failure(conn, row["id"], exc)
                continue
            # Errores AMQP (conexion caida, nack, sin ruta) se propagan: la
            # transaccion hace rollback, el evento sigue PENDING y run()
            # reconecta. No se cuentan como intento del evento.
            channel.basic_publish(
                exchange="", routing_key=QUEUE_NAME, body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2, content_type="application/json",
                    message_id=str(row["id"]), type=row["event_type"],
                    timestamp=int(time.time()),
                ),
                mandatory=True,
            )
            conn.execute(_MARK_PUBLISHED, {"id": row["id"]})
            published += 1
            logger.info(json.dumps({"event": "outbox_published", "outbox_id": row["id"], "type": row["event_type"]}))
    return published


def _register_failure(conn, outbox_id: int, exc: Exception) -> None:
    logger.error(json.dumps({"event": "outbox_event_unserializable", "outbox_id": outbox_id, "error": repr(exc)}))
    conn.execute(_MARK_FAILED_ATTEMPT, {"id": outbox_id, "error": repr(exc)[:500], "max_attempts": MAX_ATTEMPTS})


def run(database_url: str, rabbitmq_url: str, poll_interval_seconds: float = 2.0,
        reconnect_delay_seconds: float = 5.0, stop_after: Optional[int] = None) -> None:
    engine = create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 3, "options": "-c statement_timeout=5000"})
    iterations = 0
    while True:
        connection = None
        try:
            connection = pika.BlockingConnection(pika.URLParameters(rabbitmq_url))
            channel = connection.channel()
            channel.confirm_delivery()
            declare_topology(channel)
            logger.info(json.dumps({"event": "outbox_worker_started", "queue": QUEUE_NAME}))
            while True:
                sent = relay_once(engine, channel)
                # Lote lleno = probablemente hay mas pendientes: NO dormir.
                # (Con sleep fijo el relay drenaba solo ~10 eventos/s y bajo
                # carga el outbox acumulaba backlog; hallazgo de Locust.)
                wait = 0 if sent >= BATCH_SIZE else poll_interval_seconds
                connection.process_data_events(time_limit=wait)  # mantiene heartbeats
                iterations += 1
                if stop_after is not None and iterations >= stop_after:
                    return
        except (AMQPError, SQLAlchemyError, OSError) as exc:
            logger.error(json.dumps({"event": "outbox_worker_reconnecting", "error": repr(exc)}))
            time.sleep(reconnect_delay_seconds)
        finally:
            if connection is not None and connection.is_open:
                try:
                    connection.close()
                except AMQPError:
                    pass


if __name__ == "__main__":
    run(os.environ["DATABASE_URL"], os.environ["RABBITMQ_URL"])
