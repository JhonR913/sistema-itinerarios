"""Prueba de carga (Locust) de Airport Service - Plan_de_Pruebas.docx sec. 4.

Mezcla de operaciones REALES de lectura (lo que hace el frontend):
  - listar aeropuertos        (peso 6)  -> cache Redis tras la 1a llamada
  - detalle de un aeropuerto  (peso 3)  -> usa IDs reales obtenidos al iniciar
  - detalle inexistente       (peso 1)  -> 404 esperado, no cuenta como error
  - /health                   (peso 1)

Ejecucion headless reproducible (ver docs/pruebas-de-carga.md):
  locust -f services/airport-service/tests/load/locustfile.py --host=http://localhost:8001 \
         --headless -u 50 -r 10 -t 60s --csv=docs/evidencias/locust/airport --html=docs/evidencias/locust/airport.html
"""
import random

from locust import HttpUser, between, task


class AirportServiceUser(HttpUser):
    wait_time = between(0.2, 1.0)
    airport_ids = ["1"]

    def on_start(self):
        with self.client.get("/api/airports", name="/api/airports [setup]", catch_response=True) as r:
            if r.status_code == 200 and r.json():
                self.airport_ids = [a["id"] for a in r.json()]
            else:
                r.failure(f"no se pudo obtener aeropuertos: HTTP {r.status_code}")

    @task(6)
    def list_airports(self):
        self.client.get("/api/airports", name="/api/airports")

    @task(3)
    def get_airport_detail(self):
        self.client.get(f"/api/airports/{random.choice(self.airport_ids)}", name="/api/airports/{id}")

    @task(1)
    def get_unknown_airport(self):
        with self.client.get("/api/airports/no-existe", name="/api/airports/{id} [404 esperado]",
                             catch_response=True) as r:
            r.success() if r.status_code == 404 else r.failure(f"esperaba 404, obtuvo {r.status_code}")

    @task(1)
    def health(self):
        self.client.get("/health")
