# Sistema de Itinerarios Personales

Repositorio oficial de implementación (fase de código). La especificación
completa (requisitos, arquitectura, diagramas, plan de pruebas, ciclo
DevOps y plan de blindaje de seguridad) vive en los documentos de la fase
documental — este código debe ser consistente con esos documentos, no
redefinirlos sobre la marcha.

## Estado — Sprint 1 (Airport Service)

- [x] US-001 Listar aeropuertos disponibles
- [x] US-003 Consultar detalle de un aeropuerto
- [x] US-011 Resiliencia ante caída de API externa (Circuit Breaker + Retry + caché)
- [x] DEVOPS-003 Pruebas de carga (Locust)
- [x] DEVOPS-004 Swagger (automático vía FastAPI)
- [x] DEVOPS-006 Hardening de seguridad (CLAUDE.md + hook, antes del primer commit de negocio)
- [ ] US-002 Mapa Plotly (pendiente — requiere frontend, fuera de este sprint)
- [ ] Resto de épicas: ver jira/backlog.csv

## Arrancar Airport Service

```bash
cd services/airport-service
docker network create itinerarios-net 2>/dev/null || true
docker compose up -d --build
```

- Swagger: http://localhost:8001/docs
- Salud: http://localhost:8001/health

## Correr pruebas

```bash
cd services/airport-service
pip install -r requirements.txt
pytest tests/unit -v --cov=app --cov-report=term-missing
```

Resultado real de la última ejecución (ver commit de este sprint):
**4/4 pruebas unitarias en verde** (UT-001, UT-002, UT-003 + 1 prueba
complementaria). Detalle y trazabilidad en `docs/matriz-estado.md`.

## Estrategia de ramas

`main` ← `develop` ← `feature/<historia>`, con Pull Request obligatorio.
Ver Documento_Ciclo_DevOps.docx (fase documental) para el detalle completo.
