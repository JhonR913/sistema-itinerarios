import { describe, it, expect } from "vitest";
import { summarizeItineraries } from "../summary";
import type { Itinerary } from "../../../types/itinerary";

function make(id: string, from: string, to: string, departure: string, minutes: number): Itinerary {
  return {
    id,
    nombre_usuario: "jhon",
    origin: { airport_id: from, iata_code: from.toUpperCase(), name: from, city: from },
    destination: { airport_id: to, iata_code: to.toUpperCase(), name: to, city: to },
    travel_date: departure.slice(0, 10),
    departure_at: departure,
    arrival_at: new Date(Date.parse(departure) + minutes * 60_000).toISOString(),
    duration_minutes: minutes,
  };
}

const NOW = new Date("2026-10-25T12:00:00Z");

describe("summarizeItineraries", () => {
  it("returns zeros and no next trip for an empty list", () => {
    expect(summarizeItineraries([], NOW)).toEqual({ total: 0, next: null, distinctAirports: 0, totalMinutes: 0 });
  });

  it("counts distinct airports and sums durations", () => {
    const list = [make("1", "a", "b", "2026-11-01T10:00:00Z", 60), make("2", "b", "c", "2026-12-01T10:00:00Z", 90)];
    const summary = summarizeItineraries(list, NOW);
    expect(summary.total).toBe(2);
    expect(summary.distinctAirports).toBe(3);
    expect(summary.totalMinutes).toBe(150);
  });

  it("picks the closest flight that has not departed yet, by time of day", () => {
    const list = [
      make("past", "a", "b", "2026-10-25T08:00:00Z", 60), // hoy, pero ya salió
      make("later", "a", "b", "2026-12-01T10:00:00Z", 60),
      make("today-evening", "a", "b", "2026-10-25T20:00:00Z", 60),
    ];
    expect(summarizeItineraries(list, NOW).next?.id).toBe("today-evening");
  });

  it("has no next trip when every itinerary already departed", () => {
    expect(summarizeItineraries([make("past", "a", "b", "2026-01-01T10:00:00Z", 60)], NOW).next).toBeNull();
  });
});
