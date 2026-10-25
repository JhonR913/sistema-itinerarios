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
  travel_date: string;
  duration_minutes: number;
}

export interface CreateItineraryInput {
  nombre_usuario: string;
  origin_airport_id: string;
  destination_airport_id: string;
  travel_date: string;
  duration_minutes: number;
}
