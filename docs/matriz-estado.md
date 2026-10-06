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

## Revisión post-Sprint 1 — verificación de Arquitectura Hexagonal

Se verificó con `grep` real (no solo lectura de comentarios) la dirección
de dependencias de las 4 capas de Airport Service: `domain` no importa
nada externo, `application` solo importa `domain`, `infrastructure/adapters`
implementa los puertos del dominio, `infrastructure/api` depende hacia
adentro. **Confirmado: Hexagonal correctamente aplicado.**

Único ajuste aplicado: `routes.py` construía directamente los adaptadores
concretos (`ApiColombiaAdapter`, `RedisAirportCache`), mezclando
composition root con la capa de traducción HTTP. Se extrajo a
`app/infrastructure/api/dependencies.py` y se inyecta vía `Depends()` de
FastAPI. No era una violación de la regla de dependencia, pero sí
incumplía la propia regla del `CLAUDE.md` de no mezclar responsabilidades
en el router. Pruebas re-ejecutadas tras el cambio: **4/4 PASS**.
