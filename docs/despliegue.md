# Despliegue continuo en tu equipo + publicación con Cloudflare Tunnel

Objetivo: cada cambio que se fusiona a `main` (y pasa el CI) se construye y actualiza solo en el
Docker Desktop de tu PC, y el sitio queda público en tu dominio **sin abrir puertos del router**.

```
GitHub (main) ──CI en verde──► runner propio (tu PC) ──► scripts/deploy.sh ──► docker compose up -d --build
                                                                                      │
Internet ──► Cloudflare (HTTPS, tu dominio) ══ túnel ══► cloudflared ► traefik ► frontend / servicios
```

> **Estado de verificación (honesto).** Lo que se probó de verdad: las pruebas, el flujo completo de
> registro/verificación/alertas sobre PostgreSQL, RabbitMQ y SMTP reales en proceso nativo, y el
> navegador (Chromium) con las cabeceras de seguridad. **Lo que NO se pudo probar aquí** (no hay
> Docker, ni tu cuenta de GitHub, Cloudflare o Gmail): el `docker compose` de producción, el runner,
> el túnel y el envío real por Gmail. Para eso está la lista de comprobación del final: ejecútala
> una vez y, si algo falla, pásame el error.

## 0. Qué necesitas
| Pieza | Detalle |
|---|---|
| PC con Windows 10/11, Docker Desktop y **Git for Windows** (trae Git Bash) | encendido mientras quieras el sitio disponible |
| Dominio en Cloudflare | el de Hostinger, con los *nameservers* de Cloudflare ya apuntados |
| Cuenta de Gmail | con **verificación en dos pasos** activa, para crear una contraseña de aplicación |
| Este repositorio en GitHub | donde fusionas a `main` |

## 1. Gmail: contraseña de aplicación
1. Cuenta de Google → *Seguridad* → activa la **verificación en dos pasos**.
2. Busca **“Contraseñas de aplicaciones”** → crea una (nombre: `itinerarios`) → copia las 16 letras.
3. **No la pegues en el chat ni en el repositorio.** Se escribe solo en el paso 4.

Límites reales de Gmail: ~500 correos al día. La aplicación lo protege con un tope de **100 códigos
por hora** en total y 5 por hora y por correo (`MAX_CODES_PER_HOUR_GLOBAL`, `MAX_CODES_PER_HOUR`).

## 2. Cloudflare: túnel
1. Panel de Cloudflare → **Zero Trust** → *Networks* → **Tunnels** → *Create a tunnel* → tipo **Cloudflared**.
2. Nombre: `itinerarios`. En “Install and run”, **copia solo el token** (la cadena larga después de `--token`).
3. Pestaña **Published application / Public hostname** → *Add*:
   - Subdomain: `itinerarios` · Domain: *tu dominio* (resulta `itinerarios.tudominio.com`)
   - Service: **Type `HTTP`** · URL **`traefik:80`**  ← el nombre del contenedor, no `localhost`.
4. En *SSL/TLS* del dominio deja el modo **Full** o **Flexible** (el túnel ya va cifrado hasta Cloudflare).
   Activa *Always Use HTTPS*.

## 3. Runner de GitHub en tu PC (una sola vez)
1. Repositorio → *Settings* → *Actions* → *Runners* → **New self-hosted runner** → Windows x64. Sigue los
   comandos que muestra GitHub (descargar, `config.cmd`). Cuando pregunte por **etiquetas**, escribe:
   `itinerarios`.
2. Ejecútalo **con tu usuario de Windows** (no como servicio de otra cuenta): Docker Desktop solo
   funciona dentro de tu sesión. Dos formas:
   - Manual: `./run.cmd` en esa carpeta (déjalo abierto), o
   - Automático: *Programador de tareas* → tarea “Al iniciar sesión” que ejecute `run.cmd`.
3. En Docker Desktop → *Settings* → *General* → activa **Start Docker Desktop when you sign in**.
4. *Settings* → *Actions* → *General* → “Fork pull request workflows”: **Require approval for all
   outside collaborators**. Un runner propio ejecuta código en tu PC: nunca lo uses con PR de extraños
   (el workflow de despliegue solo corre sobre `main`, nunca sobre pull requests).
5. Opcional: *Settings* → *Environments* → **production** → *Required reviewers* (te pide un clic de
   aprobación antes de cada despliegue; en repos privados requiere plan de pago).

## 4. Secretos de producción (una sola vez, en tu PC)
En Git Bash, dentro de una copia del repo (cualquiera):
```bash
./scripts/configure-prod.sh
```
Te pregunta el Gmail, la contraseña de aplicación y el token del túnel (**sin mostrarlos**) y crea
`~/itinerarios-config/prod.env` con permisos 600. Ese archivo **no** está en el repositorio ni en
GitHub. Las contraseñas de las bases de datos y el `JWT_SECRET` los genera el propio despliegue la
primera vez (aleatorios) y los guarda en la misma carpeta, para que no cambien entre despliegues.

> Cambiar el SMTP o el túnel después: vuelve a ejecutar el script y haz un despliegue (paso 5).

## 5. Primer despliegue y los siguientes
- **Primero a mano** (para ver los errores en vivo): en Git Bash, `./scripts/deploy.sh`.
- **Automático**: fusiona un PR a `main`. Se ejecuta **CI** y, si termina en verde, **Deploy**
  (pestaña *Actions*). También puedes lanzarlo con *Actions → Deploy → Run workflow* (solo sobre `main`).
- El script: restaura secretos → completa `.env` faltantes → `docker compose up -d --build` →
  espera a que todos los contenedores estén *healthy* → prueba de humo (`/`, `/api/airports`,
  `/api/auth/refresh` debe dar 401) → falla con código ≠ 0 y logs si algo no quedó bien.
- Los datos (PostgreSQL) viven en volúmenes de Docker del proyecto `itinerarios` y **sobreviven** a
  los despliegues. Las migraciones se aplican solas al arrancar cada servicio.

## 6. Quién puede entrar
Cualquiera que llegue al sitio puede **crear una cuenta**: correo + contraseña propia (mínimo 10
caracteres) y un **código de 6 dígitos** que llega a ese correo (vence en 10 min, un solo uso, máx. 5
intentos). Hasta verificar el correo no hay sesión ni recordatorios. Los recordatorios de vuelo
solo se envían al correo **verificado** de la cuenta, nunca a uno escrito a mano.

Protecciones incluidas: contraseñas con scrypt; bloqueo de 15 min tras 5 contraseñas erróneas;
respuestas idénticas exista o no la cuenta; sesión en cookie `httpOnly` + `SameSite=Strict`; límites
de envío por correo y global; cabeceras CSP/`nosniff`/`X-Frame-Options`.

Lo que **no** hay (decisión consciente, ver `docs/seguridad.md`): *captcha*, límite por IP real
(detrás del túnel todos llegan desde el mismo contenedor) y MFA. Si quieres cerrar el sitio a personas
concretas (p. ej. el profesor y tu compañero), lo más simple es **Cloudflare Access** (Zero Trust →
Access → Applications → *Self-hosted* → política “Emails: lista”) sobre el mismo hostname; es gratis
hasta 50 usuarios y se hace solo en el panel, sin tocar el código. Para frenar bots:
*Security → WAF → Rate limiting rules* sobre `/api/auth/*` (p. ej. 20 peticiones/minuto por IP).

## 7. Lista de comprobación (ejecútala tú y dime qué falla)
1. [ ] `./scripts/configure-prod.sh` termina sin error y crea `~/itinerarios-config/prod.env`.
2. [ ] `./scripts/deploy.sh` termina con “Despliegue correcto” y la tabla muestra `cloudflared` *Up*.
3. [ ] `https://itinerarios.tudominio.com` carga el mapa (candado HTTPS).
4. [ ] Registrarte con **un correo tuyo real**: llega el código de 6 dígitos (mira spam la primera vez).
5. [ ] Verificar el código → entras. Refrescar la página → **sigues dentro**. Cerrar sesión → vuelve al login.
6. [ ] Crear un vuelo para **dentro de menos de 24 h**: llega el correo de recordatorio **de inmediato**.
7. [ ] “Olvidé mi contraseña” → llega código → clave nueva → entras con ella.
8. [ ] Haz un cambio pequeño en una rama, abre PR, fusiona: aparece **CI** y luego **Deploy** en *Actions*,
       y el sitio se actualiza solo.
9. [ ] Reinicia el PC: Docker Desktop y el runner arrancan; el sitio vuelve (los contenedores tienen
       `restart: unless-stopped`).

## 8. Problemas frecuentes
| Síntoma | Causa probable |
|---|---|
| *Deploy* se queda “Waiting for a runner” | runner apagado o etiqueta distinta de `itinerarios` |
| `bash.exe` no existe | Git instalado en otra ruta: edita la ruta en `.github/workflows/deploy.yml` |
| Cloudflare: *Error 1033 / 502* | el túnel no conectó (revisa `docker compose -p itinerarios logs cloudflared`) o el servicio del *hostname* no es `traefik:80` |
| `pull access denied` para `cloudflared` | el tag fijado en `gateway/cloudflared/docker-compose.yml` no existe: usa uno reciente de las *releases* de cloudflared |
| No llega el correo / 503 al registrarse | contraseña de aplicación mal copiada, o la cuenta sin verificación en dos pasos; mira `docker compose -p itinerarios logs auth-stub` (aparece `fallo SMTP`, sin la clave) |
| Docker “no daemon” en el runner | el runner corre como servicio de otra cuenta; ejecútalo con tu usuario |
