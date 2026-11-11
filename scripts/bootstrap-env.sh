#!/usr/bin/env bash
# Genera los archivos .env reales a partir de los *.env.example, con
# secretos aleatorios y CONSISTENTES entre servicios (el JWT_SECRET de
# auth-stub e itinerary-service debe ser identico; la clave de RabbitMQ y de
# cada base de datos debe coincidir entre el servidor y sus clientes).
#
#   ./scripts/bootstrap-env.sh           # crea solo lo que falta
#   ./scripts/bootstrap-env.sh --force   # regenera todo (rota secretos)
#
# Los .env generados estan en .gitignore: NO se versionan.
set -euo pipefail
cd "$(dirname "$0")/.."

FORCE=0; [[ "${1:-}" == "--force" ]] && FORCE=1
rand() { python3 -c 'import secrets; print(secrets.token_hex(24))'; }

# Un secreto por token. Si ya existe un .env, se reutiliza su valor para no
# romper volumenes de bases de datos ya inicializados con esa clave.
declare -A SECRET
for tok in JWT_SECRET AIRPORT_DB_PASSWORD ITINERARY_DB_PASSWORD NOTIFICATION_DB_PASSWORD RABBITMQ_PASSWORD; do
  SECRET[$tok]="$(rand)"
done

# Tokens ya presentes en archivos existentes (reutilizar).
reuse() { # token, archivo, patron_sed
  [[ -f "$2" ]] && { v="$(sed -n "$3" "$2" | head -n1)"; [[ -n "$v" ]] && SECRET[$1]="$v"; } || true
}
if [[ $FORCE -eq 0 ]]; then
  reuse JWT_SECRET services/auth-stub/.env 's/^JWT_SECRET=//p'
  reuse AIRPORT_DB_PASSWORD services/airport-service/db.env 's/^POSTGRES_PASSWORD=//p'
  reuse ITINERARY_DB_PASSWORD services/itinerary-service/db.env 's/^POSTGRES_PASSWORD=//p'
  reuse NOTIFICATION_DB_PASSWORD services/notification-function/db.env 's/^POSTGRES_PASSWORD=//p'
  reuse RABBITMQ_PASSWORD services/itinerary-service/rabbitmq.env 's/^RABBITMQ_DEFAULT_PASS=//p'
fi

render() { # ejemplo -> destino
  local src="$1" dst="${1%.example}"
  if [[ -f "$dst" && $FORCE -eq 0 ]]; then echo "  = $dst (ya existe, se conserva)"; return; fi
  local content; content="$(cat "$src")"
  for tok in "${!SECRET[@]}"; do content="${content//@@${tok}@@/${SECRET[$tok]}}"; done
  ( umask 077; printf '%s\n' "$content" > "$dst" )
  echo "  + $dst"
}

for f in \
  services/auth-stub/.env.example \
  services/airport-service/.env.example services/airport-service/db.env.example \
  services/itinerary-service/.env.example services/itinerary-service/db.env.example services/itinerary-service/rabbitmq.env.example \
  services/notification-function/.env.example services/notification-function/db.env.example; do
  render "$f"
done

[[ -f frontend/.env ]] || { cp frontend/.env.example frontend/.env; echo "  + frontend/.env"; }

docker network inspect itinerarios-net >/dev/null 2>&1 \
  || { docker network create itinerarios-net >/dev/null && echo "  + red docker itinerarios-net"; } \
  || echo "  ! (docker no disponible: crea la red con: docker network create itinerarios-net)"

echo "Listo. Siguiente paso: docker compose up -d --build"
