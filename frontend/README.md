# Frontend — Sistema de Itinerarios Personales

Vite + React + TypeScript. Arquitectura en capas, deliberadamente separada
para que cada pieza se pueda probar y reemplazar de forma aislada:

```
src/
  lib/httpClient.ts       # unico punto que llama fetch(); maneja errores
  api/                    # un modulo por servicio backend (airport, itinerary, auth)
  types/                  # contratos TS que reflejan los DTOs del backend
  features/
    airports/              # hook de datos + componente de mapa (RF-003)
    itineraries/            # hook de datos + formulario + listado (RF-004..RF-009)
    auth/                   # contexto de sesion, token SOLO en memoria
```

## Por qué estas decisiones (no son arbitrarias)

- **`lib/httpClient.ts` centralizado**: ningún componente llama `fetch`
  directamente. Si cambia la forma de autenticar o el manejo de errores,
  se toca un solo archivo.
- **Un hook por feature (`useAirports`, `useItineraries`)**: separa "cómo
  se obtienen los datos" de "cómo se muestran". Los componentes de UI
  (`AirportMap`, `ItineraryList`) son puramente presentacionales y se
  pueden probar sin red.
- **Token solo en memoria (`AuthContext`), nunca en `localStorage`**:
  aplicando la falla #10 de `Plan_de_Blindaje_Seguridad.docx`. Se pierde
  la sesión al refrescar — es una decisión aceptada para este alcance, no
  un olvido.
- **Validación en el formulario (ej. origen ≠ destino) es solo UX**: el
  backend vuelve a validar todo (RN-002, RNF-SEC-005); el frontend nunca
  es la única barrera.

## Variables de entorno

```
VITE_API_BASE_URL=http://localhost   # el Gateway (Traefik), no un servicio directo
```

## Comandos

```bash
npm install
npm run dev      # desarrollo
npm test         # pruebas (vitest + testing-library)
npm run build    # build de produccion (tsc + vite build)
npm run lint     # eslint
```
