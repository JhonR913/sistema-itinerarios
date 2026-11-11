# Pruebas de carga (Locust 2.31.5)

Resultados **reales** de las ejecuciones del 2026-11-04 (repetidas tras la agenda del viajero y la actualización de dependencias); CSV y HTML completos en
`docs/evidencias/locust/`. Tiempos en milisegundos.

## Qué se midió
Escenarios con el flujo real de un usuario (no tokens inventados):
- `services/airport-service/tests/load/locustfile.py`: listar aeropuertos (peso 6), detalle por id real (3), id inexistente → 404 esperado (1), `/health` (1).
- `services/itinerary-service/tests/load/locustfile.py`: cada usuario virtual obtiene **su propio JWT** en `auth-stub`, lee aeropuertos reales y ejecuta crear (3) / listar (5) / detalle (3) / actualizar (1) / borrar (1) **solo sobre sus itinerarios**; cada usuario encadena vuelos coherentes con la regla de agenda (cada uno sale desde donde aterrizó el anterior), por lo que cada creación también ejecuta la validación de agenda con su bloqueo por usuario. Cada creación recorre toda la cadena: PostgreSQL + outbox → RabbitMQ → notificación.
- Un fallo = respuesta distinta de la esperada (p. ej. POST ≠ 201). Los 404 de `[404 esperado]` cuentan como éxito.

## Resultados
| Perfil | Carga | Peticiones | Fallos | Throughput (req/s) | p50 | p95 | p99 | máx (ms) |
|---|---|---|---|---|---|---|---|---|
| Airport · nominal | 50 usuarios, rampa 10/s, 60 s | 4805 | 0 | 81.4 | 3 | 6 | 18 | 58 |
| Airport · alta | 300 usuarios, rampa 30/s, 60 s | 27219 | 0 | 460.6 | 6 | 32 | 71 | 270 |
| Itinerary · nominal | 30 usuarios, rampa 5/s, 90 s | 2779 | 0 | 31.2 | 7 | 18 | 29 | 43 |
| Itinerary · alta | 100 usuarios, rampa 10/s, 90 s | 8979 | 0 | 100.7 | 12 | 46 | 83 | 202 |

Detalle por endpoint:

**Airport · nominal** (50 usuarios, rampa 10/s, 60 s)

| Endpoint | Método | Peticiones | Fallos | p50 | p95 | p99 |
|---|---|---|---|---|---|---|
| `/api/airports` | GET | 2600 | 0 | 3 | 5 | 14 |
| `/api/airports [setup]` | GET | 50 | 0 | 20 | 31 | 38 |
| `/api/airports/{id}` | GET | 1270 | 0 | 3 | 5 | 11 |
| `/api/airports/{id} [404 esperado]` | GET | 468 | 0 | 3 | 5 | 11 |
| `/health` | GET | 417 | 0 | 2 | 4 | 8 |

**Airport · alta** (300 usuarios, rampa 30/s, 60 s)

| Endpoint | Método | Peticiones | Fallos | p50 | p95 | p99 |
|---|---|---|---|---|---|---|
| `/api/airports` | GET | 14525 | 0 | 6 | 28 | 60 |
| `/api/airports [setup]` | GET | 300 | 0 | 66 | 120 | 130 |
| `/api/airports/{id}` | GET | 7531 | 0 | 6 | 29 | 61 |
| `/api/airports/{id} [404 esperado]` | GET | 2466 | 0 | 6 | 28 | 65 |
| `/health` | GET | 2397 | 0 | 4 | 19 | 44 |

**Itinerary · nominal** (30 usuarios, rampa 5/s, 90 s)

| Endpoint | Método | Peticiones | Fallos | p50 | p95 | p99 |
|---|---|---|---|---|---|---|
| `/api/itineraries` | GET | 1084 | 0 | 6 | 12 | 19 |
| `/api/itineraries` | POST | 666 | 0 | 14 | 26 | 37 |
| `/api/itineraries/{id}` | DELETE | 223 | 0 | 7 | 13 | 20 |
| `/api/itineraries/{id}` | GET | 595 | 0 | 6 | 11 | 16 |
| `/api/itineraries/{id}` | PUT | 211 | 0 | 10 | 18 | 23 |

**Itinerary · alta** (100 usuarios, rampa 10/s, 90 s)

| Endpoint | Método | Peticiones | Fallos | p50 | p95 | p99 |
|---|---|---|---|---|---|---|
| `/api/itineraries` | GET | 3591 | 0 | 9 | 32 | 58 |
| `/api/itineraries` | POST | 2119 | 0 | 22 | 66 | 110 |
| `/api/itineraries/{id}` | DELETE | 682 | 0 | 10 | 33 | 53 |
| `/api/itineraries/{id}` | GET | 1927 | 0 | 9 | 31 | 62 |
| `/api/itineraries/{id}` | PUT | 660 | 0 | 17 | 57 | 97 |

**Cadena asíncrona bajo carga** (`docs/evidencias/locust/outbox-backlog.txt`): tras el perfil
*Itinerary · alta* quedaban 41 eventos PENDING en el outbox justo al terminar y 0 quince segundos después; todos
se publicaron y consumieron (cola sin acumulación).

## Hallazgo que corrigió el código
En la primera ejecución del perfil de itinerarios, el relay del outbox **dejó 1035 eventos
PENDING** al terminar (medido: drenaba exactamente 10 eventos/s porque dormía 2 s tras cada
lote de 20, y la creación bajo carga superaba ese ritmo). Se corrigió (`outbox_worker.run`: no
dormir si el lote vino lleno; prueba de regresión en `tests/integration`) y se repitió la
medición: los resultados de arriba son **posteriores** al fix. Las peticiones HTTP de la
primera corrida no mostraron fallos; el problema era el retraso de las notificaciones, no
visible en las métricas HTTP.

## Condiciones y límites (leer antes de citar los números)
- **Todo en una sola máquina virtual de 2 vCPU / 8 GB**: generador de carga, 3 servicios FastAPI
  (uvicorn, 1 worker c/u), PostgreSQL 16, Redis, RabbitMQ 3.12 (no 4.1) y el relay/consumidor
  compiten por CPU. Procesos nativos, **no contenedores** y **sin Traefik**.
- Aeropuertos servidos por el **mock local** (`tools/mock_api_colombia.py`), no por API Colombia:
  la latencia con el proveedor real sería distinta en la primera consulta (luego responde la caché Redis).
- Los perfiles «alta» **no llegaron a saturar** los servicios (el throughput está limitado por los
  tiempos de espera de los usuarios virtuales); no se determinó el punto de saturación.
- Prueba contra puertos directos. Por el gateway, el rate limit de Traefik (20 req/s, burst 40
  por IP) devolvería 429 por diseño.
- Una sola ejecución por perfil: sin repeticiones ni intervalos de confianza.

## Cómo reproducir
```bash
pip install -r requirements-load.txt
# sistema levantado (Compose o nativo) y AUTH_URL / AIRPORT_URL si no son los puertos por defecto
locust -f services/airport-service/tests/load/locustfile.py   --host=http://localhost:8001 --headless -u 50  -r 10 -t 60s --csv=docs/evidencias/locust/airport-nominal   --html=docs/evidencias/locust/airport-nominal.html
locust -f services/airport-service/tests/load/locustfile.py   --host=http://localhost:8001 --headless -u 300 -r 30 -t 60s --csv=docs/evidencias/locust/airport-alta      --html=docs/evidencias/locust/airport-alta.html
locust -f services/itinerary-service/tests/load/locustfile.py --host=http://localhost:8002 --headless -u 30  -r 5  -t 90s --csv=docs/evidencias/locust/itinerary-nominal --html=docs/evidencias/locust/itinerary-nominal.html
locust -f services/itinerary-service/tests/load/locustfile.py --host=http://localhost:8002 --headless -u 100 -r 10 -t 90s --csv=docs/evidencias/locust/itinerary-alta    --html=docs/evidencias/locust/itinerary-alta.html
# backlog del outbox al terminar:
docker compose exec postgres-itinerary psql -U itinerary -d itinerary -c "select status,count(*) from outbox group by 1"
```
