# Matriz de estado — requisito → implementación → prueba → evidencia

Leyenda: ✅ **Confirmado** (ejecutado) · 🟡 **Implementado, no validado** · ⏳ **Pendiente** · 🔒 **Bloqueado** (acceso externo).
Entorno de ejecución y límites: [`evidencias/entorno.md`](evidencias/entorno.md). Fecha: 2026-11-04.

## Rúbrica / entrega
| # | Requisito | Estado | Implementación | Prueba / evidencia |
|---|---|---|---|---|
| A | Flujo E2E login → vuelo → evento → notificación → correo | ✅ (procesos nativos) · 🟡 en Compose | servicios + outbox + consumidor + reminder-worker | `scripts/e2e_smoke.py` **24/24 PASS** (`evidencias/e2e-smoke.txt`); correo contra sumidero SMTP propio, no Mailpit |
| A+ | **Agenda del viajero** (sin traslapes ni saltos de ciudad, fecha y hora, llegada calculada, alertas) | ✅ (nativo) · 🟡 en Compose | `domain/scheduling.py`, lock por usuario, UI con aviso previo | 15 pruebas unitarias + 4 de integración (incluye **carrera concurrente**: sin el lock falla 4/4, con él pasa 5/5) + E2E pasos 18–21 |
| A | Resiliencia: RabbitMQ caído | ✅ (nativo) | outbox + relay/consumidor con reconexión | `scripts/e2e_resilience.py` 4/4 PASS |
| A | Resiliencia: latencia/caída de Airport, BD, Redis y proveedor | ✅ (nativo) | timeouts, circuit breaker, 503/502, respaldo PostgreSQL | `scripts/e2e_faults.py` 11/11 PASS (proxy de fallos propio, **no** Toxiproxy) |
| A | Arranque con Docker Compose | 🔒 | compose con healthchecks, `bootstrap-env.sh` | `docker compose config` OK (12 servicios); **`up` no ejecutado** (sin Docker Hub) |
| B | Pruebas backend | ✅ | unitarias + integración con PostgreSQL real | airport 20, itinerary 60, auth 10, notification 60 = **150 PASS** (`evidencias/pruebas.txt`) |
| B | Pruebas frontend, tipos, lint, build | ✅ | vitest | **72 PASS** · `tsc` OK · lint sin avisos · build OK · `npm audit --omit=dev`: 0 |
| B | Vulnerabilidades de dependencias | ✅ backend · 🟡 frontend dev | backend: `pip-audit` **0** tras subir fastapi/starlette y migrar python-jose → PyJWT; frontend: 7 en dependencias **de desarrollo** (vitest/esbuild) sin aplicar `--force` | `evidencias/seguridad-auditoria.txt`, `seguridad.md` |
| B | CI GitHub Actions | 🟡 / 🔒 | `.github/workflows/ci.yml` | **no ejecutado** en GitHub; ver `ci-y-calidad.md` |
| B | SonarCloud / Quality Gate | 🔒 | `sonar-project.properties` + job condicionado | requiere `SONAR_TOKEN` y variables; **ningún análisis ejecutado** |
| C | Carga con Locust | ✅ | scripts con flujo real (agenda encadenada por usuario virtual) | 4 perfiles repetidos con el código actual, 0 fallos, backlog del outbox 0; `pruebas-de-carga.md`, `evidencias/locust/` |
| D | Migraciones versionadas | ✅ | Alembic ×3 (itinerary 0003 `departure_at` con backfill; notification 0003 horas) | upgrade/downgrade y adopción de BD con datos; backfill probado (`migraciones.md`) |
| E | Contrato de eventos | ✅ | `docs/asyncapi.yaml` | validado con AsyncAPI CLI (0 errores) y contrastado con el código |
| F | Backlog Jira | 🟡 / 🔒 | `jira/backlog.csv` (estados reales; sprints 7 y 8 pendientes) | **no importado**; capturas manuales (ver `evidencias/README.md`) |
| G | README / documentación | ✅ | `README.md`, `context.md`, `docs/*` | nombres de servicios/puertos/variables contrastados con Compose |

## Defectos encontrados y corregidos
| Defecto | Cómo se detectó | Corrección | Prueba |
|---|---|---|---|
| Itinerario y evento en **dos transacciones** (el outbox no resolvía el Double Write) | lectura de código | `save_with_event` atómico | integración: fallo del evento revierte el itinerario |
| Relay sin reconexión; sin `SKIP LOCKED`; errores tragados | lectura | relay reescrito (confirms, 1 TX/evento, reconexión) | integración (6) |
| Relay drenaba ~10 eventos/s → **1035 PENDING** tras la carga | **Locust** (medido) | no dormir con lote lleno | regresión + repetición de carga: 0 pendientes a los 10 s |
| Mensaje inválido se reencolaba sin fin | lectura | `reject(requeue=False)` → DLQ | unit + E2E paso 11 |
| Idempotencia con SELECT+INSERT (condición de carrera) | lectura | `ON CONFLICT DO NOTHING` | integración con 8 hilos concurrentes |
| Contenedores Postgres sin `POSTGRES_PASSWORD` | lectura de `.env.example`/Compose | `db.env` + `bootstrap-env.sh` | `docker compose config`; ⏳ arranque real |
| Fallback de aeropuertos solo con circuito abierto (las 2 primeras fallas → 500) | lectura | cualquier falla del upstream usa Redis stale / PostgreSQL; 503 si no hay respaldo | unit (5 nuevas) |
| Registro con `iataCode` nulo tumbaba todo el listado | lectura | mapeo tolerante, registro inválido se omite | unit |
| Id no-UUID → 500 | lectura | 404 | unit API |
| JWT aceptado sin `exp` | lectura | `require_exp` | unit API |
| Caché Redis con `pickle` | lectura (hotspot típico de Sonar) | JSON | unit |
| Traefik con socket de Docker montado; puertos de BD/servicios abiertos | lectura | solo proveedor de archivo; puertos en `127.0.0.1` | `config` |
| `locust`/`pytest` dentro de la imagen de producción | lectura de locks | `requirements-dev.txt` aparte; locks regenerados con las mismas versiones transitivas | `pip --dry-run --require-hashes` ×4 |

**Importante:** estos defectos se detectaron leyendo el código del ZIP recibido; no se reprodujeron uno a uno sobre la versión original, salvo el del relay (medido con Locust antes del fix).

## Pruebas: antes → después
Backend 23 → **150**; frontend 55 → **72** (cobertura 54.8 % medida antes de la agenda; los componentes visuales no tienen pruebas).

## Sprints adicionales (evaluados)
| Sprint | Decisión |
|---|---|
| 6 Recordatorios | ✅ (nativo) | correo en el JWT (opcional, sin inventar identidades), eventos Updated/Deleted, `reminder-worker`, idempotencia, zonas horarias, cancelación; probado con sumidero SMTP propio. **Mailpit en Compose: 🟡 no ejecutado** |
| 7 Observabilidad | ⏳ No implementado (Prometheus/Grafana/Jaeger no se pueden levantar en el entorno); hay logs JSON con `X-Trace-Id` |
| 8 Despliegue continuo | ⏳ Sin proveedor/entorno definido; no hay URL pública |
| 9 Resiliencia | ✅ latencia, timeouts, circuit breaker, caída de BD/Redis/proveedor/RabbitMQ con **proxy de fallos propio** (`tools/fault_proxy.py`); Toxiproxy/Testcontainers no usados |
| 10 Seguridad | ✅ parcial: ver [`seguridad.md`](seguridad.md) (pip-audit 0, bandit 0, PyJWT, JWT_SECRET ≥ 32); ⏳ endurecimiento de contenedores y cabeceras |

## Riesgos conocidos
1. Primera ejecución de Compose y del CI aún no realizadas (pueden aparecer ajustes de arranque/timing).
2. Carga medida en 1 VM compartida y con mock; no extrapolar.
3. Auth stub sin contraseñas (decisión del alcance).
4. Las versiones de GitHub Actions no se verificaron en línea.
