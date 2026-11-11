#!/usr/bin/env python3
"""Prueba de humo de EXTREMO A EXTREMO del flujo real:

  login -> aeropuertos -> crear itinerario -> outbox -> RabbitMQ ->
  consumidor -> notification_history (+ idempotencia y DLQ).

Solo biblioteca estandar. Sale con codigo != 0 si algun paso falla, y no
da por buenos pasos que no pudo comprobar (los marca SKIP).

Variables (todas opcionales; los valores por defecto sirven para Docker Compose):
  GATEWAY_URL        si se define (p.ej. http://localhost) todo va por Traefik
  AUTH_URL AIRPORT_URL ITINERARY_URL   (def. http://localhost:8003/8001/8002)
  NOTIF_SQL_CMD      comando que ejecuta SQL en la BD de notificaciones leyendo
                     la consulta por argumento. Def: docker compose exec
  ITIN_SQL_CMD       idem para la BD de itinerarios (comprobar outbox)
  RABBIT_MGMT_URL    def. http://localhost:15672  (con RABBIT_USER / RABBIT_PASS)
  MAILPIT_URL        def. http://localhost:8025   (API de Mailpit o de tools/smtp_sink.py)
"""
import base64
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone

GATEWAY = os.environ.get("GATEWAY_URL")
AUTH = GATEWAY or os.environ.get("AUTH_URL", "http://localhost:8003")
AIRPORT = GATEWAY or os.environ.get("AIRPORT_URL", "http://localhost:8001")
ITIN = GATEWAY or os.environ.get("ITINERARY_URL", "http://localhost:8002")
NOTIF_SQL = os.environ.get(
    "NOTIF_SQL_CMD", "docker compose exec -T postgres-notification psql -U notif -d notification -tAc")
ITIN_SQL = os.environ.get(
    "ITIN_SQL_CMD", "docker compose exec -T postgres-itinerary psql -U itinerary -d itinerary -tAc")
MGMT = os.environ.get("RABBIT_MGMT_URL", "http://localhost:15672")
MAILPIT = os.environ.get("MAILPIT_URL", "http://localhost:8025")
TOMORROW = (datetime.now(timezone.utc) + timedelta(days=1)).date().isoformat()
IN_30_DAYS = (datetime.now(timezone.utc) + timedelta(days=30)).date().isoformat()
# Salida en ~10 h (el aviso de 24 h ya esta vencido -> se envia de inmediato) y una salida a las 15:00 de Colombia.
SOON = (datetime.now(timezone.utc) + timedelta(hours=10)).replace(microsecond=0).isoformat()
DEP_30 = f"{IN_30_DAYS}T15:00:00-05:00"
RB_USER, RB_PASS = os.environ.get("RABBIT_USER"), os.environ.get("RABBIT_PASS")

results = []


def step(name, ok, detail="", skip=False):
    status = "SKIP" if skip else ("PASS" if ok else "FAIL")
    results.append((name, status))
    print(f"[{status}] {name}" + (f" - {detail}" if detail else ""), flush=True)
    return ok


def http(method, url, body=None, token=None, basic=None, timeout=15):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if basic:
        headers["Authorization"] = "Basic " + base64.b64encode(f"{basic[0]}:{basic[1]}".encode()).decode()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw.decode(errors="replace")
    except (urllib.error.URLError, OSError) as e:
        return 0, str(e)


def uid(value: str) -> str:
    """Valida que el id sea un UUID antes de interpolarlo en SQL de prueba
    (los ids vienen de nuestra propia API; esto evita cualquier inyeccion)."""
    import uuid as _uuid
    return str(_uuid.UUID(str(value)))


def sql(cmd, query):
    out = subprocess.run(shlex.split(cmd) + [query], capture_output=True, text=True, timeout=30)
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def wait_for(fn, timeout=40, every=1.0):
    end = time.time() + timeout
    while time.time() < end:
        v = fn()
        if v:
            return v
        time.sleep(every)
    return None


def main():
    user = f"demo-{uuid.uuid4().hex[:6]}"

    for name, base in (("auth-stub", AUTH), ("airport-service", AIRPORT), ("itinerary-service", ITIN)):
        if not GATEWAY:
            code, _ = http("GET", f"{base}/health")
            step(f"{name} /health", code == 200, f"HTTP {code}")

    code, body = http("POST", f"{AUTH}/api/auth/token", {"username": user, "email": f"{user}@example.com"})
    token = body.get("access_token") if code == 200 and isinstance(body, dict) else None
    if not step("1. Login (POST /api/auth/token) devuelve JWT", bool(token), f"HTTP {code}"):
        return finish()

    code, airports = http("GET", f"{AIRPORT}/api/airports")
    ok = code == 200 and isinstance(airports, list) and len(airports) >= 2
    if not step("2. GET /api/airports devuelve >= 2 aeropuertos", ok, f"HTTP {code}, n={len(airports) if ok else '-'}"):
        return finish()
    origin, dest = airports[0], airports[1]

    code, _ = http("GET", f"{ITIN}/api/itineraries")
    step("3. Sin token, GET /api/itineraries se rechaza (401/403)", code in (401, 403), f"HTTP {code}")

    payload = {"nombre_usuario": user, "origin_airport_id": origin["id"],
               "destination_airport_id": dest["id"], "departure_at": SOON, "duration_minutes": 75}
    code, created = http("POST", f"{ITIN}/api/itineraries", payload, token)
    itin_id = created.get("id") if code == 201 and isinstance(created, dict) else None
    if not step("4. POST /api/itineraries -> 201 con id", bool(itin_id), f"HTTP {code}"):
        return finish()

    code, detail = http("GET", f"{ITIN}/api/itineraries/{itin_id}", token=token)
    step("5. GET detalle del itinerario persistido", code == 200 and detail["origin"]["iata_code"] == origin["iata_code"],
         f"HTTP {code}")

    _, other = http("POST", f"{AUTH}/api/auth/token", {"username": user + "-intruso"})
    code, _ = http("GET", f"{ITIN}/api/itineraries/{itin_id}", token=other["access_token"])
    step("6. Otro usuario no ve el itinerario (anti-IDOR)", code == 404, f"HTTP {code}")

    code, _ = http("POST", f"{ITIN}/api/itineraries", {**payload, "destination_airport_id": origin["id"]}, token)
    step("7. Origen == destino se rechaza (422)", code == 422, f"HTTP {code}")

    # --- Evento -> outbox -> RabbitMQ -> consumidor -> notification_history
    if sql(ITIN_SQL, "SELECT 1") is None:
        step("8. Evento en outbox pasa a PUBLISHED", False, "no pude consultar la BD (define ITIN_SQL_CMD)", skip=True)
    else:
        outbox = wait_for(
            lambda: sql(ITIN_SQL, f"SELECT status FROM outbox WHERE aggregate_id='{uid(itin_id)}'") == "PUBLISHED", 30)  # nosec B608
        step("8. Evento en outbox pasa a PUBLISHED (relay -> RabbitMQ con confirm)", bool(outbox))

    if sql(NOTIF_SQL, "SELECT 1") is None:
        step("9. notification_history registra la notificacion", False, "no pude consultar la BD (define NOTIF_SQL_CMD)", skip=True)
    else:
        row = wait_for(lambda: sql(NOTIF_SQL, f"SELECT status||'/'||channel FROM notification_history WHERE itinerary_id='{uid(itin_id)}'"), 40)  # nosec B608
        step("9. notification_history registra la notificacion (consumidor)", bool(row), f"fila={row}")

    # --- Idempotencia y DLQ via management API (publica mensajes de prueba)
    if RB_USER and RB_PASS:
        pub = f"{MGMT}/api/exchanges/%2F/amq.default/publish"
        msg = {"itinerary_id": itin_id, "nombre_usuario": user,
               "origin": origin["iata_code"], "destination": dest["iata_code"], "travel_date": TOMORROW}
        http("POST", pub, {"properties": {"type": "ItineraryCreatedEvent", "message_id": "1"},
                           "routing_key": "itinerary.events", "payload": json.dumps(msg),
                           "payload_encoding": "string"}, basic=(RB_USER, RB_PASS))
        time.sleep(4)
        if sql(NOTIF_SQL, "SELECT 1") is not None:
            n = sql(NOTIF_SQL, f"SELECT count(*) FROM notification_history WHERE itinerary_id='{uid(itin_id)}'")  # nosec B608
            step("10. Reentrega duplicada NO crea una 2a notificacion (idempotencia)", n == "1", f"filas={n}")
        else:
            step("10. Idempotencia ante reentrega", False, "sin acceso a la BD", skip=True)
        http("POST", pub, {"properties": {}, "routing_key": "itinerary.events", "payload": "esto-no-es-json",
                           "payload_encoding": "string"}, basic=(RB_USER, RB_PASS))

        def dlq_count():
            c, q = http("GET", f"{MGMT}/api/queues/%2F/itinerary.events.dlq", basic=(RB_USER, RB_PASS))
            return q.get("messages", 0) if c == 200 and isinstance(q, dict) else 0
        n = wait_for(dlq_count, 20)
        step("11. Mensaje invalido va a la dead-letter queue (no se reencola)", bool(n), f"mensajes en DLQ={n}")
    else:
        step("10-11. Idempotencia y DLQ via RabbitMQ", False, "define RABBIT_USER/RABBIT_PASS", skip=True)

    # --- Sprint 6: recordatorios (viaje manana + 24 h de antelacion = vence ya)
    email = f"{user}@example.com"
    if sql(NOTIF_SQL, "SELECT 1") is None:
        step("12-15. Recordatorios", False, "sin acceso a la BD", skip=True)
    else:
        sent = wait_for(lambda: sql(NOTIF_SQL, f"SELECT status FROM reminders WHERE itinerary_id='{uid(itin_id)}'") == "SENT", 60)  # nosec B608
        step("12. El recordatorio vencido se envia (reminders.status = SENT)", bool(sent))
        code, inbox = http("GET", f"{MAILPIT}/api/v1/messages")
        if code != 200:
            step("13. El correo llega al buzon SMTP (Mailpit)", False, f"sin acceso a {MAILPIT}", skip=True)
        else:
            mine = [m for m in inbox.get("messages", []) if any(t["Address"] == email for t in m["To"])]
            step("13. El correo llega al buzon SMTP (exactamente 1, sin duplicados)", len(mine) == 1,
                 f"mensajes para {email}: {len(mine)}")
        code, _ = http("PUT", f"{ITIN}/api/itineraries/{itin_id}", {"departure_at": DEP_30}, token)
        moved = code == 200 and wait_for(lambda: sql(
            NOTIF_SQL, f"SELECT travel_date||'/'||status FROM reminders WHERE itinerary_id='{uid(itin_id)}'") == f"{IN_30_DAYS}/PENDING", 30)  # nosec B608
        step("14. Editar fecha/hora reprograma el recordatorio (PENDING, nueva fecha)", bool(moved), f"PUT HTTP {code}")

    # --- Agenda del viajero: el vuelo ahora es origen->destino, 15:00-16:15 (Colombia) en +30 dias
    if len(airports) >= 3:
        third = airports[2]

        def fly(frm, to, hhmm, minutes=60):
            return http("POST", f"{ITIN}/api/itineraries", {
                "nombre_usuario": user, "origin_airport_id": frm["id"], "destination_airport_id": to["id"],
                "departure_at": f"{IN_30_DAYS}T{hhmm}:00-05:00", "duration_minutes": minutes}, token)
        code, body = fly(third, origin, "15:30")
        step("18. Vuelo que se cruza con otro tuyo (en pleno vuelo, otra ciudad) -> 409 OVERLAP",
             code == 409 and body.get("code") == "OVERLAP", f"HTTP {code} {body.get('code') if isinstance(body, dict) else ''}")
        code, body = fly(third, origin, "17:00")
        step("19. Salir de una ciudad donde no aterrizaste -> 409 ORIGIN_MISMATCH",
             code == 409 and body.get("code") == "ORIGIN_MISMATCH", f"HTTP {code} {body.get('code') if isinstance(body, dict) else ''}")
        code, body = fly(dest, origin, "16:15")
        ok_id = body.get("id") if code == 201 and isinstance(body, dict) else None
        step("20. Salir desde la ciudad de llegada justo al aterrizar (16:15) -> 201", bool(ok_id), f"HTTP {code}")
        if ok_id:
            http("DELETE", f"{ITIN}/api/itineraries/{ok_id}", token=token)
        code, lst = http("GET", f"{ITIN}/api/itineraries", token=token)
        step("21. El listado expone salida y llegada calculada", code == 200 and bool(lst) and bool(lst[0].get("arrival_at")) and bool(lst[0].get("departure_at")), f"HTTP {code}")
    else:
        step("18-21. Agenda del viajero", False, "se requieren >= 3 aeropuertos", skip=True)

    code, _ = http("DELETE", f"{ITIN}/api/itineraries/{itin_id}", token=token)
    step("15. DELETE /api/itineraries/{id} -> 204", code == 204, f"HTTP {code}")
    if sql(NOTIF_SQL, "SELECT 1") is not None:
        gone = wait_for(lambda: sql(
            NOTIF_SQL, f"SELECT status||'/'||coalesce(email,'sin-email') FROM reminders WHERE itinerary_id='{uid(itin_id)}'") == "CANCELLED/sin-email", 30)  # nosec B608
        step("16. Borrar cancela el recordatorio y elimina el correo (PII)", bool(gone))
    code, _ = http("GET", f"{ITIN}/api/itineraries/{itin_id}", token=token)
    step("17. El itinerario borrado ya no existe (404)", code == 404, f"HTTP {code}")
    return finish()


def finish():
    fails = [n for n, s in results if s == "FAIL"]
    skips = [n for n, s in results if s == "SKIP"]
    print(f"\nResumen: {sum(s == 'PASS' for _, s in results)} PASS, {len(fails)} FAIL, {len(skips)} SKIP")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
