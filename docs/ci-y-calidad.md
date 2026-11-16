# CI y calidad

Workflow: `.github/workflows/ci.yml`. **Estado: escrito pero NO ejecutado** (el entorno de
desarrollo no tiene acceso a GitHub Actions); los comandos de cada paso sí se ejecutaron
localmente (ver matriz de estado). Las etiquetas de versión de las acciones (`@v4`, `@v5`,
`trivy-action@0.28.0`…) no se pudieron verificar en línea; Dependabot las mantiene.

| Job | Qué hace | Bloquea |
|---|---|---|
| `backend` (×4) | pytest unitarias + integración con Postgres real, cobertura XML, lock con `--require-hashes` | Sí |
| `frontend` | lint, `tsc`, vitest con cobertura, build, `npm audit --omit=dev --audit-level=high` | Sí |
| `compose` | `bootstrap-env.sh`, `docker compose config`, `docker compose build` | Sí |
| `e2e` | levanta Compose con el mock de aeropuertos y corre `e2e_smoke.py` + `e2e_resilience.py` | **No** (`continue-on-error` hasta su 1.ª ejecución verde) |
| `security` | gitleaks (historial) + trivy fs (informativo) | gitleaks sí |
| `sonarcloud` | análisis + cobertura | Se **omite** sin configuración |

## Secretos / variables necesarios (ninguno es obligatorio para el resto del pipeline)
| Nombre | Tipo | Para qué |
|---|---|---|
| `SONAR_TOKEN` | secret | token de SonarCloud |
| `SONAR_ORGANIZATION` | variable | organización en sonarcloud.io |
| `SONAR_PROJECT_KEY` | variable | clave del proyecto en SonarCloud |

`GITHUB_TOKEN` lo provee GitHub. Sin los tres de Sonar el job termina con un aviso, no con error.
El Quality Gate real debe consultarse en SonarCloud: no se ha ejecutado ningún análisis desde esta entrega.

## Ramas
`main` ← `develop` ← `feature/*`, con Pull Request. Rama de trabajo de esta entrega: `feature/entrega-validacion`.


## SonarCloud: análisis desde CI (obligatorio para que se respete la configuración)
El *Automatic Analysis* de SonarCloud **ignora** `sonar-project.properties` (no mide cobertura ni aplica
exclusiones). Para que el Quality Gate refleje el proyecto real:
1. SonarCloud → proyecto → *Administration → Analysis Method* → **desactivar Automatic Analysis**.
2. Crear un token (*My Account → Security*) y guardarlo en GitHub como secreto `SONAR_TOKEN`; definir las
   variables del repositorio `SONAR_ORGANIZATION` y `SONAR_PROJECT_KEY`.
3. El job `sonarcloud` del CI analiza con `-Dsonar.qualitygate.wait=true`: si el Quality Gate falla, el CI
   queda en rojo y **no se despliega** (`deploy.yml` solo corre con CI verde).

Si prefieres seguir con Automatic Analysis, replica en la interfaz (*Administration → General Settings →
Analysis Scope*): exclusiones `tools/**,scripts/**,**/alembic/**,**/tests/**` y exclusiones de duplicación
`**/alembic/env.py,**/app/main.py,**/settings.py`. Las 3 alertas «Using HTTP protocol is insecure» de
`tools/*.py` ya llevan `# NOSONAR` con la razón (servidores de prueba locales que no se despliegan).
