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

## Pendiente para el siguiente sprint (Sprint 2 — Itinerary Service)

Ver jira/backlog.csv, épica "Gestión de Itinerarios" (US-004 a US-007).
