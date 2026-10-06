# Matriz de estado — implementación real (se actualiza por sprint)

A diferencia de la Matriz_Cumplimiento.docx de la fase documental (que
describe diseño), este archivo vive en el código y solo registra lo que
ya se implementó y se verificó ejecutando algo.

## Sprint 1 — Airport Service

| Ítem | Estado | Evidencia |
|---|---|---|
| RF-001 Listar aeropuertos | Implementado | `app/application/use_cases.py::ListAirports` |
| RF-002 Consultar por ID | Implementado | `app/application/use_cases.py::GetAirportById` |
| RF-016 Cache Redis | Implementado | `app/infrastructure/adapters/redis_cache.py` |
| RF-017 Circuit Breaker | Implementado | `app/infrastructure/adapters/api_colombia_adapter.py` |
| Patrón Adapter | Implementado | `app/infrastructure/adapters/api_colombia_adapter.py` |
| RNF-SEC-001 (sin secretos en código) | Implementado | `.env.example` + `.gitignore`, sin valores reales en el repo |
| RNF-SEC-008 (sin stack trace en prod) | Implementado | `app/infrastructure/api/error_handlers.py` |
| UT-001, UT-002, UT-003 | **Ejecutadas — 4/4 PASS** | `pytest tests/unit -v` (ver commit de este sprint) |
| Pruebas de carga | Diseñadas, no ejecutadas aún | `tests/load/locustfile.py` (requiere el servicio desplegado) |
| Swagger | Implementado (automático) | FastAPI expone `/docs` sin configuración adicional |
| Docker | Implementado | `Dockerfile` + `docker-compose.yml` (no verificado con `docker compose up` real en este entorno) |

## Sprint 2 — Itinerary Service

| Ítem | Estado | Evidencia |
|---|---|---|
| RF-004/005/006 Crear, validar aeropuertos y rechazar salida = llegada | Implementado | `app/application/use_cases.py::ItineraryService.create` |
| RF-007/008/009 Consultar, actualizar y eliminar | Implementado | `ItineraryService.get/list/update/delete` |
| ADR-006 / RN-007 Snapshot inmutable de aeropuertos | Implementado | `domain/models.py::AirportSnapshot`, columnas `*_iata/_name/_city` |
| RF-010 / RN-006 Evento `ItineraryCreatedEvent` en Outbox (misma transacción) | Implementado | `adapters/sqlalchemy_repository.py::add`, tabla `outbox` (PENDING) |
| Anti-IDOR y anti mass-assignment | Implementado | `_get_owned`, `ItineraryUpdate(extra="forbid")` |
| URL del Airport Service con `/api` | Corregido | `infrastructure/config.py`, `.env.example` |
| Pruebas | **26/26 PASS** | `pytest` en `services/itinerary-service` |
| Autenticación | Placeholder (header `X-User-Name`) | Pendiente US-010 (JWT) |
| Worker que publica el Outbox en RabbitMQ | Pendiente | US-008 |
| PostgreSQL + Alembic | Pendiente (hoy SQLite con `create_all`) | ADR-001 |
| Retry / backoff / Circuit Breaker hacia Airport Service, 502 | Pendiente | RNF-05 |
| docker-compose + healthcheck de Itinerary Service | Pendiente | RNF-07, RNF-15 |

Nota: al cambiar el esquema (columnas de snapshot y tabla `outbox`) hay que borrar la base SQLite
local anterior (`itineraries.db`) porque `create_all` no altera tablas existentes.
