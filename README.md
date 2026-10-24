# Sistema de Itinerarios Personales

Repositorio oficial de implementación (monorepo). La especificación
completa vive en los documentos de la fase documental — este código es
consistente con esos documentos, no los redefine sobre la marcha.

## Estado real (no aspiracional) — 5 sprints completos

| Sprint | Entregable | Pruebas | Build/lint |
|---|---|---|---|
| 1 | Airport Service (Adapter, Redis, Circuit Breaker) | 6/6 PASS | — |
| 2 | Itinerary Service (Outbox, anti-IDOR, anti-mass-assignment) | 10/10 PASS | — |
| 3 | Notification Function (consumidor real de RabbitMQ) + Gateway | 2/2 PASS | — |
| 4 | Auth stub (emisor JWT) | 5/5 PASS | — |
| 5 | Frontend (Vite+React+TS, mapa Plotly, gestión de itinerarios) | 2/2 PASS | build + lint OK |

**Total: 25/25 pruebas automatizadas ejecutadas y en verde**, en 5
servicios. Detalle completo con evidencia en `docs/matriz-estado.md`.

## Lo único que NO se pudo verificar desde este entorno

Este repositorio se construyó en un entorno de build sin Docker, sin
acceso a GitHub/Jira reales y sin RabbitMQ/Postgres en ejecución. Por
construcción, estas 4 cosas quedan como los únicos pasos que **debés
correr vos** antes de poder decir "desplegado al 100%":

| # | Qué falta | Dónde está la guía |
|---|---|---|
| 1 | `docker compose up -d --build` real, de punta a punta | Ver "Cómo levantar todo" más abajo |
| 2 | Repo remoto en GitHub + ramas protegidas + CI | Guía paso a paso ya entregada en el chat (parte A) |
| 3 | Proyecto Jira real + import de `jira/backlog.csv` | Guía paso a paso ya entregada en el chat (parte B) |
| 4 | SonarQube real (token + host) para que corra el Quality Gate del CI | `Documento_Ciclo_DevOps.docx` sección 5 |

## Cómo levantar todo (tu primer paso)

```bash
docker network create itinerarios-net
docker compose up -d --build
```

Antes de correrlo, copiá cada `.env.example` a `.env` en:
`services/auth-stub/`, `services/airport-service/`,
`services/itinerary-service/`, `services/notification-function/`,
`frontend/` — y completá los valores reales.

**Crítico:** `JWT_SECRET` en `services/auth-stub/.env` y en
`services/itinerary-service/.env` debe ser **exactamente el mismo valor**
(uno emite el token, el otro lo valida; si no coinciden, todo falla con
401). Generá uno fuerte, por ejemplo:

```bash
openssl rand -hex 32
```

### Verificación rápida tras levantar

```bash
curl -X POST http://localhost/api/auth/token -H "Content-Type: application/json" -d '{"username":"jhon"}'
# copiá el access_token de la respuesta

curl http://localhost/api/airports
# deberia responder con la lista de aeropuertos (puede tardar la primera vez: llama a API Colombia)

curl -X POST http://localhost/api/itineraries -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" \
  -d '{"nombre_usuario":"jhon","origin_airport_id":"<id-real>","destination_airport_id":"<otro-id>","travel_date":"2026-12-01","duration_minutes":90}'
```

- Frontend: http://localhost:5173
- Gateway: http://localhost/api/...
- RabbitMQ management: http://localhost:15672 (guest/guest — **cambiar antes de producción real**, ver `Plan_de_Blindaje_Seguridad.docx` sección 4)
- Swagger de cada servicio: puerto directo + `/docs` (ver `docker-compose.yml` de cada uno)

Si algo no levanta: `docker compose logs <servicio>` primero. Las causas
más comunes son red no creada, puerto ocupado, o `.env` faltante.

## Correr todas las pruebas

```bash
for s in airport-service itinerary-service notification-function auth-stub; do
  echo "== $s =="
  (cd services/$s && pip install -r requirements.txt -q && pytest tests/unit -v)
done

cd frontend && npm install && npm test && npm run build
```

## Estrategia de ramas

`main` ← `develop` ← `feature/<historia>`, Pull Request obligatorio, merge
`--no-ff` (ver historial real con `git log --graph --all`). Checklist de
seguridad en `.github/pull_request_template.md`.

## Estructura (monorepo)

```
services/
  auth-stub/              # Sprint 4 — emisor JWT (sin gestion de identidad completa)
  airport-service/         # Sprint 1 — Hexagonal + Adapter + Redis + Postgres (3 niveles resiliencia)
  itinerary-service/        # Sprint 2 — Hexagonal + Outbox (Double Write Problem)
  notification-function/    # Sprint 3 — FaaS, consumidor real de RabbitMQ, idempotente
frontend/                   # Sprint 5 — Vite+React+TS, arquitectura en capas
gateway/traefik/             # Sprint 3 — routing + rate limiting, sin logica de negocio
docs/matriz-estado.md        # Estado real de implementacion, por sprint, con evidencia
jira/backlog.csv             # Backlog con columna Status
```

## Pendiente real (no hecho, no prometido)

- CI (GitHub Actions) y SonarQube: requieren repo remoto y secretos del equipo.
- `docker compose up` de punta a punta: requiere Docker, no disponible en el entorno de build.
- Registro de usuarios real: fuera de alcance por decisión documentada (ADR, Auth stub).
