"""Prueba de carga (Locust) contra Airport Service — escenarios definidos
en Plan_de_Pruebas.docx seccion 4.
Ejecutar: locust -f tests/load/locustfile.py --host=http://localhost:8001
"""
from locust import HttpUser, task, between


class AirportServiceUser(HttpUser):
    wait_time = between(0.5, 2.0)

    @task(3)
    def list_airports(self):
        self.client.get("/api/airports")

    @task(1)
    def get_airport_detail(self):
        self.client.get("/api/airports/1")

    @task(1)
    def health(self):
        self.client.get("/health")
