# Evidencias

## Generadas por ejecución real (en esta carpeta)
| Evidencia | Archivo | Entorno |
|---|---|---|
| Flujo extremo a extremo (16 comprobaciones) | `e2e-smoke.txt` | procesos nativos, ver `entorno.md` |
| Resiliencia: caída de RabbitMQ | `e2e-resilience.txt` | idem |
| Pruebas backend / frontend | `pruebas.txt` | local |
| Carga (Locust) CSV + HTML | `locust/` | idem; ver `docs/pruebas-de-carga.md` |

## Requieren acción manual (NO se generaron ni se simulan)
| Evidencia | Cómo obtenerla |
|---|---|
| Interfaz y mapa | `docker compose up`, abrir <http://localhost>, captura del dashboard y del mapa |
| Creación de itinerario en la UI | captura del formulario y del itinerario en la lista |
| Evento y notificación | captura de `docker compose logs outbox-worker send-notification-function` y del `select * from notification_history` |
| `docker compose ps` con todo *healthy* | captura/terminal tras `docker compose up -d --build` (**primera ejecución real de Compose: pendiente**) |
| Pipeline de GitHub Actions | captura de la ejecución en la pestaña Actions tras abrir el PR |
| Quality Gate de SonarCloud | configurar `SONAR_TOKEN`/variables, ejecutar y capturar el panel |
| Backlog en Jira | importar `jira/backlog.csv` (Settings → System → External System Import → CSV) y capturar el tablero |

## Capturas (`capturas/`)
Capturas **reales** tomadas con Chromium (Playwright) sobre el sistema en ejecución nativa (datos de prueba del
mock de API Colombia, usuarios `viajero-*` generados). Generadas por `scripts/e2e_ui.py` (13 comprobaciones de
la interfaz: login con correo, llegada calculada, aviso de traslape, botón bloqueado, ciudad incorrecta, vuelo
encadenado válido, sin errores de consola). No incluyen Jira ni SonarCloud (siguen pendientes de captura manual).
