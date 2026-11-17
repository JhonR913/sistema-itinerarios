# Matriz de la suite de pruebas

La matriz distingue las pruebas que ya están en el repositorio de las nuevas pruebas de interfaz incluidas aquí.

| Capa | Servicio / componente | Tipo | Ubicación que ejecuta la suite | Fuente |
|---|---|---|---|---|
| Backend | airport-service | Unitarias + integración | `services/airport-service/tests` | Existente |
| Backend | itinerary-service | Unitarias + integración | `services/itinerary-service/tests` | Existente |
| Backend | auth-stub | Unitarias + integración | `services/auth-stub/tests` | Existente |
| Backend | notification-function | Unitarias + integración | `services/notification-function/tests` | Existente |
| Frontend | Pruebas funcionales ya creadas | Vitest | `frontend/src/**/*.test.ts(x)` | Existente |
| Frontend UI | StateMessage | Renderizado, carga, error, vacío y accesibilidad | `frontend/src/components/ui/StateMessage.component.test.tsx` | Complementaria nueva |
| Frontend UI | TopBar | Marca, navegación y espacio de sesión | `frontend/src/features/app-shell/TopBar.component.test.tsx` | Complementaria nueva |
| Frontend UI | SessionMenu | Sesión sin usuario, foco al login, usuario y logout | `frontend/src/features/auth/SessionMenu.component.test.tsx` | Complementaria nueva |
| Calidad | Frontend | ESLint, TypeScript, build y auditoría prod | `frontend/package.json` | Comandos ya definidos |
| E2E | Flujo principal | Login, itinerario, outbox, RabbitMQ, notificación y DLQ | `scripts/e2e_smoke.py` | Existente; requiere Compose |
| E2E | Resiliencia RabbitMQ | Reintentos / recuperación | `scripts/e2e_resilience.py` | Existente; requiere Compose |
| E2E | Fallos de dependencias | Airport, BD, Redis y proveedor | `scripts/e2e_faults.py` | Existente; requiere servicios auxiliares |
| Carga | Itinerary Service | Usuarios virtuales / agenda | `services/itinerary-service/tests/load/locustfile.py` | Existente; ejecución manual controlada |

## Cantidades documentadas antes de esta suite

`docs/evidencias/pruebas.txt` registra 20 + 60 + 85 + 74 = 239 pruebas backend y 101 pruebas frontend en 12 archivos (ejecución documentada el 15/11/2026). La suite nueva agrega 3 archivos de pruebas UI; las cantidades finales se deben confirmar ejecutándolas en la copia local del proyecto.

## Cobertura y alcance

Estos 3 archivos nuevos (9 casos) cubren tres componentes visuales concretos que la matriz de estado del repositorio identificaba como sin pruebas de componentes. No equivalen a cobertura visual de todos los componentes: el resto del frontend ya tiene pruebas funcionales existentes, pero no se debe interpretar este paquete como una certificación exhaustiva de cada pantalla o flujo.
