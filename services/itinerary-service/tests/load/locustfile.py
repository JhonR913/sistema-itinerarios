"""Prueba de carga (Locust) de Itinerary Service con el flujo REAL de un usuario:

  on_start: POST /api/auth/token (auth-stub) -> JWT propio por usuario virtual
            GET  /api/airports (airport-service) -> IDs reales de aeropuertos
  tareas:   crear (peso 3) / listar (5) / detalle (3) / actualizar (1) / borrar (1)

Cada usuario virtual opera SOLO sobre sus propios itinerarios (anti-IDOR real).
Cada creacion escribe en PostgreSQL + outbox y dispara el flujo
outbox -> RabbitMQ -> notificacion, es decir ejercita toda la cadena asincrona.

Variables:  AUTH_URL (def. http://localhost:8003)  AIRPORT_URL (def. http://localhost:8001)
Host de Locust = Itinerary Service (def. http://localhost:8002).
NOTA: NO apuntar a traves de Traefik con muchos usuarios: el rate limit del
gateway (20 req/s promedio por IP, burst 40) devolveria 429 por diseno.

  locust -f services/itinerary-service/tests/load/locustfile.py --host=http://localhost:8002 \
         --headless -u 30 -r 5 -t 90s --csv=docs/evidencias/locust/itinerary --html=docs/evidencias/locust/itinerary.html
"""
import os
import random
import uuid
from datetime import datetime, timedelta, timezone

import requests
from locust import HttpUser, between, task

AUTH_URL = os.environ.get("AUTH_URL", "http://localhost:8003")
AIRPORT_URL = os.environ.get("AIRPORT_URL", "http://localhost:8001")


class ItineraryServiceUser(HttpUser):
    wait_time = between(0.3, 1.5)

    def on_start(self):
        self.username = f"locust-{uuid.uuid4().hex[:8]}"
        token = requests.post(f"{AUTH_URL}/api/auth/token", json={"username": self.username}, timeout=10)
        token.raise_for_status()
        self.headers = {"Authorization": f"Bearer {token.json()['access_token']}"}
        airports = requests.get(f"{AIRPORT_URL}/api/airports", timeout=30)
        airports.raise_for_status()
        self.airport_ids = [a["id"] for a in airports.json()]
        assert len(self.airport_ids) >= 2, "se necesitan al menos 2 aeropuertos"
        self.my_ids = []
        # Agenda coherente: cada vuelo sale desde donde aterrizo el anterior (regla del servidor).
        self.cursor_airport = random.choice(self.airport_ids)
        self.cursor_time = (datetime.now(timezone.utc) + timedelta(days=7)).replace(minute=0, second=0, microsecond=0)
        self.chain = []   # (id, aeropuerto_origen, hora_origen) para poder deshacer el ultimo vuelo
        self._pending = None

    def _body(self):
        destination = random.choice([a for a in self.airport_ids if a != self.cursor_airport])
        minutes = random.randint(61, 600)
        self._pending = (destination, self.cursor_time + timedelta(minutes=minutes + 720))
        return {"nombre_usuario": self.username, "origin_airport_id": self.cursor_airport,
                "destination_airport_id": destination,
                "departure_at": self.cursor_time.isoformat(),
                "duration_minutes": minutes}

    @task(3)
    def create_itinerary(self):
        with self.client.post("/api/itineraries", json=self._body(), headers=self.headers,
                              name="/api/itineraries", catch_response=True) as r:
            if r.status_code == 201:
                new_id = r.json()["id"]
                self.my_ids.append(new_id)
                self.chain.append((new_id, self.cursor_airport, self.cursor_time))
                self.cursor_airport, self.cursor_time = self._pending
            else:
                r.failure(f"esperaba 201, obtuvo {r.status_code}: {r.text[:120]}")

    @task(5)
    def list_itineraries(self):
        self.client.get("/api/itineraries", headers=self.headers, name="/api/itineraries")

    @task(3)
    def get_itinerary(self):
        if self.my_ids:
            self.client.get(f"/api/itineraries/{random.choice(self.my_ids)}", headers=self.headers,
                            name="/api/itineraries/{id}")

    @task(1)
    def update_itinerary(self):
        if self.my_ids:
            self.client.put(f"/api/itineraries/{random.choice(self.my_ids)}", headers=self.headers,
                            json={"duration_minutes": random.randint(30, 60)}, name="/api/itineraries/{id}")

    @task(1)
    def delete_itinerary(self):
        if self.my_ids:
            itinerary_id = self.my_ids.pop()
            _, self.cursor_airport, self.cursor_time = self.chain.pop()   # se deshace el ultimo tramo
            self.client.delete(f"/api/itineraries/{itinerary_id}", headers=self.headers,
                               name="/api/itineraries/{id}")
