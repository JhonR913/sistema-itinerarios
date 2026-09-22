# CLAUDE.md — Reglas de seguridad y estilo para este repositorio

Este archivo es contexto para el asistente de código. Es una guía de
comportamiento, NO un mecanismo de bloqueo: para lo que no puede fallar
bajo ninguna circunstancia, este repo también usa un hook `PreToolUse`
(ver `.claude/hooks/`) y una revisión de seguridad en cada Pull Request.
Basado en Plan_de_Blindaje_Seguridad.docx (fase documental del proyecto).

## Reglas de seguridad obligatorias

1. Nunca escribir secretos, API keys o contraseñas directamente en código
   o en archivos versionados. Usar variables de entorno y `.env.example`
   con placeholders.
2. Nunca construir SQL concatenando strings; usar siempre el ORM o
   parámetros preparados.
3. Validar en el servidor todo dato de entrada, incluso si el frontend ya
   valida (Pydantic para los DTOs).
4. Nunca confiar en autorización validada solo en frontend; toda acción
   sensible se valida en el backend.
5. En endpoints que reciben un ID de recurso, verificar siempre que
   pertenezca al usuario solicitante (anti-IDOR).
6. En actualizaciones, aceptar solo una lista blanca explícita de campos
   (anti mass-assignment).
7. No exponer detalle de errores/stack trace al cliente en producción;
   el detalle solo va a logs internos.
8. Verificar firma en cualquier webhook que se agregue a futuro.

## Arquitectura del proyecto

- Cada servicio sigue Arquitectura Hexagonal: `domain/` no importa nada de
  `infrastructure/` ni de librerías externas. `application/` orquesta el
  dominio a través de puertos definidos en `domain/ports.py`.
  `infrastructure/adapters/` implementa esos puertos.
- El patrón Adapter es obligatorio en `airport-service` para aislar el
  formato de API Colombia del modelo de dominio interno `Airport`.
- No dupliques lógica de negocio en `infrastructure/api/` (routers): esa
  capa solo traduce HTTP ↔ casos de uso.
- Todo cambio de contrato, modelo de datos o decisión arquitectónica debe
  ser consistente con lo ya cerrado en la fase documental (ver /docs).

## Estilo

- Python: type hints obligatorios en funciones públicas.
- Commits en español, Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`).
- Nunca modificar `main` ni `develop` directamente: todo cambio va por
  rama `feature/<historia>` + Pull Request.
