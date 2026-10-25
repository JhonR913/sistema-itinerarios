import { apiRequest } from "../lib/httpClient";
import type { CreateItineraryInput, Itinerary } from "../types/itinerary";

export const itineraryApi = {
  listMine: (token: string) => apiRequest<Itinerary[]>("/api/itineraries", { token }),

  create: (input: CreateItineraryInput, token: string) =>
    apiRequest<{ id: string }>("/api/itineraries", { method: "POST", body: input, token }),

  remove: (id: string, token: string) =>
    apiRequest<void>(`/api/itineraries/${id}`, { method: "DELETE", token }),
};
