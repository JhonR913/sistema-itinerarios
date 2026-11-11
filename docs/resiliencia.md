# Resiliencia: fallos y latencia (Sprint 9)

## Herramienta
`tools/fault_proxy.py` — proxy TCP con API de administración (solo biblioteca estándar).
Se eligió en lugar de Toxiproxy/Testcontainers porque **no se pudo descargar Toxiproxy ni usar
Docker** en el entorno de trabajo, y esto cubre lo necesario con cero dependencias. Modos por
puerto, cambiables en caliente: `pass`, `latency`, `drop` (corta también conexiones ya
abiertas), `blackhole` (acepta y nunca responde).

## Escenarios (`scripts/e2e_faults.py`, resultado: `evidencias/e2e-faults.txt`)
| # | Fallo inyectado | Comportamiento verificado |
|---|---|---|
| A1 | Airport Service con 6 s de latencia (timeout del cliente: 2 s, 2 intentos) | `POST /api/itineraries` → **502** en ~5 s (acotado) |
| A2 | tras 3 fallos | circuito **abierto**: 502 en milisegundos, sin llamar a la red |
| A3 | idem | `GET /api/itineraries` (no depende de Airport) sigue en 200 |
| A4 | se quita la latencia | pasados 30 s (half-open) el POST vuelve a **201**, sin reiniciar |
| B1/B2 | PostgreSQL de itinerarios cae (conexiones cortadas) | **503** + `Retry-After` (antes: 500); el POST no deja datos a medias |
| B3 | vuelve la BD | 200 sin reiniciar (`pool_pre_ping`) |
| B4 | BD que acepta TCP y no responde | 503 en ~8 s: `connect_timeout=3`, `statement_timeout=5 s`, `pool_timeout=5 s` |
| C1 | Redis caído | aeropuertos 200 (la caché falla "abierta": cache miss) |
| D1 | proveedor externo caído + Redis vacío | 200 desde PostgreSQL (3.er nivel de resiliencia) |

Además, ya cubiertos antes: caída de RabbitMQ (`scripts/e2e_resilience.py`) y pruebas unitarias del
circuit breaker (`tests/unit/test_airport_adapter.py`, `test_adapter_resilience.py`).

## Defectos que esta fase encontró y corrigió
1. El **primer** fallo de Airport (timeout) devolvía **500**: el `RetryError` de tenacity no se traducía a 502 (solo el circuito abierto lo hacía).
2. Sin `connect_timeout`, una BD que no responde dejaba la petición colgada indefinidamente.
3. BD caída → 500 genérico; ahora 503 con `Retry-After`.
4. Con PostgreSQL de aeropuertos caído, una respuesta válida del proveedor se perdía (500) al fallar el `upsert` del respaldo; ahora se sirve igual.
5. Timeout de Airport 3 s × 3 intentos (≈ 11 s) → 2 s × 2 intentos (≈ 5 s, configurable `AIRPORT_HTTP_TIMEOUT_SECONDS`).

## Reproducir
Nativo: levantar los servicios apuntando a los puertos del proxy (ver `scripts/` del README y
`docker-compose.faults.yml`) y `python3 scripts/e2e_faults.py`. En Compose: `docker-compose.faults.yml`
(**sin validar en Docker**: solo `docker compose config`).

## Límites
Single-node, un solo proxy, sin pérdida de paquetes ni particiones parciales; el circuit breaker es por
proceso (cada réplica tiene el suyo). Sin Testcontainers.
