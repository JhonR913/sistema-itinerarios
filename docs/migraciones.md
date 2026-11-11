# Migraciones de base de datos (Alembic)

| Servicio | BD | Revisiones |
|---|---|---|
| `airport-service` | `airport` | `0001_baseline` (tabla `airports`) |
| `itinerary-service` | `itinerary` | `0001_baseline` (`itineraries`, `outbox`), `0003_departure_at` (`departure_at TIMESTAMPTZ NOT NULL`; las filas existentes se migran a las 00:00 America/Bogota de su `travel_date`; índice `(user_id, departure_at)`), `0002_outbox_delivery_tracking` (`attempts`, `published_at`, `last_error`, índice parcial de pendientes) |
| `notification-function` | `notification` | `0001_baseline` (`notification_history` + índice único `itinerary_id`) |

## Cómo se aplican
Automáticamente al iniciar el contenedor (`alembic upgrade head && ...`). El `outbox-worker`
**no** migra: espera a que `itinerary-service` esté sano. `env.py` toma un
*advisory lock* de PostgreSQL, de modo que dos arranques simultáneos no chocan.

## Comandos manuales
```bash
# con Compose (la URL viene del .env del contenedor)
docker compose exec itinerary-service alembic current
docker compose exec itinerary-service alembic upgrade head
docker compose exec itinerary-service alembic downgrade -1     # revierte la última

# sin Docker
cd services/itinerary-service && DATABASE_URL=postgresql://... alembic upgrade head
# nueva migración (SQL explícito con op.execute, como las existentes)
alembic revision -m "descripcion"
```

## Datos existentes
`0001_baseline` usa `CREATE ... IF NOT EXISTS`: en una base creada con el esquema anterior
(scripts de `initdb`) solo registra la versión; **no modifica ni borra datos**. Verificado:
BD con 1 itinerario y 1 evento → `upgrade head` conserva ambos y añade las columnas nuevas
(`docs/evidencias/`). Reiniciar contenedores o repetir `upgrade head` no cambia nada.

## Reversión
`downgrade` de `0002` solo quita columnas/índice nuevos. `downgrade` de `0001` es
**destructivo** (elimina tablas): usar solo en desarrollo.


`downgrade` de `0003` (itinerary) elimina `departure_at` (se pierde la hora, no la fecha). En `notification-function`, `0003_trip_times` añade `departure_at`, `arrival_at` y las ciudades a `reminders`; es aditiva y reversible.
