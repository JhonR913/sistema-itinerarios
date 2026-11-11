#!/usr/bin/env python3
"""Prueba de resiliencia del Transactional Outbox: RabbitMQ CAE mientras se
crean itinerarios. Esperado:
  - La API sigue respondiendo 201 (no depende del broker).
  - Los eventos quedan PENDING en la tabla outbox (no se pierden).
  - Al volver el broker, el relay los entrega y las notificaciones aparecen.

Comandos configurables (defaults para Docker Compose):
  BROKER_STOP_CMD   def: docker compose stop rabbitmq
  BROKER_START_CMD  def: docker compose start rabbitmq
  + las mismas variables de e2e_smoke.py (AUTH_URL, ITINERARY_URL, AIRPORT_URL, *_SQL_CMD)
"""
import os
import shlex
from datetime import datetime, timedelta, timezone
import subprocess
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(__file__))
import e2e_smoke as e  # noqa: E402

STOP = os.environ.get("BROKER_STOP_CMD", "docker compose stop rabbitmq")
START = os.environ.get("BROKER_START_CMD", "docker compose start rabbitmq")
N = 3


def main():
    # Viajero nuevo en cada corrida: la agenda (409) es por usuario y no debe heredar vuelos viejos.
    user = f"resiliencia-{uuid.uuid4().hex[:6]}"
    _, tok = e.http("POST", f"{e.AUTH}/api/auth/token", {"username": user})
    token = tok["access_token"]
    _, airports = e.http("GET", f"{e.AIRPORT}/api/airports")

    subprocess.run(shlex.split(STOP), check=True, capture_output=True)
    print("-> RabbitMQ detenido", flush=True)
    time.sleep(3)
    ids = []
    for i in range(N):
        # Vuelos encadenados A->B, B->A, ... un dia aparte cada uno (agenda coherente).
        a, b = (airports[0], airports[1]) if i % 2 == 0 else (airports[1], airports[0])
        dep = f"{(datetime.now(timezone.utc) + timedelta(days=20 + i)).date().isoformat()}T10:00:00-05:00"
        code, body = e.http("POST", f"{e.ITIN}/api/itineraries", {
            "nombre_usuario": user, "origin_airport_id": a["id"],
            "destination_airport_id": b["id"], "departure_at": dep, "duration_minutes": 60}, token)
        if code == 201:
            ids.append(body["id"])
    e.step(f"A. Con el broker caido la API acepta {N} itinerarios (201)", len(ids) == N, f"creados={len(ids)}")
    in_list = ",".join(f"'{e.uid(i)}'" for i in ids)
    pending = e.sql(e.ITIN_SQL, f"SELECT count(*) FROM outbox WHERE aggregate_id IN ({in_list}) AND status='PENDING'")  # nosec B608
    e.step("B. Los eventos quedan PENDING en el outbox (no se pierden)", pending == str(N), f"pendientes={pending}")

    subprocess.run(shlex.split(START), check=True, capture_output=True)
    print("-> RabbitMQ reiniciado; esperando reconexion del relay y del consumidor...", flush=True)
    done = e.wait_for(lambda: e.sql(
        e.NOTIF_SQL, f"SELECT count(*) FROM notification_history WHERE itinerary_id IN ({in_list})") == str(N), 120, 2)  # nosec B608
    pub = e.sql(e.ITIN_SQL, f"SELECT count(*) FROM outbox WHERE aggregate_id IN ({in_list}) AND status='PUBLISHED'")  # nosec B608
    e.step("C. Al volver el broker el relay publica los eventos pendientes", pub == str(N), f"PUBLISHED={pub}")
    e.step("D. El consumidor reconecta y registra las notificaciones", bool(done))
    return e.finish()


if __name__ == "__main__":
    sys.exit(main())
