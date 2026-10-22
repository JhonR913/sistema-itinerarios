import os
from locust import HttpUser, task, between

TEST_JWT = os.environ.get("TEST_JWT", "invalid-token-for-smoke-test")


class ItineraryServiceUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.headers = {"Authorization": f"Bearer {TEST_JWT}"}

    @task(3)
    def list_itineraries(self):
        self.client.get("/api/itineraries", headers=self.headers)

    @task(1)
    def create_itinerary(self):
        self.client.post("/api/itineraries", headers=self.headers, json={
            "nombre_usuario": "carga-test",
            "origin_airport_id": "1",
            "destination_airport_id": "2",
            "travel_date": "2026-12-01",
            "duration_minutes": 90,
        })
