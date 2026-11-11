"""Proceso programado: cada REMINDER_POLL_SECONDS busca recordatorios
vencidos (status PENDING y remind_at <= now()) y envia el correo.

- FOR UPDATE SKIP LOCKED: varias replicas no envian el mismo recordatorio a la vez.
- Un envio por transaccion; solo se marca SENT si el SMTP acepto el mensaje.
- At-least-once: si el proceso muere entre el SMTP y el COMMIT se reenvia
  (limitacion conocida; SMTP no es transaccional).
- Tras MAX_ATTEMPTS fallos queda FAILED con el ultimo error.
"""
import logging
import os
import time

import psycopg2

import mailer
import reminders

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reminder-worker")

MAX_ATTEMPTS = 5
BATCH_SIZE = 20

_SELECT_DUE = """
    SELECT itinerary_id::text, email, nombre_usuario, origin, destination, travel_date, attempts,
           departure_at, arrival_at, origin_city, destination_city
    FROM reminders
    WHERE status = 'PENDING' AND remind_at <= now()
    ORDER BY remind_at
    LIMIT 1
    FOR UPDATE SKIP LOCKED
"""


def send_due(database_url: str, send=mailer.send, batch_size: int = BATCH_SIZE) -> int:
    """Envia hasta `batch_size` recordatorios vencidos. Devuelve cuantos se enviaron."""
    tz_name, _ = reminders.settings()
    sender = os.environ.get("SMTP_FROM", "itinerarios@localhost")
    sent = 0
    for _ in range(batch_size):
        conn = psycopg2.connect(database_url, connect_timeout=5)
        try:
            with conn, conn.cursor() as cur:
                cur.execute(_SELECT_DUE)
                row = cur.fetchone()
                if row is None:
                    break
                (itinerary_id, email, nombre, origin, destination, travel_date, attempts,
                 departure_at, arrival_at, origin_city, destination_city) = row
                try:
                    send(mailer.build_reminder(sender, email, nombre or "viajero", origin, destination,
                                               travel_date, itinerary_id, tz_name,
                                               departure_at, arrival_at, origin_city, destination_city))
                except Exception as exc:  # noqa: BLE001 - SMTP/formato: se reintenta o queda FAILED
                    logger.error('{"event":"reminder_send_failed","itinerary_id":"%s","error":"%s"}',
                                 itinerary_id, repr(exc))
                    cur.execute(
                        """UPDATE reminders SET attempts = attempts + 1, last_error = %s, updated_at = now(),
                               status = CASE WHEN attempts + 1 >= %s THEN 'FAILED' ELSE 'PENDING' END
                           WHERE itinerary_id = %s""",
                        (repr(exc)[:500], MAX_ATTEMPTS, itinerary_id))
                    break  # no insistir en este ciclo; el siguiente poll reintenta
                cur.execute(
                    "UPDATE reminders SET status = 'SENT', sent_at = now(), attempts = attempts + 1, "
                    "last_error = NULL, updated_at = now() WHERE itinerary_id = %s", (itinerary_id,))
                sent += 1
                logger.info('{"event":"reminder_sent","itinerary_id":"%s"}', itinerary_id)
        finally:
            conn.close()
    return sent


def run(database_url: str, poll_seconds: float = 30.0, stop_after=None) -> None:
    n = 0
    while True:
        try:
            send_due(database_url)
        except psycopg2.Error as exc:
            logger.error('{"event":"reminder_db_error","error":"%s"}', repr(exc))
        n += 1
        if stop_after is not None and n >= stop_after:
            return
        time.sleep(poll_seconds)


if __name__ == "__main__":
    logger.info('{"event":"reminder_worker_started"}')
    run(os.environ["DATABASE_URL"], float(os.environ.get("REMINDER_POLL_SECONDS", "30")))
