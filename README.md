# Sistema de Itinerarios Personales

Repositorio oficial de implementación (monorepo). La especificación
completa vive en los documentos de la fase documental — este código debe
ser consistente con esos documentos, no redefinirlos sobre la marcha.

## Estado real (no aspiracional)

| Sprint | Servicio | Pruebas unitarias | Docker | RabbitMQ |
|---|---|---|---|---|
| 1 | Airport Service | 4/4 PASS | Escrito, no verificado end-to-end | N/A |
| 2 | Itinerary Service | 10/10 PASS | Escrito, no verificado end-to-end | Productor (Outbox → cola `itinerary.created`) |
| 3 | Notification Function + Gateway | 2/2 PASS | Escrito, no verificado end-to-end | Consumidor real (`consumer.py`, con ack/nack) |

**Total: 16/16 pruebas unitarias ejecutadas y en verde.**

Los 6 archivos `docker-compose.yml`/Traefik se validaron sintácticamente
(YAML correcto, red compartida `itinerarios-net` consistente, RabbitMQ
declarado una sola vez y referenciado desde donde corresponde). **No se
ejecutó `docker compose up` real** porque este entorno de construcción no
tiene Docker instalado — el primer paso para ti es correrlo en tu máquina
y confirmar que levanta.

## Cómo levantar todo

```bash
docker network create itinerarios-net
docker compose up -d --build
```

- Gateway: http://localhost/api/airports · http://localhost/api/itineraries
- Airport Service (directo, dev): http://localhost:8001/docs
- Itinerary Service (directo, dev): http://localhost:8002/docs
- RabbitMQ management: http://localhost:15672 (guest/guest — cambiar antes de producción, ver Plan_de_Blindaje_Seguridad.docx)

Si algo no levanta, lo más probable es un puerto ocupado o la red no
creada antes del `up`. Revisa `docker compose logs <servicio>`.

## Correr todas las pruebas unitarias

```bash
for s in airport-service itinerary-service notification-function; do
  echo "== $s =="
  (cd services/$s && pip install -r requirements.txt -q && pytest tests/unit -v)
done
```

## Estrategia de ramas

`main` ← `develop` ← `feature/<historia>`, con Pull Request obligatorio y
merge `--no-ff` (ver historial de este repo con `git log --graph --all`).
Checklist de seguridad en `.github/pull_request_template.md`.

## Estructura (monorepo)

```
services/
  airport-service/       # Sprint 1 — Hexagonal + Adapter (API Colombia)
  itinerary-service/      # Sprint 2 — Hexagonal + Outbox (Double Write Problem)
  notification-function/  # Sprint 3 — FaaS, consumidor real de RabbitMQ, idempotente
gateway/traefik/           # Sprint 3 — routing + rate limiting, sin logica de negocio
docs/matriz-estado.md      # Estado real de implementacion, por sprint, con evidencia
jira/backlog.csv           # Backlog con columna Status
```

## Pendiente (próximos sprints)

- US-002: mapa Plotly (frontend) — en progreso, ver `frontend/`.
- US-010: Auth stub real emisor de JWT (hoy los servicios validan JWT pero
  nada lo emite todavía).
- `docker compose up` verificado de punta a punta en una máquina con Docker.
- CI (GitHub Actions) y SonarQube reales — requieren repo remoto.
