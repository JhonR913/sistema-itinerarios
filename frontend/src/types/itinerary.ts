export interface AirportSnapshot {
  airport_id: string;
  iata_code: string;
  name: string;
  city: string;
}

export interface Itinerary {
  id: string;
  nombre_usuario: string;
  origin: AirportSnapshot;
  destination: AirportSnapshot;
  /** Fecha local (Bogotá) de la salida, "YYYY-MM-DD". */
  travel_date: string;
  /** Instante de salida, ISO 8601 en UTC. */
  departure_at: string;
  /** Instante de llegada (salida + duración), ISO 8601 en UTC. */
  arrival_at: string;
  duration_minutes: number;
}

export interface CreateItineraryInput {
  nombre_usuario: string;
  origin_airport_id: string;
  destination_airport_id: string;
  /** ISO 8601 con zona, p. ej. "2026-12-01T06:00:00-05:00". */
  departure_at: string;
  duration_minutes: number;
}
