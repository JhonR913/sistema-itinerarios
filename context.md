# Contexto del proyecto — Sistema de Itinerarios Personales

> Documento de traspaso: pégalo al inicio de un chat nuevo para continuar sin perder el hilo.
> Actualizado: 2026-11-15. Repositorio: <https://github.com/JhonR913/sistema-itinerarios>.
> Leyenda: ✅ verificado (ejecutado) · 🟡 implementado, no validado · ⏳ pendiente · 🔒 depende de ti (cuentas/secretos).

## 1. Qué es
Sistema universitario de microservicios para planificar vuelos: el usuario se registra, elige origen, destino,
fecha y hora; el sistema calcula la llegada, impide que un vuelo se cruce con otro suyo o salga de una
ciudad donde no aterrizó, y le envía por correo un recordatorio 24 h antes de cada salida.

| Pieza | Tecnología |
|---|---|
| `frontend` | React + Vite + TypeScript, mapa Plotly, nginx |
| `auth-stub` (nombre histórico) | **Identidad real**: FastAPI + PostgreSQL, registro con código por correo, login, sesión por cookie `httpOnly`, emite JWT HS256 |
| `airport-service` | FastAPI, patrón Adapter (API Colombia), Redis, circuit breaker, respaldo PostgreSQL |
| `itinerary-service` | FastAPI hexagonal, agenda sin traslapes, **Transactional Outbox** → RabbitMQ |
| `notification-function` | consumidor idempotente + `reminder-worker` que envía correos por SMTP |
| Infra | PostgreSQL por servicio, Redis, RabbitMQ, Traefik, Docker Compose, Alembic, SonarCloud, Dependabot |

## 2. Reglas de trabajo (no negociables)
- No afirmar que algo pasó/está desplegado sin verificarlo; distinguir ✅ / 🟡 / ⏳ / 🔒.
- Sin secretos en el repositorio ni en el chat (`.env` ignorados; plantillas `@@TOKEN@@`).
- **Todo cambio va en una rama nueva** (el ruleset de GitHub rechaza pushes directos, GH013) y entra por PR.
- Commits en español, Conventional Commits. Nunca modificar `main`/`develop` directamente. Sin force push.
- Hexagonal (el dominio no importa infraestructura), SQL siempre parametrizado, validación en servidor, anti-IDOR.
- No exponer BD, RabbitMQ ni credenciales a Internet.

## 3. Estado actual
**✅ Verificado en el entorno de desarrollo del asistente** (PostgreSQL 16, Redis, RabbitMQ y SMTP de pruebas como procesos nativos, sin Docker):
- 239 pruebas de backend (airport 20, itinerary 60, auth 85, notification 74) y 101 de frontend; `tsc` y eslint limpios.
- Flujo completo: registro → código por correo → sesión → agenda → outbox → RabbitMQ → notificación → recordatorio (31/31 pasos en `scripts/e2e_smoke.py`).
- Resiliencia con RabbitMQ caído (4/4); fallos de dependencias (11/11, ejecutado antes de la identidad real); Locust 4 perfiles; migraciones Alembic.
- Navegador real (Playwright/Chromium): registrarse, verificar, refrescar sin perder sesión, cerrar sesión, login, agenda y el mapa bajo la CSP.
- `pip-audit` 0 vulnerabilidades; `bandit` 0 hallazgos.
- Evidencias en `docs/evidencias/`; detalle por ítem en `docs/matriz-estado.md` y `docs/seguridad.md`.

**✅ Verificado por el dueño:** `docker compose up` con la versión anterior (todos los contenedores sanos; la app funciona en `http://localhost`).

**🟡 / 🔒 No verificado todavía** (hace falta Docker, GitHub, Cloudflare o Gmail reales):
- `docker compose` con la identidad real y con el perfil de producción (`cloudflared`).
- `deploy.yml`, `scripts/deploy.sh`, el runner y el túnel de Cloudflare.
- Envío real por Gmail. nginx real con las cabeceras de seguridad (solo se probaron con un servidor de reemplazo).
- CI en GitHub nunca se ha visto correr; SonarCloud con Quality Gate en rojo (ver §7).
- Versión de `cloudflared` fijada (`2026.10.5`) tomada de las releases de GitHub; si no existe la imagen, cambiar el tag.

## 4. Cómo funciona el acceso (decisiones de diseño)
- Registro: correo + nombre + contraseña (≥ 10 caracteres, `scrypt`). Código de 6 dígitos al correo: 10 min, un solo uso, 5 intentos (contados de forma atómica en SQL), guardado como HMAC.
- Sin verificar el correo no hay sesión. Los recordatorios van **solo al correo verificado** (claim `email` del JWT).
- Login con mensaje único; bloqueo 15 min tras 5 fallos; 60 s entre códigos, 5/h por correo y 100/h globales (protege la cuota de Gmail).
- Registro, reenvío y olvido de contraseña responden igual exista o no la cuenta (sin enumeración).
- JWT de acceso (30 min) **solo en memoria**; sesión de 14 días en cookie `httpOnly` + `SameSite=Strict` (+ `Secure` en producción), path `/api/auth`.
- `POST /api/auth/token` (login sin contraseña) **ya no existe**.
- Sin captcha, MFA ni límite por IP real (tras el túnel todos llegan del mismo contenedor): mitigar con Cloudflare WAF o Cloudflare Access (ver `docs/despliegue.md` §6).

## 5. Qué debes hacer para subirlo a GitHub (en Git Bash)
Tienes el zip `itinerarios-identidad-despliegue.zip` (solo archivos versionados, sin secretos).
```bash
cd /c/proyectos/itinerarios-repo            # tu clon
git checkout main && git pull
git checkout -b feature/identidad-real-y-despliegue
# descomprimir ENCIMA del clon (ajusta la ruta del zip):
powershell.exe -NoProfile -Command "Expand-Archive -Force -Path \$env:USERPROFILE\Downloads\itinerarios-identidad-despliegue.zip -DestinationPath ."
# borrar lo que ya no existe en la versión nueva:
git rm -f --ignore-unmatch frontend/src/features/auth/LoginForm.tsx \
  services/auth-stub/tests/unit/test_issue_token.py services/auth-stub/tests/unit/test_jwt_issuer.py \
  services/auth-stub/tests/unit/test_email_validation.py
git update-index --chmod=+x scripts/*.sh       # Windows pierde el bit de ejecución
git add -A
git status                                     # revisa: NO debe aparecer ningún .env
git commit -m "feat: identidad real con código por correo, despliegue automático y túnel de Cloudflare"
git push -u origin feature/identidad-real-y-despliegue
```
Luego, en GitHub: abrir el **Pull Request** hacia `main` → esperar el **CI** en verde → fusionar.
Antes, cerrar los 29 PRs viejos de Dependabot (la nueva configuración abre 1 por ecosistema al mes).

## 6. Qué necesito de tu correo (Gmail) para que los recordatorios y códigos funcionen
**No me pases contraseñas ni tokens por el chat.** Los escribes solo en tu PC con `scripts/configure-prod.sh`.
1. Cuenta de Gmail que enviará los mensajes (la usarás como remitente).
2. Activar la **verificación en dos pasos** en esa cuenta de Google.
3. Crear una **contraseña de aplicación** (Cuenta de Google → Seguridad → Contraseñas de aplicaciones → nombre `itinerarios`) y copiar las 16 letras.
4. Escribir ambos datos en el paso 4 del despliegue (el script los pide sin mostrarlos).

Lo único que sí necesito de ti, en texto, para ayudarte: confirmar cuando esté hecho y, si algo falla,
el **mensaje de error exacto** (`docker compose -p itinerarios logs auth-stub` muestra `fallo SMTP` sin claves).
Límites: Gmail permite ≈ 500 correos al día; la app corta en 100 códigos por hora.

## 7. Cómo desplegarlo automáticamente (resumen; guía completa en `docs/despliegue.md`)
Flujo: **PR fusionado a `main` → CI en verde → workflow Deploy → runner en tu PC → `scripts/deploy.sh` → Docker Desktop actualizado**; Cloudflare Tunnel publica `https://itinerarios.tudominio.com` sin abrir puertos.
1. **Cloudflare:** Zero Trust → Networks → Tunnels → crear túnel `itinerarios` → copiar el **token** → *Public hostname*: `itinerarios.tudominio.com` → servicio `HTTP` `traefik:80`.
2. **Secretos:** `./scripts/configure-prod.sh` (pide Gmail, contraseña de aplicación y token; crea `~/itinerarios-config/prod.env`, fuera del repo).
3. **Runner de GitHub:** Settings → Actions → Runners → *New self-hosted runner* (Windows), etiqueta **`itinerarios`**, ejecutarlo con tu usuario (`run.cmd` o tarea al iniciar sesión). Docker Desktop con *Start when you sign in*. Opcional: Environment `production` con aprobación manual.
4. **Primer despliegue a mano:** `./scripts/deploy.sh` (restaura/genera secretos, `docker compose up -d --build`, espera *healthy*, prueba de humo).
5. **Desde ahí es automático:** cada fusión a `main` con CI verde se despliega solo (o *Actions → Deploy → Run workflow*).
6. **SonarCloud:** desactivar *Automatic Analysis* (Administration → Analysis Method), crear el secreto `SONAR_TOKEN` y las variables `SONAR_ORGANIZATION` y `SONAR_PROJECT_KEY`. El CI usa `qualitygate.wait=true`: con el gate en rojo **no se despliega**. Si sigue en rojo (duplicación 9,6 % medida por Sonar vs 1,9 % local), enviar la lista de archivos duplicados.
7. **Lista de comprobación final** (9 puntos) en `docs/despliegue.md` §7: sitio con HTTPS, registro con tu correo real, refrescar conserva sesión, recordatorio inmediato para un vuelo < 24 h, recuperar contraseña, despliegue automático por PR, reinicio del PC.

## 8. Pendiente
- ⏳ Ejecutar la lista de comprobación de despliegue y corregir lo que falle (necesita tu Docker, GitHub, Cloudflare y Gmail).
- ⏳ Sprint 7 (observabilidad: métricas/trazas) y endurecimiento de contenedores (`read_only`, `cap_drop`, `no-new-privileges`).
- ⏳ Importar `jira/backlog.csv` y tomar capturas manuales de Jira/Sonar (`docs/evidencias/README.md`).
- ⏳ Extras opcionales no implementados: editar un vuelo desde la pantalla, exportar `.ics` al calendario.
- ⏳ Ver el CI correr por primera vez en GitHub (versiones de las *actions* sin verificar en línea).

## 9. Mapa del repositorio
`services/*` (4 servicios) · `frontend/` · `gateway/traefik` y `gateway/cloudflared` · `scripts/` (`bootstrap-env.sh`, `configure-prod.sh`, `deploy.sh`, E2E) ·
`tools/` (proxy de fallos, mock de API Colombia, sumidero SMTP; solo pruebas) · `docs/` (`despliegue.md`, `seguridad.md`, `matriz-estado.md`, `migraciones.md`, `asyncapi.yaml`, evidencias) ·
`.github/workflows/` (`ci.yml`, `deploy.yml`) · `jira/backlog.csv` · `sonar-project.properties`.
