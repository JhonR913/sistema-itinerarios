# Entorno de las ejecuciones (honestidad sobre el alcance)
- VM Linux Ubuntu 24.04, 2 vCPU, 8 GB. Python 3.11.15 (igual que los Dockerfiles), Node v22.23.4.
- **Sin Docker**: PostgreSQL 16.x, Redis y RabbitMQ 3.12.1 instalados con apt y ejecutados como procesos nativos;
  servicios con uvicorn y los mismos comandos que los contenedores (`alembic upgrade head && uvicorn ...`).
- Proveedor de aeropuertos: `tools/mock_api_colombia.py` (datos de prueba). Sin Traefik, sin nginx, sin contenedores.
- Usuario RabbitMQ `itinerarios` creado a mano para imitar `rabbitmq.env`.
- NO verificado aquí: `docker compose up`, build de imágenes, Traefik, GitHub Actions, SonarCloud, Jira.
