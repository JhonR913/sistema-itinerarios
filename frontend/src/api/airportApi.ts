import { apiRequest } from "../lib/httpClient";
import type { Airport } from "../types/airport";

export const airportApi = {
  listAll: () => apiRequest<Airport[]>("/api/airports"),
  getById: (id: string) => apiRequest<Airport>(`/api/airports/${id}`),
};
