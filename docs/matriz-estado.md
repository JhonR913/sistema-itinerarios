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

## Sprint 2 — Itinerary Service

| Ítem | Estado | Evidencia |
|---|---|---|
| RF-004 a RF-010 | Implementado | `app/application/use_cases.py` |
| Patrón Outbox (Double Write Problem) | Implementado | `outbox_publisher.py` + `outbox_worker.py` |
| Adapter HTTP a Airport Service + Circuit Breaker | Implementado | `airport_http_adapter.py` |
| RNF-SEC-006 (anti-IDOR) | Implementado y probado | `test_UT008...` |
| RNF-SEC-007 (anti mass-assignment) | Implementado y probado | `test_UT010...` |
| RNF-SEC-004 (sin SQL concatenado) | Implementado | `postgres_repository.py`, 100% `text()` parametrizado |
| Composition root limpia desde el inicio | Implementado | `dependencies.py`, lección del audit de Sprint 1 aplicada sin parche posterior |
| UT-004 a UT-011 + 2 complementarias | **Ejecutadas — 10/10 PASS** | `pytest tests/unit -v` |
| Pruebas de carga | Diseñadas, no ejecutadas aún | `tests/load/locustfile.py` |
| Docker | Escrito, no verificado end-to-end (sin Docker en este entorno) | `Dockerfile` + `docker-compose.yml` |

## Sprint 3 — Notification Function + Gateway + conexión RabbitMQ real

| Ítem | Estado | Evidencia |
|---|---|---|
| RF-012 Procesar notificación | Implementado | `services/notification-function/handler.py` |
| Idempotencia ante reentrega (at-least-once) | Implementado y probado | `tests/unit/test_handler.py` — 2/2 PASS (inserta 1ra vez, ignora duplicado) |
| Conexión real a RabbitMQ | Implementado | `consumer.py` (pika, basic_consume + ack/nack) |
| RabbitMQ como pieza compartida (un solo broker) | Verificado | Declarado una vez en `itinerary-service/docker-compose.yml`, referenciado desde `notification-function` vía `depends_on` + misma red `itinerarios-net` |
| API Gateway (Traefik) | Implementado | `gateway/traefik/` — routing + rate limiting, sin lógica de negocio |
| docker-compose raíz (monorepo) | Implementado | `docker-compose.yml` con `include:` de los 4 sub-compose |
| Validación de sintaxis de los 6 YAML (compose + Traefik) | **Verificada — 6/6 OK** | `python3 -c "import yaml; yaml.safe_load(...)"` sobre cada archivo |
| `docker compose up` end-to-end real | **No verificado** | Este entorno no tiene Docker instalado; pendiente de correrlo en tu máquina (ver sección "Cómo levantar todo" en el README) |

## Resumen de pruebas unitarias ejecutadas hasta ahora

- Airport Service: 4/4 PASS
- Itinerary Service: 10/10 PASS
- Notification Function: 2/2 PASS
- **Total: 16/16 PASS**, en los 3 servicios Python del sistema.
