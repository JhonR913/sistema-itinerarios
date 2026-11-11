# Contexto del proyecto (estado de la entrega)

Sistema universitario de itinerarios personales: frontend React, 4 servicios Python,
PostgreSQL por servicio, Redis, RabbitMQ (Transactional Outbox), Traefik, Docker Compose.
Repositorio conocido: https://github.com/JhonR913/sistema-itinerarios (no accedido desde esta sesión).

## Qué se verificó (ejecutado) en esta entrega
- Backend: pruebas unitarias + integración con PostgreSQL real (ver `docs/matriz-estado.md`).
- Frontend: 55 tests, `tsc`, lint, build.
- Flujo completo login → itinerario → outbox → RabbitMQ → notificación, idempotencia, DLQ,
  caída de RabbitMQ: `scripts/e2e_smoke.py`, `scripts/e2e_resilience.py` (procesos nativos).
- Migraciones Alembic (upgrade/downgrade, adopción de BD existente).
- Locust: 4 perfiles (`docs/pruebas-de-carga.md`).

## Qué NO se verificó
- `docker compose up` real (sin acceso a Docker Hub en el entorno de trabajo).
- GitHub Actions, SonarCloud/Quality Gate, Jira, Traefik en ejecución.

## Decisiones técnicas relevantes
- Outbox transaccional: itinerario + evento en una transacción (`save_with_event`).
- DLQ `itinerary.created.dlq`; idempotencia con `ON CONFLICT DO NOTHING`.
- Alembic con baseline idempotente; `initdb` ya no se usa.
- Secretos: `scripts/bootstrap-env.sh`; `.env` fuera de git; puertos solo en 127.0.0.1.
- Traefik sin socket de Docker; `/` enruta al frontend, `/api/*` a los servicios.
- Caché Redis en JSON (no pickle).

## Hallazgos corregidos (detectados por lectura de código y por Locust)
Outbox no transaccional; relay sin reconexión y con techo de ~10 eventos/s (backlog de 1035
eventos medido bajo carga); consumidor con mensajes venenosos en bucle; fallback de aeropuertos
solo con circuito abierto; id no UUID → 500; Postgres sin contraseña en `.env.example`; JWT sin
exigir `exp`.

## Pendiente / siguiente paso
Primera ejecución real de Compose y del CI; Sonar; capturas manuales; Sprints 6–10 (ver `jira/backlog.csv`).
