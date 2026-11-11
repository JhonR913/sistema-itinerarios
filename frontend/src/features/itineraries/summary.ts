import type { Itinerary } from "../../types/itinerary";

export interface ItinerarySummary {
  total: number;
  /** Próximo vuelo que aún no ha salido (por hora de salida), si existe. */
  next: Itinerary | null;
  /** Aeropuertos distintos que aparecen como origen o destino. */
  distinctAirports: number;
  totalMinutes: number;
}

/**
 * Métricas derivadas únicamente de los itinerarios cargados. No se
 * inventa ningún valor: lo que el backend no entrega (p. ej. estado del
 * vuelo) simplemente no se calcula.
 */
export function summarizeItineraries(itineraries: Itinerary[], now: Date = new Date()): ItinerarySummary {
  const airportIds = new Set<string>();
  let totalMinutes = 0;
  let next: Itinerary | null = null;

  for (const it of itineraries) {
    airportIds.add(it.origin.airport_id);
    airportIds.add(it.destination.airport_id);
    totalMinutes += it.duration_minutes;
    const departure = Date.parse(it.departure_at);
    if (departure >= now.getTime() && (next === null || departure < Date.parse(next.departure_at))) {
      next = it;
    }
  }

  return { total: itineraries.length, next, distinctAirports: airportIds.size, totalMinutes };
}
