#!/usr/bin/env python3
"""Pruebas de FALLOS y LATENCIA sobre el sistema en ejecucion (Sprint 9).

Requiere que los servicios apunten a sus dependencias A TRAVES de
tools/fault_proxy.py (ver docs/resiliencia.md y docker-compose.faults.yml):
  itinerary -> airport-service         via proxy  (puerto FAULT_AIRPORT_PORT)
  itinerary -> postgres-itinerary      via proxy  (FAULT_DB_PORT)
  airport   -> redis-airport           via proxy  (FAULT_REDIS_PORT)
  airport   -> API de aeropuertos      via proxy  (FAULT_UPSTREAM_PORT)

Escenarios (cada uno verifica el comportamiento y la RECUPERACION):
  A. Airport lento (> timeout)        -> 502 acotado en tiempo; circuito abierto responde al instante; se recupera
  B. PostgreSQL de itinerarios caido   -> 503 (no 500); se recupera sin reiniciar
  C. Redis caido                       -> aeropuertos siguen respondiendo (200)
  D. Proveedor externo caido + Redis vacio -> respaldo PostgreSQL (200)
Variables: FAULT_ADMIN_URL (def. http://localhost:8099), AUTH_URL, ITINERARY_URL, AIRPORT_URL,
           REDIS_FLUSH_CMD (def. 'docker compose exec -T redis-airport redis-cli flushall'),
           BREAKER_RESET_SECONDS (def. 32)
"""
import os
import shlex
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import e2e_smoke as e  # noqa: E402

ADMIN = os.environ.get("FAULT_ADMIN_URL", "http://localhost:8099")
P_AIRPORT = os.environ.get("FAULT_AIRPORT_PORT", "18001")
P_DB = os.environ.get("FAULT_DB_PORT", "15432")
P_REDIS = os.environ.get("FAULT_REDIS_PORT", "16379")
P_UP = os.environ.get("FAULT_UPSTREAM_PORT", "19000")
FLUSH = os.environ.get("REDIS_FLUSH_CMD", "docker compose exec -T redis-airport redis-cli flushall")
BREAKER_RESET = float(os.environ.get("BREAKER_RESET_SECONDS", "32"))


def fault(port, mode="pass", latency_ms=0):
    code, _ = e.http("POST", f"{ADMIN}/faults/{port}", {"mode": mode, "latency_ms": latency_ms})
    assert code == 200, f"no pude fijar el fallo en :{port} (HTTP {code})"


_n = [0]


def timed(method, url, body=None, token=None):
    if method == "POST" and url.endswith("/api/itineraries"):
        # Un viajero distinto por intento: estas pruebas miden fallos de infraestructura,
        # no la agenda (repetir el mismo vuelo daria 409 por traslape).
        _n[0] += 1
        _, t = e.http("POST", f"{e.AUTH}/api/auth/token", {"username": f"faults-{os.getpid()}-{_n[0]}"})
        token = t["access_token"]
    t0 = time.time()
    code, resp = e.http(method, url, body, token, timeout=40)
    return code, resp, time.time() - t0


def create_body(a):
    return {"nombre_usuario": "faults", "origin_airport_id": a[0]["id"], "destination_airport_id": a[1]["id"],
            "departure_at": e.DEP_30, "duration_minutes": 60}


def main():
    fault("reset")
    _, tok = e.http("POST", f"{e.AUTH}/api/auth/token", {"username": "faults"})
    token = tok["access_token"]
    code, airports = e.http("GET", f"{e.AIRPORT}/api/airports")
    if code != 200:
        e.step("Precondicion: GET /api/airports", False, f"HTTP {code}")
        return e.finish()
    body = create_body(airports)
    code, _, _ = timed("POST", f"{e.ITIN}/api/itineraries", body, token)
    e.step("Precondicion: crear itinerario sin fallos -> 201", code == 201, f"HTTP {code}")

    # ---- A. Airport Service lento -------------------------------------------------
    fault(P_AIRPORT, "latency", 6000)       # > timeout de 2 s del adaptador
    code, _, dt = timed("POST", f"{e.ITIN}/api/itineraries", body, token)
    e.step("A1. Airport lento: POST responde 502 (no cuelga) en tiempo acotado", code == 502 and dt < 12, f"HTTP {code} en {dt:.1f}s")
    for _ in range(3):
        timed("POST", f"{e.ITIN}/api/itineraries", body, token)   # acumula fallos -> abre el circuito
    code, _, dt = timed("POST", f"{e.ITIN}/api/itineraries", body, token)
    e.step("A2. Circuito ABIERTO: falla al instante sin esperar al servicio", code == 502 and dt < 1.0, f"HTTP {code} en {dt*1000:.0f} ms")
    code, _, _ = timed("GET", f"{e.ITIN}/api/itineraries", token=token)
    e.step("A3. Las operaciones que no dependen de Airport siguen funcionando (GET lista)", code == 200, f"HTTP {code}")
    fault(P_AIRPORT, "pass")
    print(f"   ... esperando {BREAKER_RESET:.0f}s a que el circuito pase a half-open", flush=True)
    time.sleep(BREAKER_RESET)
    code, _, dt = timed("POST", f"{e.ITIN}/api/itineraries", body, token)
    e.step("A4. Recuperacion: al volver Airport el POST vuelve a 201 sin reiniciar nada", code == 201, f"HTTP {code} en {dt:.1f}s")

    # ---- B. PostgreSQL de itinerarios caido ---------------------------------------
    fault(P_DB, "drop")
    code, resp, dt = timed("GET", f"{e.ITIN}/api/itineraries", token=token)
    e.step("B1. BD caida: GET responde 503 (no 500) y rapido", code == 503 and dt < 10, f"HTTP {code} en {dt:.1f}s")
    code, _, _ = timed("POST", f"{e.ITIN}/api/itineraries", body, token)
    e.step("B2. BD caida: POST responde 503 y NO deja nada a medias", code == 503, f"HTTP {code}")
    fault(P_DB, "pass")
    code, _, _ = timed("GET", f"{e.ITIN}/api/itineraries", token=token)
    e.step("B3. Recuperacion: al volver la BD, GET vuelve a 200 sin reiniciar", code == 200, f"HTTP {code}")
    fault(P_DB, "blackhole")
    code, _, dt = timed("GET", f"{e.ITIN}/api/itineraries", token=token)
    e.step("B4. BD que no responde (agujero negro): la peticion NO queda colgada indefinidamente", dt < 40, f"HTTP {code} en {dt:.1f}s")
    fault(P_DB, "pass")

    # ---- C. Redis caido ------------------------------------------------------------
    fault(P_REDIS, "drop")
    code, resp, dt = timed("GET", f"{e.AIRPORT}/api/airports")
    e.step("C1. Redis caido: aeropuertos siguen respondiendo 200 (cache = miss)", code == 200 and isinstance(resp, list) and len(resp) >= 2, f"HTTP {code} en {dt:.1f}s")
    fault(P_REDIS, "pass")

    # ---- D. Proveedor externo caido + Redis vacio ----------------------------------
    subprocess.run(shlex.split(FLUSH), capture_output=True)
    fault(P_UP, "drop")
    code, resp, dt = timed("GET", f"{e.AIRPORT}/api/airports")
    e.step("D1. Proveedor caido + Redis vacio: se sirve desde PostgreSQL (respaldo durable)", code == 200 and isinstance(resp, list) and len(resp) >= 2, f"HTTP {code} en {dt:.1f}s")
    fault(P_UP, "pass")
    fault("reset")
    return e.finish()


if __name__ == "__main__":
    sys.exit(main())
