# Changelog

## [1.0.0] - Primer release funcional completo

### Añadido
- Airport Service: Hexagonal, patrón Adapter (API Colombia), caché Redis,
  Circuit Breaker + Retry, PostgreSQL como 3er nivel de resiliencia. 6/6 pruebas.
- Itinerary Service: Hexagonal, Outbox transaccional (Double Write Problem),
  Adapter HTTP a Airport Service, anti-IDOR, anti-mass-assignment. 10/10 pruebas.
- Notification Function: consumidor real de RabbitMQ, idempotente ante
  reentrega. 2/2 pruebas.
- Auth stub: emisor de JWT (HS256), validado cruzadamente contra Itinerary
  Service. 5/5 pruebas.
- Frontend: Vite + React + TypeScript, mapa Plotly (lazy-loaded), gestión
  de itinerarios, token JWT solo en memoria. 2/2 pruebas, lint limpio,
  build de producción verificado.
- API Gateway (Traefik): routing + rate limiting.
- Blindaje de seguridad: CLAUDE.md, hook PreToolUse, PR template con
  checklist de seguridad.

### Total
25/25 pruebas automatizadas ejecutadas y en verde.

### Pendiente (no incluido en este release)
- Verificación real de `docker compose up` end-to-end (requiere Docker).
- CI/CD real (GitHub Actions + SonarQube) — requiere repo remoto y secretos.
- GenerateItineraryReportFunction (US-009, Nivel 2 opcional).
