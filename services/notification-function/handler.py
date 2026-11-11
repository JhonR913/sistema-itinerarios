"""
Funcion OpenFaaS: SendNotificationFunction (RF-012) + recordatorios (Sprint 6).
Trigger: mensaje en la cola "itinerary.events" de RabbitMQ. El tipo de
evento viaja en la propiedad AMQP `type` y el id del outbox en `message_id`
(se pasan en `context = {"type": ..., "message_id": ...}`).

  ItineraryCreatedEvent -> fila en notification_history (idempotente) y
                           programa el recordatorio (reminders).
  ItineraryUpdatedEvent -> reprograma el recordatorio.
  ItineraryDeletedEvent -> cancela el recordatorio y borra datos personales.

Idempotencia: ON CONFLICT sobre indices/PK unicos (nada de SELECT-luego-INSERT)
y, para reminders, el orden por `last_event_id`.

Errores:
  - InvalidMessageError: permanente -> el consumidor rechaza SIN reencolar (DLQ).
  - psycopg2.Error (BD caida, etc.): transitorio, se propaga para reintentar.
"""
import json
import logging
import os
from datetime import date, datetime, timezone

import psycopg2

import reminders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("send-notification-function")

CREATED, UPDATED, DELETED = "ItineraryCreatedEvent", "ItineraryUpdatedEvent", "ItineraryDeletedEvent"
REQUIRED = {
    CREATED: ("itinerary_id", "nombre_usuario", "origin", "destination", "travel_date"),
    UPDATED: ("itinerary_id", "origin", "destination", "travel_date"),
    DELETED: ("itinerary_id",),
}
CHANNEL = "log-simulado"


class InvalidMessageError(ValueError):
    """Mensaje que nunca podra procesarse; reintentar no sirve."""


def _parse(event, message_type: str) -> dict:
    raw = event.body if hasattr(event, "body") else event
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise InvalidMessageError(f"JSON invalido: {exc}") from exc
    if not isinstance(payload, dict):
        raise InvalidMessageError("El mensaje debe ser un objeto JSON")
    missing = [f for f in REQUIRED[message_type] if not payload.get(f)]
    if missing:
        raise InvalidMessageError(f"Faltan campos obligatorios: {', '.join(missing)}")
    if "travel_date" in REQUIRED[message_type]:
        try:
            date.fromisoformat(payload["travel_date"])
        except (TypeError, ValueError) as exc:
            raise InvalidMessageError("travel_date invalida (YYYY-MM-DD)") from exc
    for key in ("departure_at", "arrival_at"):
        if payload.get(key) is not None:
            try:
                reminders.parse_instant(payload[key])
            except (TypeError, ValueError) as exc:
                raise InvalidMessageError(f"{key} invalida (ISO 8601 con zona horaria)") from exc
    for key in ("origin", "destination"):
        if key in payload and not reminders.IATA_RE.match(str(payload[key])):
            raise InvalidMessageError(f"{key} no es un codigo IATA")
    return payload


def _event_id(context, message_type: str) -> int:
    raw = (context or {}).get("message_id")
    if raw is None:
        if message_type == CREATED:
            return 0  # compatibilidad: invocacion sin id (p. ej. OpenFaaS directo)
        raise InvalidMessageError("Falta message_id (id del outbox) para ordenar el evento")
    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise InvalidMessageError(f"message_id invalido: {raw}") from exc


def handle(event, context=None):
    message_type = (context or {}).get("type") or CREATED
    if message_type not in REQUIRED:
        raise InvalidMessageError(f"Tipo de evento desconocido: {message_type}")
    payload = _parse(event, message_type)
    event_id = _event_id(context, message_type)
    itinerary_id = payload["itinerary_id"]

    # DATABASE_URL se lee en cada invocacion (no al importar) para poder
    # probar el modulo sin variables de entorno.
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=5)
    try:
        with conn, conn.cursor() as cur:
            try:
                if message_type == CREATED:
                    cur.execute(
                        """INSERT INTO notification_history (itinerary_id, channel, status, sent_at)
                           VALUES (%s, %s, %s, %s)
                           ON CONFLICT (itinerary_id) DO NOTHING""",
                        (itinerary_id, CHANNEL, "SENT", datetime.now(timezone.utc)),
                    )
                    inserted = cur.rowcount == 1
                    reminders.register_created(cur, payload, event_id)
                elif message_type == UPDATED:
                    inserted = reminders.apply_updated(cur, payload, event_id)
                else:
                    reminders.apply_deleted(cur, payload, event_id)
                    inserted = True
            except psycopg2.errors.InvalidTextRepresentation as exc:  # itinerary_id no es UUID
                raise InvalidMessageError(f"itinerary_id invalido: {itinerary_id}") from exc
    finally:
        conn.close()

    if message_type == CREATED:
        if not inserted:
            logger.info('{"event":"duplicate_ignored","itinerary_id":"%s"}', itinerary_id)
            return {"statusCode": 200, "body": "already processed"}
        logger.info(
            '{"event":"notification_sent","itinerary_id":"%s","nombre_usuario":"%s","ruta":"%s -> %s"}',
            itinerary_id, payload["nombre_usuario"], payload["origin"], payload["destination"],
        )
        return {"statusCode": 200, "body": "ok"}

    logger.info('{"event":"reminder_%s","itinerary_id":"%s","applied":%s}',
                "rescheduled" if message_type == UPDATED else "cancelled", itinerary_id, str(inserted).lower())
    return {"statusCode": 200, "body": "ok" if inserted else "ignored (stale or unknown)"}
