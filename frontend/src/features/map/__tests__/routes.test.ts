import { describe, it, expect } from "vitest";
import { buildRoutes } from "../routes";
import type { Airport } from "../../../types/airport";
import type { Itinerary } from "../../../types/itinerary";

const AIRPORTS: Airport[] = [
  { id: "1", iata_code: "BOG", name: "El Dorado", city: "Bogotá", latitude: 4.7, longitude: -74.1 },
  { id: "2", iata_code: "MDE", name: "José María Córdova", city: "Rionegro", latitude: 6.16, longitude: -75.42 },
];

const snapshot = (id: string, iata: string) => ({ airport_id: id, iata_code: iata, name: iata, city: iata });

const ITINERARY = (id: string, from: string, to: string): Itinerary => ({
  id,
  nombre_usuario: "jhon",
  origin: snapshot(from, "X"),
  destination: snapshot(to, "Y"),
  travel_date: "2026-11-01",
  duration_minutes: 60,
});

describe("buildRoutes", () => {
  it("resolves coordinates from the real airport list and builds an arc", () => {
    const { routes, unresolved } = buildRoutes([ITINERARY("a", "1", "2")], AIRPORTS);
    expect(unresolved).toHaveLength(0);
    expect(routes).toHaveLength(1);
    expect(routes[0].arc.lat[0]).toBe(4.7);
    expect(routes[0].destination.iata_code).toBe("MDE");
  });

  it("reports itineraries with unknown airports instead of inventing coordinates", () => {
    const { routes, unresolved } = buildRoutes([ITINERARY("a", "1", "999")], AIRPORTS);
    expect(routes).toHaveLength(0);
    expect(unresolved.map((i) => i.id)).toEqual(["a"]);
  });
});
