import { greatCircleArc, type Arc, type GeoPoint } from "../../lib/geo";
import type { Airport } from "../../types/airport";
import type { Itinerary } from "../../types/itinerary";

export interface MapRoute {
  itinerary: Itinerary;
  origin: Airport;
  destination: Airport;
  arc: Arc;
}

export interface RoutesResult {
  routes: MapRoute[];
  /** Itinerarios cuyo origen o destino no está en la lista de aeropuertos cargada. */
  unresolved: Itinerary[];
}

export const toPoint = (airport: Airport): GeoPoint => ({ lat: airport.latitude, lon: airport.longitude });

/**
 * Une cada itinerario con las coordenadas REALES del aeropuerto (por id).
 * Si un aeropuerto no se encuentra no se dibuja la ruta ni se inventa una
 * coordenada: se informa en `unresolved` para que la interfaz lo declare.
 */
export function buildRoutes(itineraries: Itinerary[], airports: Airport[]): RoutesResult {
  const byId = new Map(airports.map((a) => [a.id, a]));
  const routes: MapRoute[] = [];
  const unresolved: Itinerary[] = [];

  for (const itinerary of itineraries) {
    const origin = byId.get(itinerary.origin.airport_id);
    const destination = byId.get(itinerary.destination.airport_id);
    if (!origin || !destination) {
      unresolved.push(itinerary);
      continue;
    }
    routes.push({
      itinerary,
      origin,
      destination,
      arc: greatCircleArc(toPoint(origin), toPoint(destination)),
    });
  }

  return { routes, unresolved };
}
