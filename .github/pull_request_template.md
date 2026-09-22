## Descripción

## Checklist de seguridad (Plan_de_Blindaje_Seguridad.docx)
- [ ] No se agregaron secretos/API keys al código ni a `.env` versionado.
- [ ] Toda query nueva usa parámetros/ORM (sin concatenación de SQL).
- [ ] Toda entrada nueva se valida en el servidor.
- [ ] Toda acción sensible valida autorización en backend.
- [ ] Endpoints con ID verifican pertenencia al usuario (anti-IDOR).
- [ ] Updates usan lista blanca de campos (anti mass-assignment).
- [ ] No se expone stack trace en errores de producción.

## Cómo se probó
- [ ] Pruebas unitarias en verde.
