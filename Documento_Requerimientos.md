# Documento de requerimientos

**Sistema de Itinerarios Personales**

Ingeniería de Sistemas y Computación · Facultad de Ingeniería y Ciencias Básicas · Universidad Central
Arquitecturas de software emergentes · 2026-2

---

## 1. Introducción y alcance

Este documento formaliza los requisitos funcionales y no funcionales del Sistema de Itinerarios Personales,
un sistema distribuido (monorepo de microservicios) que permite a un usuario registrarse y autenticarse,
consultar aeropuertos colombianos, visualizarlos en un mapa interactivo y gestionar itinerarios de viaje. El
sistema valida la coherencia de la agenda del viajero, notifica de forma asíncrona los eventos de creación,
actualización y borrado, y envía recordatorios de vuelo por correo electrónico.

El alcance cubre el Nivel 1 completo (obligatorio) y un subconjunto de Nivel 2 orientado a resiliencia,
seguridad y observabilidad mínima viable: Circuit Breaker, caché Redis con degradación en tres niveles,
API Gateway, broker de mensajería con contrato AsyncAPI, JWT con validación independiente en cada servicio y
despliegue continuo. Las capacidades de Nivel 3 (gRPC, Service Mesh, Chaos Engineering, Kubernetes, Vault,
Contract Testing) quedan documentadas como backlog futuro y no forman parte de esta versión.

### 1.1 Fuera de alcance

- Autenticación multifactor (MFA), *captcha* y límite de peticiones por IP real detrás del túnel
  (mitigaciones: tope de códigos por correo y global, bloqueo de cuenta; opcionalmente Cloudflare Access/WAF).
- Reservas reales, pagos o integración con aerolíneas. Los horarios los planifica el usuario y la duración se
  estima por distancia; no hay datos reales de aerolíneas ni estado de vuelo.
- Edición de datos de aeropuertos (el sistema es de solo lectura respecto de Airport).
- Roles y permisos diferenciados (administrador vs. usuario).
- Compartición de itinerarios entre usuarios.
- Trazas distribuidas y métricas (solo se emiten logs JSON con `X-Trace-Id`).

---

## 2. Arquitectura general

El navegador (o, en producción, el túnel `cloudflared`) solo habla con **Traefik**, el único punto de entrada,
que enruta por prefijo (`/` → frontend, `/api/auth`, `/api/airports`, `/api/itineraries`) y aplica el rate limit.
Hay tres microservicios HTTP y cada uno es dueño de su base de datos. Ningún servicio comparte base de datos
con otro: se comunican solo por HTTP o por eventos. Los servicios FastAPI siguen arquitectura hexagonal
(`domain` → `application` → `infrastructure`) y cada servicio con estado versiona su esquema con Alembic.

| Servicio | Responsabilidad | Tecnología |
|---|---|---|
| `frontend` | Dashboard, mapa de aeropuertos, CRUD de itinerarios | React 18, TypeScript, Vite, Plotly, nginx |
| `traefik` | Único punto de entrada, rate limit (20 req/s, ráfaga 40) | Traefik 3 (proveedor de archivo) |
| `auth-stub` | Identidad real: registro con código por correo, login con contraseña (scrypt), sesión por cookie `httpOnly`, emisión de JWT HS256. El nombre se conserva por compatibilidad con rutas, CI y documentación. | FastAPI + PostgreSQL (`postgres-auth`) |
| `airport-service` | Aeropuertos desde API Colombia con 3 niveles de resiliencia (Redis fresco → Redis stale → PostgreSQL) y Circuit Breaker | FastAPI, Redis, PostgreSQL |
| `itinerary-service` | CRUD de itinerarios (anti-IDOR, lista blanca de campos), validación de agenda y Transactional Outbox | FastAPI, PostgreSQL |
| `outbox-worker` | Relay outbox → RabbitMQ (confirms, `SKIP LOCKED`, reconexión) | Python, pika |
| `send-notification-function` | Consume el evento, registra la notificación (idempotente, DLQ) y programa el recordatorio | Python, pika, psycopg2 |
| `reminder-worker` | Envía por SMTP los recordatorios de vuelo programados (24 h antes de la salida real) | Python, SMTP |
| `mailpit` (solo desarrollo) | Captura los correos (códigos y recordatorios); interfaz en `:8025` | Mailpit |
| `cloudflared` (solo producción) | Túnel a Internet con dominio propio hacia Traefik | Cloudflare Tunnel |

**Flujo asíncrono.** `itinerary-service` guarda el itinerario y el evento en la tabla `outbox` en una sola
transacción. El `outbox-worker` lee los eventos `PENDING`, los publica en RabbitMQ (`itinerary.events`, con
*confirms*) y `send-notification-function` los consume, registra `notification_history` (idempotente) y programa
el recordatorio en `reminders`. El `reminder-worker` envía esos recordatorios por SMTP al correo verificado del
usuario. Los mensajes inválidos terminan en la DLQ `itinerary.events.dlq`.

---

## 3. Actores del sistema

| Actor | Tipo | Responsabilidad |
|---|---|---|
| Usuario final | Humano | Se registra, verifica su correo, inicia sesión, consulta aeropuertos, visualiza el mapa y crea, lee, actualiza y elimina sus itinerarios. Recibe recordatorios por correo. |
| Frontend Web | Sistema propio | React + Vite servido por nginx. Consume los servicios a través del Gateway y renderiza el mapa Plotly. Avisa conflictos de agenda antes de enviar. |
| API Gateway (Traefik) | Infraestructura propia | Único punto de entrada: ruteo por prefijo y rate limit. Sin lógica de negocio. |
| `auth-stub` (servicio de identidad) | Sistema propio | Registro, códigos de verificación y recuperación por correo, login, sesión y emisión de JWT HS256. |
| Airport Service | Sistema propio | Adapta API Colombia, cachea en Redis y PostgreSQL, y expone el contrato interno de aeropuertos. |
| Itinerary Service | Sistema propio | CRUD de itinerarios, validación de aeropuertos y de agenda, y publicación de eventos mediante Transactional Outbox. |
| `outbox-worker` | Sistema propio | Lee los eventos `PENDING` del outbox y los publica en RabbitMQ con *confirms*. |
| RabbitMQ | Infraestructura | Transporta los eventos de itinerario (cola `itinerary.events` y DLQ `itinerary.events.dlq`). |
| `send-notification-function` | Sistema propio | Consume el evento, registra la notificación de forma idempotente y programa, reprograma o cancela el recordatorio. |
| `reminder-worker` | Sistema propio | Envía por SMTP los recordatorios de vuelo vencidos al correo verificado del usuario. |
| Servidor SMTP | Infraestructura | Mailpit en desarrollo; SMTP real en producción. |
| `cloudflared` | Infraestructura (producción) | Túnel saliente hacia Cloudflare que publica Traefik en el dominio propio. |
| API Colombia | Sistema externo | Fuente de datos reales de aeropuertos colombianos. |

---

## 4. Requisitos funcionales

Convenciones: Prioridad (Alta/Media/Baja), Nivel (1/2/3 según la rúbrica del proyecto).

### 4.1 Aeropuertos

| ID | Nombre | Descripción | Prioridad | Nivel |
|---|---|---|---|---|
| RF-001 | Listar aeropuertos | El sistema debe permitir consultar el listado de aeropuertos colombianos, obtenidos y adaptados desde API Colombia (`GET /api/airports`). | Alta | 1 |
| RF-002 | Consultar aeropuerto por ID | El sistema debe exponer un endpoint para obtener el detalle de un aeropuerto por su identificador interno (`GET /api/airports/{id}`). | Alta | 1 |
| RF-003 | Visualizar aeropuertos en mapa | El frontend debe renderizar los aeropuertos en un mapa interactivo (Plotly), usando exclusivamente el formato adaptado por Airport Service. | Alta | 1 |
| RF-016 | Cachear respuestas de API externa | Airport Service debe servir los aeropuertos en tres niveles: Redis con datos frescos, Redis con datos *stale* y PostgreSQL como último respaldo, con invalidación por TTL. Los aeropuertos se cargan desde API Colombia en la primera consulta (no hay datos semilla). | Media | 2 |
| RF-017 | Aplicar Circuit Breaker | Airport Service debe abrir el circuito y responder con fallback controlado cuando API Colombia esté degradada o caída. Si el upstream y todos los respaldos fallan, responde 503. | Alta | 2 |

### 4.2 Itinerarios

| ID | Nombre | Descripción | Prioridad | Nivel |
|---|---|---|---|---|
| RF-004 | Crear itinerario | El sistema debe permitir crear un itinerario con `nombre_usuario`, aeropuerto de origen, aeropuerto de destino, fecha y hora de salida (instante ISO 8601 **con zona**) y duración en minutos. La llegada se calcula como salida + duración. Responde 201 `{id}`. | Alta | 1 |
| RF-005 | Validar aeropuertos al crear | Antes de persistir un itinerario, el sistema debe verificar por HTTP, con Circuit Breaker, que ambos aeropuertos existan en Airport Service. Si Airport Service no está disponible responde 502. | Alta | 1 |
| RF-006 | Rechazar origen = destino | El sistema debe rechazar con 422 un itinerario cuyo origen sea igual al destino. | Alta | 1 |
| RF-007 | Consultar itinerario(s) | El sistema debe permitir consultar un itinerario por ID y listar los itinerarios del usuario autenticado, ordenados por salida e incluyendo `departure_at` y `arrival_at`. | Alta | 1 |
| RF-008 | Actualizar itinerario | El sistema debe permitir modificar un itinerario propio, re-validando aeropuertos y agenda. Solo se aceptan los campos de una lista blanca. | Media | 1 |
| RF-009 | Eliminar itinerario | El sistema debe permitir eliminar un itinerario propio. | Media | 1 |
| RF-013 | Tiempo al próximo vuelo | El panel del frontend debe mostrar el tiempo que falta para el próximo vuelo del usuario. | Baja | 2 |
| RF-026 | Validar la agenda del viajero | Al crear o editar un vuelo, el servidor debe validar la agenda del usuario dentro de la misma transacción, con bloqueo por usuario (`pg_advisory_xact_lock`), y responder 409 `{detail, code, conflicting_itinerary_id}` si ocurre: `OVERLAP` (se cruza en el tiempo con otro vuelo), `ORIGIN_MISMATCH` (no sale desde donde aterrizó el vuelo anterior) o `NEXT_MISMATCH` (no termina donde sale el vuelo siguiente). | Alta | 2 |
| RF-027 | Margen mínimo de conexión | El sistema debe permitir exigir un margen mínimo entre aterrizar y volver a salir, configurable con `MIN_CONNECTION_MINUTES` (por defecto 0). | Baja | 2 |
| RF-028 | Aislamiento por usuario | Un usuario solo debe poder ver, editar y borrar sus propios itinerarios (anti-IDOR). Si el itinerario no es suyo o el id no es un UUID, el sistema responde 404. | Alta | 2 |
| RF-029 | Asistencia en el frontend | El frontend debe avisar de un conflicto de agenda antes de enviar, sugerir desde qué ciudad y hora puede salir el usuario y estimar la duración por distancia (estimación, no horario real de aerolínea). El servidor es la autoridad. | Media | 2 |

### 4.3 Eventos y notificaciones

| ID | Nombre | Descripción | Prioridad | Nivel |
|---|---|---|---|---|
| RF-010 | Publicar evento | Al crear, actualizar o eliminar un itinerario, el sistema debe registrar un evento (`ItineraryCreatedEvent`, `Updated`, `Deleted`) en la tabla `outbox` dentro de la misma transacción de escritura. | Alta | 1 |
| RF-011 | Despachar eventos pendientes | El `outbox-worker` debe leer los eventos `PENDING` (con `SKIP LOCKED`) y publicarlos en RabbitMQ con *confirms* y reconexión, marcándolos `PUBLISHED`. | Alta | 2 |
| RF-012 | Procesar notificación | `send-notification-function` debe consumir el evento, registrar una fila en `notification_history` de forma idempotente por `itinerary_id` (canal `log-simulado`) y programar el recordatorio en `reminders`. | Alta | 1 |
| RF-030 | Dead Letter Queue | Los mensajes inválidos o no procesables deben enviarse a la cola `itinerary.events.dlq` sin bloquear la cola principal. | Media | 2 |
| RF-031 | Recordatorio de vuelo por correo | El `reminder-worker` debe enviar por SMTP un recordatorio al **correo verificado** de la cuenta 24 h antes de la salida real (`REMINDER_LEAD_HOURS`). Si el vuelo sale en menos de 24 h, el aviso se envía de inmediato. | Alta | 2 |
| RF-032 | Reprogramar y cancelar recordatorio | Los eventos `Updated` y `Deleted` deben reprogramar o cancelar el recordatorio asociado. | Media | 2 |

### 4.4 Identidad y acceso

| ID | Nombre | Descripción | Prioridad | Nivel |
|---|---|---|---|---|
| RF-014 | Autenticar usuario | El sistema debe permitir iniciar sesión con correo y contraseña (`POST /api/auth/login`), devolviendo `{access_token, token_type, expires_in_minutes, name, email}` y una cookie `httpOnly`. El token JWT (HS256) debe incluir `exp`. | Alta | 2 |
| RF-015 | Propagar identidad | El Gateway debe propagar el JWT hacia los servicios internos sin modificarlo, y cada servicio debe validarlo de forma independiente (Bearer, `exp`, `user_id`). | Media | 2 |
| RF-019 | Registrar cuenta | El sistema debe permitir registrar una cuenta con correo, nombre y contraseña de mínimo 10 caracteres (`POST /api/auth/register`, 202). La contraseña se almacena con scrypt y la cuenta queda sin verificar. | Alta | 2 |
| RF-020 | Verificar correo por código | El sistema debe enviar por SMTP un código de 6 dígitos que vence en 10 min, es de un solo uso y admite 5 intentos. Sin verificarlo no hay sesión ni recordatorios (`POST /api/auth/verify`, `POST /api/auth/resend`). | Alta | 2 |
| RF-021 | Mantener la sesión | La sesión debe sobrevivir al refrescar la página mediante cookie `httpOnly` con `SameSite=Strict`; el JWT vive solo en memoria. Deben existir `POST /api/auth/refresh` y `POST /api/auth/logout`. | Media | 2 |
| RF-022 | Recuperar contraseña | El sistema debe permitir recuperar la contraseña por código enviado al correo (`POST /api/auth/forgot`, `POST /api/auth/reset`). | Media | 2 |
| RF-023 | Bloqueo por intentos fallidos | El sistema debe bloquear la cuenta 15 min tras 5 contraseñas erróneas y responder igual exista o no la cuenta. | Media | 2 |
| RF-024 | Limitar envío de códigos | El sistema debe limitar los códigos a 5 por hora y por correo y a 100 por hora en total (`MAX_CODES_PER_HOUR`, `MAX_CODES_PER_HOUR_GLOBAL`). | Media | 2 |

### 4.5 Documentación

| ID | Nombre | Descripción | Prioridad | Nivel |
|---|---|---|---|---|
| RF-018 | Documentar API (Swagger) | Cada microservicio debe exponer documentación OpenAPI/Swagger navegable y un `GET /health`. | Alta | 1 |

---

## 5. Interfaz de la API

| Servicio | Endpoints |
|---|---|
| auth | `POST /api/auth/register` `{email, name, password}` (202) · `POST /api/auth/verify` `{email, code}` → sesión · `POST /api/auth/login` `{email, password}` → `{access_token, token_type, expires_in_minutes, name, email}` (+ cookie `httpOnly`) · `POST /api/auth/refresh` · `POST /api/auth/logout` · `POST /api/auth/resend` · `POST /api/auth/forgot` · `POST /api/auth/reset` `{email, code, password}` |
| airports | `GET /api/airports`, `GET /api/airports/{id}` |
| itineraries (Bearer JWT) | `POST /api/itineraries` `{nombre_usuario, origin_airport_id, destination_airport_id, departure_at, duration_minutes}` (201 `{id}`), `GET /api/itineraries`, `GET/PUT/DELETE /api/itineraries/{id}` |
| todos | `GET /health` |

`departure_at` es un instante ISO 8601 **con zona** (por ejemplo `2026-12-01T06:00:00-05:00`); la llegada se
calcula como salida + `duration_minutes`.

**Códigos de error.**

| Código | Situación |
|---|---|
| 401 / 403 | Sin token válido (el token debe traer `exp`) |
| 404 | El itinerario no es del usuario o el id no es UUID |
| 409 | El vuelo no es coherente con la agenda (`OVERLAP`, `ORIGIN_MISMATCH`, `NEXT_MISMATCH`) |
| 422 | Validación, aeropuerto inexistente, origen = destino, salida sin zona o en el pasado |
| 502 | Airport Service no disponible |
| 503 | La base de datos no responde, o el upstream de aeropuertos y sus respaldos fallan |

---

## 6. Requisitos no funcionales

| ID | Categoría | Descripción | Métrica / criterio | Nivel |
|---|---|---|---|---|
| RNF-001 | Rendimiento | Las respuestas de Airport Service con aeropuertos cacheados deben ser rápidas. | P95 < 200 ms con caché caliente (contrastar con los reportes de Locust) | 2 |
| RNF-002 | Disponibilidad | El fallo de API Colombia no debe tumbar Airport Service. | Fallback activo con Circuit Breaker abierto; 0 % de errores 5xx propagados al frontend mientras haya respaldo | 2 |
| RNF-003 | Resiliencia | Las llamadas HTTP salientes (de `itinerary-service` a `airport-service` y de `airport-service` a API Colombia) deben protegerse con Circuit Breaker. | El circuito se abre ante fallos repetidos y se aplica el fallback | 2 |
| RNF-004 | Consistencia | La publicación del evento no debe perderse ni duplicar el registro de negocio (Double Write Problem resuelto con Transactional Outbox). | 0 pérdidas de evento verificadas por `e2e_resilience.py` (cae RabbitMQ con itinerarios en curso) | 1 |
| RNF-005 | Observabilidad | Todos los servicios deben emitir logs estructurados en JSON. | Logs JSON en todos los servicios | 1 |
| RNF-006 | Trazabilidad | Las peticiones deben poder seguirse en los logs mediante un identificador de correlación. | Cabecera `X-Trace-Id` en los logs JSON | 1 |
| RNF-007 | Seguridad de API | Los endpoints de itinerarios deben requerir JWT válido con `exp`; cada servicio lo valida de forma independiente. | 401/403 en tokens ausentes, inválidos o expirados | 2 |
| RNF-008 | Mantenibilidad | Cada servicio FastAPI debe seguir arquitectura hexagonal (`domain` → `application` → `infrastructure`). | 0 dependencias de infraestructura en el dominio | 1 |
| RNF-009 | Escalabilidad | Cada microservicio debe poder escalar horizontalmente de forma independiente, sin estado en memoria compartido entre réplicas. | Servicios sin estado local | 2 |
| RNF-010 | Interoperabilidad | Los contratos entre servicios deben documentarse. | OpenAPI para HTTP y `docs/asyncapi.yaml` para eventos | 1/2 |
| RNF-011 | Testabilidad | El flujo completo debe ser verificable con pruebas reproducibles en CI. | Pruebas unitarias y de integración con PostgreSQL real; E2E `e2e_smoke.py` (login → itinerario → outbox → RabbitMQ → notificación, idempotencia, DLQ) y `e2e_resilience.py` | 2 |
| RNF-012 | Despliegue | Todo el sistema debe desplegarse con un único comando. | `docker compose up -d --build` levanta el sistema completo | 1 |
| RNF-013 | Seguridad de cuentas | Las contraseñas se almacenan con scrypt; las respuestas no revelan si una cuenta existe; la sesión usa cookie `httpOnly` y `SameSite=Strict`; el frontend se sirve con cabeceras CSP, `nosniff` y `X-Frame-Options`. | Verificado con pruebas y navegador (Chromium) | 2 |
| RNF-014 | Gestión de secretos | Ningún secreto debe estar en Git; `JWT_SECRET` (≥ 32 caracteres, idéntico en `auth-stub` e `itinerary-service`) y las claves de BD y RabbitMQ se generan con `bootstrap-env.sh`. | gitleaks en CI; el servicio rechaza un `JWT_SECRET` corto | 1 |
| RNF-015 | Migraciones | Cada servicio con estado debe versionar su esquema con Alembic y aplicarlo al arrancar con *advisory lock*, adoptando bases existentes sin borrar datos (`0001_baseline`). | `alembic upgrade head` automático | 1 |
| RNF-016 | Integración y despliegue continuo | Cada push o PR debe ejecutar CI (tests con PostgreSQL real, frontend, build de Compose, E2E, gitleaks, trivy y SonarCloud opcional). Solo `main` con CI en verde despliega, mediante runner autoalojado y túnel `cloudflared`. | Definido en `docs/despliegue.md` y `.github/workflows/ci.yml` | 2 |
| RNF-017 | Carga | El sistema debe contar con pruebas de carga reproducibles. | Locust, perfiles y reportes en `docs/evidencias/locust/` | 2 |

---

## 7. Reglas de negocio

| ID | Regla |
|---|---|
| RN-001 | Un itinerario debe tener exactamente un aeropuerto de origen y uno de destino. |
| RN-002 | El aeropuerto de origen y el de destino no pueden ser el mismo. |
| RN-003 | Ambos aeropuertos deben existir en Airport Service al momento de crear o actualizar el itinerario. |
| RN-004 | La salida debe ser un instante ISO 8601 **con zona horaria** y **no puede estar en el pasado**; en caso contrario se responde 422. Todas las horas se interpretan en Colombia (UTC-5). |
| RN-005 | La duración se expresa en minutos y debe ser un entero mayor que cero. |
| RN-006 | Cada creación, actualización o borrado exitoso de un itinerario genera exactamente un evento de integración (`Created`, `Updated`, `Deleted`). |
| RN-007 | El snapshot de datos de aeropuerto guardado en el itinerario (IATA, nombre, ciudad) no se actualiza retroactivamente si el aeropuerto cambia en el origen. |
| RN-008 | Un itinerario pertenece a un único usuario, identificado por el `user_id` del JWT; no existe compartición entre usuarios. |
| RN-009 | Dos vuelos de un mismo usuario no pueden solaparse en el tiempo (`OVERLAP`). |
| RN-010 | Un vuelo debe salir desde el aeropuerto donde aterrizó el vuelo anterior del usuario (`ORIGIN_MISMATCH`). Se permite salir a la hora exacta de llegada o después. |
| RN-011 | Un vuelo debe terminar en el aeropuerto desde el que sale el vuelo siguiente del usuario (`NEXT_MISMATCH`). |
| RN-012 | Entre aterrizar y volver a salir debe haber al menos `MIN_CONNECTION_MINUTES` (por defecto 0). |
| RN-013 | La agenda no se revalida al borrar un vuelo: quitar uno intermedio puede dejar tramos desconectados. Es una decisión consciente, porque el usuario pudo cancelar o viajar por otro medio. |
| RN-014 | El recordatorio se envía 24 h antes de la salida real, o de inmediato si faltan menos de 24 h, y **solo al correo verificado** de la cuenta. |
| RN-015 | Sin verificar el correo no hay sesión. El código de verificación dura 10 min, es de un solo uso y admite 5 intentos. |
| RN-016 | Tras 5 contraseñas erróneas la cuenta se bloquea 15 min. |

**Distinción regla de negocio vs. regla técnica.** RN-001 a RN-016 son reglas de negocio (invariantes del dominio
y de la identidad). El uso de Redis, Circuit Breaker, Outbox, JWT, scrypt, la DLQ y el túnel `cloudflared` son
decisiones técnicas de soporte y se documentan como ADR en el documento de arquitectura.

---

## 8. Configuración y despliegue

**Requisitos previos.** Docker Desktop (o Engine) con Compose ≥ 2.20 y un shell bash (Git Bash o WSL en
Windows) para `scripts/bootstrap-env.sh`. Python 3 solo se requiere para las pruebas de humo y, para desarrollar,
Python 3.11 y Node 20+.

**Arranque.**

```bash
./scripts/bootstrap-env.sh            # genera los .env con secretos aleatorios y crea la red itinerarios-net
docker compose up -d --build          # levanta todos los contenedores
docker compose ps                     # esperar a que todos estén "healthy"
```

Sin acceso a API Colombia se usa `docker-compose.mock.yml` (datos de prueba).

**Variables de entorno principales.**

| Archivo | Variables |
|---|---|
| `services/auth-stub/.env` | `JWT_SECRET`, `DATABASE_URL`, SMTP (en desarrollo, Mailpit) |
| `services/airport-service/.env` | `DATABASE_URL`, `REDIS_URL`, opcional `API_COLOMBIA_BASE_URL` |
| `services/itinerary-service/.env` | `DATABASE_URL`, `RABBITMQ_URL`, `AIRPORT_SERVICE_URL`, `JWT_SECRET` (≥ 32 caracteres), opcional `MIN_CONNECTION_MINUTES` |
| `services/notification-function/.env` | `DATABASE_URL`, `RABBITMQ_URL`, SMTP y `REMINDER_LEAD_HOURS` |
| `frontend/.env` | `VITE_API_BASE_URL` (vacío = mismo origen) |

**Puertos de desarrollo** (solo en `127.0.0.1`): aplicación `:80` y `:5173`, Mailpit `:8025`, consola de RabbitMQ
`:15672`, Swagger en `:8001` (aeropuertos), `:8002` (itinerarios) y `:8003` (auth).

**Despliegue continuo.** Cada cambio en `main` con CI en verde se despliega con un runner autoalojado en el
servidor de producción, que ejecuta Compose con el perfil de producción. `cloudflared` publica Traefik en el
dominio propio mediante un túnel saliente (HTTPS), sin abrir puertos. Procedimiento completo en `docs/despliegue.md`.

---

## 9. Preguntas resueltas (antes abiertas)

| Pregunta | Decisión |
|---|---|
| ¿Nivel de alcance? | Nivel 1 + Nivel 2 dirigido (ver sección 1). |
| ¿Qué es «usuario»? | Cuenta real con correo verificado, identificada por el `user_id` del JWT. Se conserva `nombre_usuario` en el itinerario. |
| ¿JWT real o simulado? | Real: HS256 con `exp`, emitido tras login con contraseña y verificación de correo. |
| ¿Redis y observabilidad obligatorios ya? | Logs estructurados con `X-Trace-Id`: sí (Nivel 1). Redis: sí (Nivel 2). Trazas distribuidas y métricas: backlog. |
| ¿Notification Service o Function? | Proceso consumidor dedicado (`send-notification-function`) más `reminder-worker`, ambos en Python. |
| ¿Origen = destino? | Rechazado (422). |
| ¿Motor de base de datos? | PostgreSQL, una base por servicio con estado (`postgres-auth`, `postgres-airport`, `postgres-itinerary`, `postgres-notification`). |
| ¿Broker? | RabbitMQ con cola `itinerary.events` y DLQ `itinerary.events.dlq`. |
| ¿Runtime de las funciones? | Contenedores Python orquestados con docker-compose. |
| ¿Duración? | Minutos de vuelo, entero positivo. |
| ¿Aeropuerto deja de existir? | No afecta itinerarios ya creados (snapshot inmutable); solo se valida al crear o actualizar. |
| ¿Fecha futura obligatoria? | Sí: la salida no puede estar en el pasado y debe incluir zona horaria. |
| ¿Cómo se publica en Internet? | Túnel `cloudflared` hacia Traefik con dominio propio; despliegue por runner autoalojado. |
| ¿Cómo se envía el correo? | Mailpit en desarrollo; SMTP real en producción. |

---

## 10. Limitaciones conocidas

- Compose en desarrollo lo ejecutó el autor con la versión anterior; la versión con identidad real, el perfil de
  producción (`cloudflared`) y el despliegue por runner no se han ejecutado todavía en Docker (se probaron los
  servicios como procesos nativos).
- Identidad: sin MFA, sin captcha y sin límite por IP real detrás del túnel.
- El correo se probó contra un sumidero SMTP propio (`tools/smtp_sink.py`), no contra Mailpit ni Gmail real.
- Los horarios son planificados por el usuario (la duración se estima por distancia); no hay datos reales de
  aerolíneas ni estado de vuelo. Todas las horas se interpretan en Colombia (UTC-5).
- Sin trazas distribuidas ni métricas (solo logs JSON con `X-Trace-Id`).
- El despliegue continuo y la URL pública están definidos pero no verificados de extremo a extremo.
- El rate limit de Traefik es por IP; las pruebas de carga se hicieron contra los puertos directos, no por el Gateway.
- Si existía una cola `itinerary.events` sin argumentos (versión anterior), debe borrarse
  (`docker compose down -v`) para evitar `PRECONDITION_FAILED`.

---

## 11. Criterios de aceptación del documento

- Todo RF y RNF tiene ID único, prioridad o nivel y, cuando aplica, una métrica verificable.
- Toda regla de negocio está separada de las decisiones técnicas.
- Toda pregunta abierta de la fase de descubrimiento tiene una decisión registrada y trazable al documento de arquitectura.
- Los requisitos de Nivel 1 son suficientes y necesarios para una demo funcional completa sin depender de Nivel 2.
