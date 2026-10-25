"""
Funcion OpenFaaS: SendNotificationFunction (RF-012).
Trigger: mensaje en la cola "itinerary.created" de RabbitMQ.
Idempotente: verifica si ya existe un registro para ese itinerary_id
antes de insertar (at-least-once delivery del broker)."""
import json
import logging
import os
from datetime import datetime, timezone

import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("send-notification-function")

DATABASE_URL = os.environ["DATABASE_URL"]


def handle(event, context):
    payload = json.loads(event.body if hasattr(event, "body") else event)
    itinerary_id = payload["itinerary_id"]

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn, conn.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM notification_history WHERE itinerary_id = %s", (itinerary_id,)
            )
            if cur.fetchone():
                logger.info('{"event":"duplicate_ignored","itinerary_id":"%s"}', itinerary_id)
                return {"statusCode": 200, "body": "already processed"}

            logger.info(
                '{"event":"notification_sent","itinerary_id":"%s","nombre_usuario":"%s","ruta":"%s -> %s"}',
                itinerary_id, payload["nombre_usuario"], payload["origin"], payload["destination"],
            )

            cur.execute(
                """INSERT INTO notification_history (itinerary_id, channel, status, sent_at)
                   VALUES (%s, %s, %s, %s)""",
                (itinerary_id, "log-simulado", "SENT", datetime.now(timezone.utc)),
            )
    finally:
        conn.close()

    return {"statusCode": 200, "body": "ok"}
