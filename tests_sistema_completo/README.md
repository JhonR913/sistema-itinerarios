# Suite de pruebas completa — Sistema de Itinerarios

Esta carpeta se copia en la **raíz** del repositorio, al mismo nivel que `frontend`, `services`, `scripts` y `docker-compose.yml`.

Su nombre `tests_sistema_completo` evita confundir esta suite con el directorio de código `frontend/`.

## Qué incluye

1. **Backend:** ejecuta las suites existentes de los cuatro servicios (`airport-service`, `itinerary-service`, `auth-stub` y `notification-function`) con pytest y PostgreSQL 16 temporal. El entorno de prueba usa Python 3.11 dentro de Docker, igual que el workflow de CI del repositorio; no depende del Python 3.15 instalado en Windows.
2. **Frontend:** ejecuta lint, comprobación TypeScript, Vitest con cobertura, build y auditoría de dependencias de producción.
3. **Pruebas UI complementarias:** incluye tres archivos complementarios con nueve casos de prueba basados en los componentes actuales `StateMessage`, `TopBar` y `SessionMenu`. Un instalador los copia a sus ubicaciones correctas dentro de `frontend/src` sin sobrescribir archivos existentes.

La suite **no reemplaza** las pruebas que ya existen. Las pruebas backend y las 12 suites Vitest actuales permanecen en sus carpetas originales.

## Antes de ejecutarla

- Docker Desktop debe estar abierto y mostrar que el motor está en ejecución.
- Node.js y npm deben estar instalados.
- Abre PowerShell en la carpeta raíz del repositorio.
- No ejecutes esta suite desde `System32`.

## Instalación de las tres pruebas UI complementarias

Desde PowerShell, en la raíz del repositorio:

```powershell
.\tests_sistema_completo\frontend\instalar_pruebas_ui.ps1
```

El script crea las carpetas destino que hagan falta y copia solo los archivos `.test.tsx`. Si alguno ya existe, lo conserva y muestra una advertencia. No modifica componentes ni lógica de la aplicación.

Si necesitas reemplazar conscientemente alguno de esos tres archivos de prueba, primero haz una copia de seguridad y luego ejecuta:

```powershell
.\tests_sistema_completo\frontend\instalar_pruebas_ui.ps1 -Reemplazar
```

## Ejecutar solo backend

```powershell
.\tests_sistema_completo\backend\ejecutar_backend.ps1
```

El script crea una red Docker y un PostgreSQL 16 temporal con cuatro bases separadas. Ejecuta pytest dentro de contenedores Python 3.11 para respetar la versión usada por CI. Al finalizar elimina únicamente los contenedores y la red temporales que él mismo creó. No borra volúmenes ni bases de datos de la aplicación.

## Ejecutar solo frontend

```powershell
.\tests_sistema_completo\frontend\ejecutar_frontend.ps1
```

El script instala las dependencias con `npm ci` y ejecuta lint, TypeScript, Vitest con cobertura, build y `npm audit` para dependencias de producción.

## Ejecutar backend y frontend

```powershell
.\tests_sistema_completo\ejecutar_todo.ps1
```

Este comando instala las tres pruebas UI complementarias si aún no existen y después ejecuta las suites backend y frontend.

## Qué pruebas ya existen en el repositorio

La evidencia versionada del proyecto registra, en una ejecución del 15 de noviembre de 2026:

- `airport-service`: 20 pruebas.
- `itinerary-service`: 60 pruebas.
- `auth-stub`: 85 pruebas.
- `notification-function`: 74 pruebas.
- Frontend: 101 pruebas en 12 archivos, además de TypeScript y ESLint aprobados.

Son resultados documentados en el repositorio, **no resultados de una ejecución en este computador**. Al ejecutar esta suite se obtendrá el resultado real de la versión local.

## Pruebas E2E y de carga

El repositorio también contiene pruebas de extremo a extremo y de carga, pero no se lanzan automáticamente con `ejecutar_todo.ps1`:

- E2E: `scripts/e2e_smoke.py`, `scripts/e2e_resilience.py` y `scripts/e2e_faults.py`. Requieren levantar los servicios del proyecto mediante Docker Compose y configurar las variables indicadas en el README principal.
- Carga: `services/itinerary-service/tests/load/locustfile.py`. Requiere Locust y un sistema levantado. No se lanza automáticamente porque genera tráfico de carga.

En Windows, ejecuta `scripts/bootstrap-env.sh` desde Git Bash y sigue la sección **Pruebas** del README principal antes de correr esas pruebas. No uses `docker compose down -v` para detener el sistema, porque elimina volúmenes de datos.

## Resultados

Los resultados de cada comando aparecen en la terminal. Se guardan registros de ejecución en `resultado_ejecucion/` cuando el script consigue iniciarlos. Conserva las salidas completas para documentar pruebas aprobadas y fallidas.

## Límites

- No se afirma que la aplicación esté libre de defectos por el hecho de que pasen los tests.
- Las pruebas E2E dependen de Docker Compose y de los servicios auxiliares.
- La prueba de carga debe ejecutarse en un entorno controlado; no apuntarla a producción.
- Esta carpeta no cambia endpoints, modelos, lógica, bases de datos ni configuración de despliegue de la aplicación.
