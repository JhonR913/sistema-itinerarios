#!/usr/bin/env bash
# Despliega ESTE checkout en el Docker local. Lo ejecuta el runner de GitHub Actions
# (.github/workflows/deploy.yml) o tu a mano:   ./scripts/deploy.sh
#
# * Los secretos NO viven en el checkout (el runner lo recrea en cada despliegue): se guardan en
#   $ITINERARIOS_CONFIG_DIR (por defecto ~/itinerarios-config) y se restauran aqui.
# * Las bases de datos persisten en volumenes de Docker del proyecto "itinerarios".
# * Sale con codigo != 0 si algun contenedor no queda sano o el sitio no responde.
set -euo pipefail
cd "$(dirname "$0")/.."

CONFIG_DIR="${ITINERARIOS_CONFIG_DIR:-$HOME/itinerarios-config}"
PROJECT="${COMPOSE_PROJECT:-itinerarios}"
PROD_ENV="$CONFIG_DIR/prod.env"
ENV_FILES=(
  services/auth-stub/.env services/auth-stub/db.env
  services/airport-service/.env services/airport-service/db.env
  services/itinerary-service/.env services/itinerary-service/db.env services/itinerary-service/rabbitmq.env
  services/notification-function/.env services/notification-function/db.env
  frontend/.env
)
log() { printf '\n==> %s\n' "$*"; }

[[ -f "$PROD_ENV" ]] || {
  echo "Falta $PROD_ENV. Crealo una sola vez con: ./scripts/configure-prod.sh" >&2; exit 1; }

grep -Eq '^TUNNEL_TOKEN=.+' "$PROD_ENV" || { echo "prod.env no tiene TUNNEL_TOKEN (./scripts/configure-prod.sh)" >&2; exit 1; }
grep -Eq '^SMTP_PASSWORD=.+' "$PROD_ENV" || { echo "prod.env no tiene SMTP_PASSWORD (./scripts/configure-prod.sh)" >&2; exit 1; }

log "Restaurando secretos generados en despliegues anteriores"
mkdir -p "$CONFIG_DIR/envs"
for f in "${ENV_FILES[@]}"; do
  if [[ -f "$CONFIG_DIR/envs/$f" ]]; then mkdir -p "$(dirname "$f")"; cp "$CONFIG_DIR/envs/$f" "$f"; fi
done

log "Completando los .env que falten (secretos aleatorios; los existentes se conservan)"
./scripts/bootstrap-env.sh

log "Guardando secretos para el proximo despliegue"
for f in "${ENV_FILES[@]}"; do
  mkdir -p "$CONFIG_DIR/envs/$(dirname "$f")"
  ( umask 077; cp "$f" "$CONFIG_DIR/envs/$f" )
done

DC=(docker compose -p "$PROJECT" --env-file "$PROD_ENV" --profile tunnel)

log "Construyendo y levantando"
"${DC[@]}" up -d --build --remove-orphans

log "Esperando a que todos los contenedores esten sanos (max. 5 min)"
healthy() {
  local bad=0 line
  while read -r line; do
    case "$line" in *" starting"|*" unhealthy"|*" exited"|*" restarting") bad=1 ;; esac
  done < <("${DC[@]}" ps -q | xargs docker inspect --format \
    '{{.Name}} {{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}')
  return $bad
}
for _ in $(seq 1 60); do healthy && break; sleep 5; done
if ! healthy; then
  echo "Algun contenedor no quedo sano:" >&2
  "${DC[@]}" ps >&2
  "${DC[@]}" logs --tail=40 >&2 || true
  exit 1
fi

log "Prueba de humo sobre el sitio local"
curl -fsS -o /dev/null http://127.0.0.1/ || { echo "El frontend no responde en http://127.0.0.1/" >&2; exit 1; }
curl -fsS http://127.0.0.1/api/airports | head -c 120; echo
code="$(curl -s -o /dev/null -w '%{http_code}' -X POST http://127.0.0.1/api/auth/refresh)"
[[ "$code" == "401" ]] || { echo "auth deberia responder 401 sin sesion y respondio $code" >&2; exit 1; }

docker image prune -f >/dev/null 2>&1 || true
log "Despliegue correcto"
"${DC[@]}" ps --format 'table {{.Service}}\t{{.Status}}'
