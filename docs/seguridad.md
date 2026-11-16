# Seguridad (Sprint 10) — estado real

Leyenda: ✅ confirmado (ejecutado) · 🟡 implementado, no validado · ⏳ pendiente.
Evidencia: [`evidencias/seguridad-auditoria.txt`](evidencias/seguridad-auditoria.txt).

## Dependencias
| Qué | Estado | Detalle |
|---|---|---|
| Auditoría de los 4 `requirements.lock` con `pip-audit` | ✅ | **0 vulnerabilidades conocidas** el 2026-11-04. La auditoría inicial encontró `starlette 0.38.6` (7 avisos, vía `fastapi 0.115.0`), `python-jose 3.3.0` (4 avisos) y `pyasn1 0.4.8` (3 avisos) |
| `fastapi 0.115.0 → 0.162.0` (arrastra `starlette 1.10.0`) | ✅ | tras subirlo pasan todas las suites (unitarias, integración, E2E, resiliencia, fallos y carga) |
| `python-jose → PyJWT 2.15.0` | ✅ | `python-jose` fija `pyasn1<0.5` (vulnerable) y tiene avisos sin parche; solo se usaba HS256 en 2 archivos, así que se migró. `exp` sigue siendo obligatorio (`options={"require": ["exp"]}`) |
| Locks con hashes (`--require-hashes`) | ✅ | regenerados con `uv pip compile --generate-hashes`; instalación real con `--require-hashes --only-binary=:all:` |
| Dependabot | 🟡 | `.github/dependabot.yml` configurado; no ejecutado en GitHub |
| Frontend `npm audit --omit=dev` | ✅ | 0 (las 7 de desarrollo siguen sin aplicarse `--force` a ciegas) |

Los upgrades **no** se aplicaron a ciegas: cada uno se resolvió, se instaló desde el lock con hashes y se volvió a ejecutar todo el conjunto de pruebas.

## Código y secretos
| Qué | Estado | Detalle |
|---|---|---|
| `bandit` (SAST) sobre servicios, tools y scripts | ✅ | **0 hallazgos** con `.bandit`. Se corrigieron/justificaron: SQL con ids en scripts E2E (ahora validados como UUID antes de interpolar), `0.0.0.0` en herramientas de desarrollo, `urlopen` del cliente de pruebas |
| `JWT_SECRET` mínimo 32 caracteres | ✅ | el servicio **no arranca** con un secreto más corto (RFC 7518 §3.2); `bootstrap-env.sh` genera 48 |
| Secretos fuera de git | ✅ | `*.env` ignorados; plantillas con `@@TOKEN@@`; contraseñas aleatorias |
| `gitleaks` | 🟡 | job en CI; no ejecutado en GitHub |
| `trivy` (imágenes/dependencias) | 🟡 | job en CI (informativo); **no se construyeron imágenes** (sin Docker Hub) |

## Identidad y sesión (cuentas reales)
| Qué | Estado | Detalle |
|---|---|---|
| Contraseñas | ✅ | `scrypt` (N=2^15, r=8, p=3, sal aleatoria, parámetros dentro del hash), comparación en tiempo constante; mínimo 10 caracteres |
| Verificación del correo | ✅ | código de 6 dígitos, 10 min, un solo uso, **5 intentos contados de forma atómica en SQL** (prueba con 100 hilos: solo 5 pasan), guardado como HMAC-SHA256 con clave del servidor |
| Sin enumeración de cuentas | ✅ | registro, reenvío y olvido responden igual exista o no la cuenta; login con mensaje único y verificación ficticia si el usuario no existe |
| Bloqueo y topes | ✅ | 5 contraseñas erróneas → 15 min; 60 s entre códigos, 5/h por correo, 100/h globales (protege la cuota de Gmail y a terceros) |
| Sesión | ✅ | token de acceso JWT de 30 min **solo en memoria**; sesión de 14 días en cookie `httpOnly` + `SameSite=Strict` + `Secure` (producción), path `/api/auth`, guardada como SHA-256; logout y cambio de contraseña la revocan |
| Recordatorios solo al correo verificado | ✅ | el claim `email` solo se emite tras verificar; ya no existe `POST /api/auth/token` (probado: 404) |
| Cabeceras web | ✅ en navegador · 🟡 en nginx real | CSP (sin scripts externos ni inline), `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`; el mapa Plotly funciona bajo esa CSP (Chromium), pero nginx no se ejecutó aquí |
| SMTP | ✅ | `STARTTLS` con verificación de certificado; los errores no registran credenciales ni el código |
| Sin captcha, MFA ni límite por IP real | ⏳ decisión | detrás del túnel todos llegan desde un contenedor; mitigar con Cloudflare WAF/Access (ver `despliegue.md` §6) |

## Infraestructura
| Qué | Estado |
|---|---|
| Traefik sin socket de Docker; puertos de BD/servicios en `127.0.0.1` | ✅ (por revisión de `docker compose config`) |
| RabbitMQ sin usuario `guest`, credenciales por `rabbitmq.env` | ✅ por configuración; ⏳ arranque real en Compose |
| Endurecimiento de contenedores (`read_only`, `cap_drop: [ALL]`, `no-new-privileges`) | ⏳ **no aplicado**: no se puede probar sin Docker y un cambio ciego podría impedir el arranque |
| Cabeceras de seguridad (CSP, HSTS, etc.) en nginx/Traefik | ⏳ pendiente |
| Contraseñas/registro de usuarios | ⏳ el `auth-stub` sigue sin contraseña (decisión del alcance) |
