# Despliegue continuo y publicación con Cloudflare Tunnel

Objetivo: cada cambio fusionado a `main` que pase la integración continua (CI) se construye y se actualiza
automáticamente en el Docker Desktop del equipo anfitrión, y el sitio queda público en el dominio propio
**sin abrir puertos del router**.

```
GitHub (main) ──CI en verde──► runner propio (equipo anfitrión) ──► scripts/deploy.sh ──► docker compose up -d --build
                                                                                               │
Internet ──► Cloudflare (HTTPS, dominio propio) ══ túnel ══► cloudflared ► traefik ► frontend / servicios
```

> **Estado de verificación.** Se probaron: las pruebas automatizadas, el flujo completo de
> registro, verificación y alertas sobre PostgreSQL, RabbitMQ y SMTP reales en proceso nativo, y el
> navegador (Chromium) con las cabeceras de seguridad. **No se pudieron probar** en el entorno de desarrollo
> (sin Docker ni acceso a las cuentas de GitHub, Cloudflare o Gmail): el `docker compose` de producción, el
> runner, el túnel y el envío real por Gmail. Para ello se incluye la lista de comprobación de la sección 7,
> que debe ejecutarse una vez; ante cualquier fallo, conviene registrar el mensaje de error para su análisis.

## 0. Requisitos

| Elemento | Detalle |
|---|---|
| Equipo con Windows 10/11, Docker Desktop y **Git for Windows** (incluye Git Bash) | Debe permanecer encendido mientras el sitio deba estar disponible |
| Dominio en Cloudflare | Dominio registrado en Hostinger, con los *nameservers* de Cloudflare ya configurados |
| Cuenta de Gmail | Con **verificación en dos pasos** activa, necesaria para crear una contraseña de aplicación |
| Repositorio en GitHub | Donde se fusionan los cambios a `main` |

## 1. Gmail: contraseña de aplicación

1. En la cuenta de Google, ir a *Seguridad* y activar la **verificación en dos pasos**.
2. Buscar **«Contraseñas de aplicaciones»**, crear una (nombre sugerido: `itinerarios`) y copiar los 16 caracteres.
3. **No debe pegarse en chats ni en el repositorio.** Se introduce únicamente en el paso 4.

Límites reales de Gmail: aproximadamente 500 correos al día. La aplicación se protege con un tope de
**100 códigos por hora** en total y 5 por hora y por correo (`MAX_CODES_PER_HOUR_GLOBAL`, `MAX_CODES_PER_HOUR`).

## 2. Cloudflare: túnel

1. En el panel de Cloudflare: **Zero Trust** → *Networks* → **Tunnels** → *Create a tunnel* → tipo **Cloudflared**.
2. Nombre: `itinerarios`. En «Install and run», copiar **únicamente el token** (la cadena larga posterior a `--token`).
3. En la pestaña **Published application / Public hostname**, seleccionar *Add*:
   - Subdomain: `itinerarios` · Domain: el dominio propio (resulta `itinerarios.<dominio>`).
   - Service: **Type `HTTP`** · URL **`traefik:80`** (nombre del contenedor, no `localhost`).
4. En *SSL/TLS* del dominio, dejar el modo **Full** o **Flexible** (el túnel ya viaja cifrado hasta Cloudflare)
   y activar *Always Use HTTPS*.

## 3. Runner de GitHub en el equipo (una sola vez)

1. En el repositorio: *Settings* → *Actions* → *Runners* → **New self-hosted runner** → Windows x64. Seguir los
   comandos que muestra GitHub (descarga y `config.cmd`). Cuando solicite **etiquetas**, indicar:
   `itinerarios`.
2. Ejecutarlo **con el usuario de Windows** (no como servicio de otra cuenta), ya que Docker Desktop solo
   funciona dentro de la sesión del usuario. Hay dos opciones:
   - Manual: `./run.cmd` en la carpeta del runner (debe dejarse abierto).
   - Automática: *Programador de tareas* → tarea «Al iniciar sesión» que ejecute `run.cmd`.
3. En Docker Desktop: *Settings* → *General* → activar **Start Docker Desktop when you sign in**.
4. En GitHub: *Settings* → *Actions* → *General* → «Fork pull request workflows»: **Require approval for all
   outside collaborators**. Un runner propio ejecuta código en el equipo anfitrión, por lo que nunca debe
   usarse con pull requests de terceros (el workflow de despliegue solo corre sobre `main`, nunca sobre pull requests).
5. Opcional: *Settings* → *Environments* → **production** → *Required reviewers*, lo que exige una aprobación
   manual antes de cada despliegue (en repositorios privados requiere un plan de pago).

## 4. Secretos de producción (una sola vez, en el equipo anfitrión)

En Git Bash, dentro de una copia del repositorio:

```bash
./scripts/configure-prod.sh
```

El script solicita el Gmail, la contraseña de aplicación y el token del túnel (**sin mostrarlos**) y crea
`~/itinerarios-config/prod.env` con permisos 600. Ese archivo **no** está en el repositorio ni en GitHub.
Las contraseñas de las bases de datos y el `JWT_SECRET` los genera el propio despliegue la primera vez
(valores aleatorios) y los guarda en la misma carpeta para que no cambien entre despliegues.

> Para cambiar el SMTP o el túnel posteriormente, se vuelve a ejecutar el script y se realiza un despliegue (sección 5).

## 5. Primer despliegue y siguientes

- **Primer despliegue manual** (para observar los errores en vivo): en Git Bash, `./scripts/deploy.sh`.
- **Despliegue automático**: al fusionar un PR a `main` se ejecuta **CI** y, si termina en verde, **Deploy**
  (pestaña *Actions*). También puede lanzarse desde *Actions → Deploy → Run workflow* (solo sobre `main`).
- El script realiza, en orden: restauración de secretos → completado de los `.env` faltantes →
  `docker compose up -d --build` → espera a que todos los contenedores estén *healthy* → prueba de humo
  (`/`, `/api/airports` y `/api/auth/refresh`, que debe responder 401) → termina con código distinto de 0 y
  muestra los logs si algo no quedó correcto.
- Los datos (PostgreSQL) residen en volúmenes de Docker del proyecto `itinerarios` y **se conservan** entre
  despliegues. Las migraciones se aplican automáticamente al arrancar cada servicio.

## 6. Control de acceso

Cualquier persona que llegue al sitio puede **crear una cuenta** con correo, contraseña propia (mínimo 10
caracteres) y un **código de 6 dígitos** enviado a ese correo (vence en 10 min, es de un solo uso y admite
máximo 5 intentos). Mientras el correo no se verifique no hay sesión ni recordatorios. Los recordatorios de
vuelo se envían únicamente al correo **verificado** de la cuenta, nunca a uno ingresado manualmente.

Protecciones incluidas:

- Contraseñas almacenadas con scrypt.
- Bloqueo de 15 min tras 5 contraseñas erróneas.
- Respuestas idénticas exista o no la cuenta.
- Sesión en cookie `httpOnly` con `SameSite=Strict`.
- Límites de envío por correo y global.
- Cabeceras CSP, `nosniff` y `X-Frame-Options`.

Elementos **no incluidos** (decisión deliberada, ver `docs/seguridad.md`): *captcha*, límite por IP real
(detrás del túnel todas las peticiones llegan desde el mismo contenedor) y MFA.

Para restringir el sitio a personas concretas (por ejemplo, el docente y un compañero), la opción más simple es
**Cloudflare Access** (Zero Trust → Access → Applications → *Self-hosted* → política «Emails: lista») sobre el
mismo hostname. Es gratuito hasta 50 usuarios y se configura solo desde el panel, sin modificar el código.
Para frenar bots: *Security → WAF → Rate limiting rules* sobre `/api/auth/*` (por ejemplo, 20 peticiones por
minuto por IP).

## 7. Lista de comprobación

Debe ejecutarse una vez en el equipo anfitrión; ante cualquier fallo, registrar el mensaje de error.

1. [ ] `./scripts/configure-prod.sh` termina sin error y crea `~/itinerarios-config/prod.env`.
2. [ ] `./scripts/deploy.sh` termina con «Despliegue correcto» y la tabla muestra `cloudflared` en estado *Up*.
3. [ ] `https://itinerarios.<dominio>` carga el mapa (con candado HTTPS).
4. [ ] El registro con un correo real envía el código de 6 dígitos (revisar la carpeta de spam la primera vez).
5. [ ] Al verificar el código se inicia sesión; al refrescar la página la sesión persiste; al cerrar sesión se regresa al login.
6. [ ] Al crear un vuelo para dentro de menos de 24 h, el correo de recordatorio llega **de inmediato**.
7. [ ] «Olvidé mi contraseña» envía un código; con la clave nueva se puede iniciar sesión.
8. [ ] Un cambio pequeño en una rama, con PR y fusión, dispara **CI** y luego **Deploy** en *Actions*, y el sitio se actualiza solo.
9. [ ] Tras reiniciar el equipo, Docker Desktop y el runner arrancan y el sitio vuelve a estar disponible
       (los contenedores tienen `restart: unless-stopped`).

## 8. Problemas frecuentes

| Síntoma | Causa probable |
|---|---|
| *Deploy* queda en «Waiting for a runner» | Runner apagado o con una etiqueta distinta de `itinerarios` |
| `bash.exe` no existe | Git instalado en otra ruta; debe editarse la ruta en `.github/workflows/deploy.yml` |
| Cloudflare: *Error 1033 / 502* | El túnel no conectó (revisar `docker compose -p itinerarios logs cloudflared`) o el servicio del *hostname* no es `traefik:80` |
| `pull access denied` para `cloudflared` | El tag fijado en `gateway/cloudflared/docker-compose.yml` no existe; usar uno reciente de las *releases* de cloudflared |
| No llega el correo / 503 al registrarse | Contraseña de aplicación mal copiada o cuenta sin verificación en dos pasos; revisar `docker compose -p itinerarios logs auth-stub` (aparece `fallo SMTP`, sin la clave) |
| Docker «no daemon» en el runner | El runner corre como servicio de otra cuenta; debe ejecutarse con el usuario de la sesión |
