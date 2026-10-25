import { describe, it, expect } from "vitest";
import { summarizeItineraries } from "../summary";
import type { Itinerary } from "../../../types/itinerary";

function make(id: string, from: string, to: string, date: string, minutes: number): Itinerary {
  return {
    id,
    nombre_usuario: "jhon",
    origin: { airport_id: from, iata_code: from.toUpperCase(), name: from, city: from },
    destination: { airport_id: to, iata_code: to.toUpperCase(), name: to, city: to },
    travel_date: date,
    duration_minutes: minutes,
  };
}

describe("summarizeItineraries", () => {
  it("returns zeros and no next trip for an empty list", () => {
    expect(summarizeItineraries([], "2026-10-25")).toEqual({
      total: 0,
      next: null,
      distinctAirports: 0,
      totalMinutes: 0,
    });
  });

  it("counts distinct airports and sums durations", () => {
    const list = [make("1", "a", "b", "2026-11-01", 60), make("2", "b", "c", "2026-12-01", 90)];
    const summary = summarizeItineraries(list, "2026-10-25");
    expect(summary.total).toBe(2);
    expect(summary.distinctAirports).toBe(3);
    expect(summary.totalMinutes).toBe(150);
  });

  it("picks the closest upcoming trip, ignoring past ones and including today", () => {
    const list = [
      make("past", "a", "b", "2026-01-01", 60),
      make("later", "a", "b", "2026-12-01", 60),
      make("today", "a", "b", "2026-10-25", 60),
    ];
    expect(summarizeItineraries(list, "2026-10-25").next?.id).toBe("today");
  });

  it("has no next trip when every itinerary is in the past", () => {
    const list = [make("past", "a", "b", "2026-01-01", 60)];
    expect(summarizeItineraries(list, "2026-10-25").next).toBeNull();
  });
});
