#!/usr/bin/env python3
"""Mock MINIMO de API Colombia (GET /api/v1/Airport) para ejecutar el
sistema SIN internet: pruebas de humo, Locust y demos offline.

ATENCION: son DATOS DE PRUEBA (IATA reales, coordenadas aproximadas), no la
respuesta del servicio real. Los resultados de carga medidos contra este mock
NO representan la latencia de API Colombia. Apuntar el servicio con:
    API_COLOMBIA_BASE_URL=http://localhost:9000/api/v1

Uso:  python3 tools/mock_api_colombia.py [puerto=9000]
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AIRPORTS = [
    (1, "BOG", "Aeropuerto Internacional El Dorado", "Bogotá", 4.7016, -74.1469),
    (2, "MDE", "Aeropuerto Internacional José María Córdova", "Rionegro", 6.1645, -75.4231),
    (3, "CTG", "Aeropuerto Internacional Rafael Núñez", "Cartagena", 10.4424, -75.5130),
    (4, "CLO", "Aeropuerto Internacional Alfonso Bonilla Aragón", "Cali", 3.5432, -76.3816),
    (5, "BAQ", "Aeropuerto Internacional Ernesto Cortissoz", "Barranquilla", 10.8896, -74.7808),
    (6, "BGA", "Aeropuerto Internacional Palonegro", "Bucaramanga", 7.1265, -73.1848),
    (7, "SMR", "Aeropuerto Internacional Simón Bolívar", "Santa Marta", 11.1196, -74.2306),
    (8, "PEI", "Aeropuerto Internacional Matecaña", "Pereira", 4.8127, -75.7395),
    (9, "ADZ", "Aeropuerto Internacional Gustavo Rojas Pinilla", "San Andrés", 12.5836, -81.7112),
    (10, "CUC", "Aeropuerto Internacional Camilo Daza", "Cúcuta", 7.9276, -72.5115),
]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        if self.path.rstrip("/") == "/api/v1/Airport":
            body = json.dumps([
                {"id": i, "name": n, "iataCode": c, "latitude": la, "longitude": lo,
                 "city": {"id": i, "name": city}}
                for i, c, n, city, la, lo in AIRPORTS
            ]).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        else:
            body = b'{"error":"not found"}'
            self.send_response(404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):  # silencioso
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9000
    print(f"mock API Colombia en http://0.0.0.0:{port}/api/v1/Airport (DATOS DE PRUEBA)", flush=True)  # nosec B104
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()  # nosec B104
