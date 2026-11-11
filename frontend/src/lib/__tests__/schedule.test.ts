import { describe, it, expect } from "vitest";
import {
  describeConflict,
  estimateDurationMinutes,
  formatTime,
  nextAvailability,
  nowLocalInputValue,
  timeUntil,
  toDepartureIso,
} from "../schedule";
import type { Airport } from "../../types/airport";
import type { Itinerary } from "../../types/itinerary";

const at = (hhmm: string, day = "2026-12-01") => Date.parse(`${day}T${hhmm}:00-05:00`);
const snap = (id: string, city: string) => ({ airport_id: id, iata_code: city.slice(0, 3).toUpperCase(), name: city, city });

/** Bogotá -> Valledupar, 6:00 a 8:00 (el escenario del enunciado). */
const BOG_VUP: Itinerary = {
  id: "f1",
  nombre_usuario: "jhon",
  origin: snap("bog", "Bogota"),
  destination: snap("vup", "Valledupar"),
  travel_date: "2026-12-01",
  departure_at: new Date(at("06:00")).toISOString(),
  arrival_at: new Date(at("08:00")).toISOString(),
  duration_minutes: 120,
};
const cand = (originId: string, destinationId: string, hhmm: string, day?: string, duration = 60) => ({
  originId,
  destinationId,
  departureMs: at(hhmm, day),
  durationMinutes: duration,
});

describe("describeConflict (regla de agenda)", () => {
  it("rejects a flight that overlaps one of yours, even from another city", () => {
    expect(describeConflict(cand("tun", "bog", "07:00"), [BOG_VUP])).toMatch(/Se cruza/);
  });
  it("rejects leaving from a city you are not in after landing", () => {
    expect(describeConflict(cand("tun", "bog", "09:00"), [BOG_VUP])).toMatch(/anterior llega a Valledupar/);
  });
  it("allows leaving from the arrival city exactly when you land", () => {
    expect(describeConflict(cand("vup", "bog", "08:00"), [BOG_VUP])).toBeNull();
  });
  it("allows leaving from the arrival city on a later day", () => {
    expect(describeConflict(cand("vup", "mde", "15:00", "2026-12-04"), [BOG_VUP])).toBeNull();
  });
  it("requires ending where your next flight starts", () => {
    expect(describeConflict(cand("tun", "mde", "02:00"), [BOG_VUP])).toMatch(/siguiente vuelo sale de Bogota/);
    expect(describeConflict(cand("tun", "bog", "02:00"), [BOG_VUP])).toBeNull();
  });
  it("respects a minimum connection margin", () => {
    expect(describeConflict(cand("vup", "bog", "08:00"), [BOG_VUP], 60)).toMatch(/Se cruza/);
    expect(describeConflict(cand("vup", "bog", "09:00"), [BOG_VUP], 60)).toBeNull();
  });
  it("ignores the itinerary being edited", () => {
    expect(describeConflict({ ...cand("bog", "vup", "06:30"), ignoreId: "f1" }, [BOG_VUP])).toBeNull();
  });
  it("is fine with an empty agenda", () => {
    expect(describeConflict(cand("a", "b", "10:00"), [])).toBeNull();
  });
});

describe("nextAvailability", () => {
  it("is null without flights", () => expect(nextAvailability([])).toBeNull());
  it("points to the arrival city of the last-landing flight", () => {
    const later: Itinerary = { ...BOG_VUP, id: "f2", origin: snap("vup", "Valledupar"), destination: snap("mde", "Medellin"),
      departure_at: new Date(at("10:00")).toISOString(), arrival_at: new Date(at("11:00")).toISOString() };
    expect(nextAvailability([later, BOG_VUP])).toMatchObject({ airportId: "mde", city: "Medellin" });
  });
});

describe("helpers", () => {
  it("builds the departure ISO with the Colombia offset", () => {
    expect(toDepartureIso("2026-12-01T06:00")).toBe("2026-12-01T06:00:00-05:00");
  });
  it("shows Bogota local time regardless of the browser zone", () => {
    expect(formatTime("2026-12-01T11:00:00Z")).toBe("06:00");
  });
  it("gives the current Bogota wall clock for the datetime-local min", () => {
    expect(nowLocalInputValue(new Date("2026-12-01T11:30:00Z"))).toBe("2026-12-01T06:30");
  });
  it("estimates a plausible duration (Bogota-Medellin ~ 45-75 min) with a floor", () => {
    const bog = { latitude: 4.7016, longitude: -74.1469 } as Airport;
    const mde = { latitude: 6.1645, longitude: -75.4231 } as Airport;
    const minutes = estimateDurationMinutes(bog, mde);
    expect(minutes).toBeGreaterThanOrEqual(45);
    expect(minutes).toBeLessThanOrEqual(75);
    expect(estimateDurationMinutes(bog, bog)).toBe(30);
  });
  it("describes the remaining time", () => {
    const now = new Date("2026-12-01T00:00:00Z");
    expect(timeUntil("2026-12-01T05:20:00Z", now)).toBe("en 5 h 20 min");
    expect(timeUntil("2026-12-01T00:20:00Z", now)).toBe("en 20 min");
    expect(timeUntil("2026-12-03T01:00:00Z", now)).toBe("en 2 días");
    expect(timeUntil("2026-11-30T00:00:00Z", now)).toBeNull();
  });
});
