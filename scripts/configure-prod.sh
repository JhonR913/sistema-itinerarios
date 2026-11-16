#!/usr/bin/env bash
# Crea (o actualiza) el archivo de configuracion de produccion con los secretos que escribas
# aqui, SIN mostrarlos y SIN pasar por el repositorio ni por ningun chat.
#
#   ./scripts/configure-prod.sh
#
# Resultado: $ITINERARIOS_CONFIG_DIR/prod.env (por defecto ~/itinerarios-config/prod.env), permisos 600.
set -euo pipefail
CONFIG_DIR="${ITINERARIOS_CONFIG_DIR:-$HOME/itinerarios-config}"
TARGET="$CONFIG_DIR/prod.env"
mkdir -p "$CONFIG_DIR"

ask() { # variable, pregunta, secreto(0/1), valor por defecto
  local var="$1" prompt="$2" secret="$3" def="${4:-}" val
  if [[ "$secret" == 1 ]]; then read -r -s -p "$prompt: " val; echo; else read -r -p "$prompt${def:+ [$def]}: " val; fi
  val="${val:-$def}"
  [[ -n "$val" ]] || { echo "  ! $var no puede quedar vacio" >&2; exit 1; }
  [[ "$val" != *$'\n'* && "$val" != *' '* ]] || { echo "  ! $var no puede tener espacios" >&2; exit 1; }
  printf -v "$var" '%s' "$val"
}

echo "Configuracion de produccion -> $TARGET"
ask SMTP_USER "Correo de Gmail que enviara los mensajes" 0
ask SMTP_PASSWORD "Contrasena de APLICACION de Gmail (16 letras, sin espacios)" 1
ask TUNNEL_TOKEN "Token del tunel de Cloudflare" 1

( umask 077; cat > "$TARGET" <<EOT
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_STARTTLS=1
SMTP_USER=$SMTP_USER
SMTP_PASSWORD=$SMTP_PASSWORD
SMTP_FROM=$SMTP_USER
TUNNEL_TOKEN=$TUNNEL_TOKEN
COOKIE_SECURE=1
WEB_BIND=127.0.0.1
EOT
)
chmod 600 "$TARGET" 2>/dev/null || true
echo "Listo. Archivo creado (los valores no se muestran). Siguiente paso: ver docs/despliegue.md"
