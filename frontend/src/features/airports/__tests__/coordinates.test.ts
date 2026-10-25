import { describe, it, expect } from "vitest";
import { isValidLatLon, sanitizeAirports, toCoordinate } from "../coordinates";
import type { Airport } from "../../../types/airport";

const airport = (iata: string, lat: unknown, lon: unknown): Airport => ({
  id: iata,
  iata_code: iata,
  name: iata,
  city: iata,
  latitude: lat as number,
  longitude: lon as number,
});

// Referencias aproximadas solo para pruebas (no son datos de producción).
const BOG = [4.7, -74.15] as const;
const MDE = [6.16, -75.42] as const;
const CLO = [3.54, -76.38] as const;
const CTG = [10.44, -75.51] as const;

describe("toCoordinate", () => {
  it("accepts numbers and numeric text, including decimal comma", () => {
    expect(toCoordinate(4.7)).toBe(4.7);
    expect(toCoordinate("-74.15")).toBe(-74.15);
    expect(toCoordinate("4,70")).toBe(4.7);
  });

  it("rejects null, empty, text and non-finite values", () => {
    for (const bad of [null, undefined, "", "  ", "abc", Number.NaN, Infinity, {}]) {
      expect(toCoordinate(bad)).toBeNull();
    }
  });
});

describe("isValidLatLon", () => {
  it("checks the geographic ranges", () => {
    expect(isValidLatLon(4.7, -74.15)).toBe(true);
    expect(isValidLatLon(91, 0)).toBe(false);
    expect(isValidLatLon(0, 181)).toBe(false);
  });
});

describe("sanitizeAirports", () => {
  it("keeps correct Colombian airports untouched", () => {
    const input = [airport("BOG", ...BOG), airport("MDE", ...MDE), airport("CLO", ...CLO), airport("CTG", ...CTG)];
    const result = sanitizeAirports(input);
    expect(result.invalidCount).toBe(0);
    expect(result.correctedCount).toBe(0);
    expect(result.airports.map((a) => [a.latitude, a.longitude])).toEqual([BOG, MDE, CLO, CTG].map((c) => [...c]));
  });

  it("converts text coordinates to numbers", () => {
    const [a] = sanitizeAirports([airport("BOG", "4.70", "-74.15")]).airports;
    expect(a.latitude).toBe(4.7);
    expect(a.longitude).toBe(-74.15);
  });

  it("drops missing, invalid and (0, 0) coordinates without inventing positions", () => {
    const result = sanitizeAirports([
      airport("AAA", null, null),
      airport("BBB", "x", "y"),
      airport("CCC", 0, 0),
      airport("DDD", 95, -74),
      airport("BOG", ...BOG),
    ]);
    expect(result.airports.map((a) => a.iata_code)).toEqual(["BOG"]);
    expect(result.invalidCount).toBe(4);
  });

  it("fixes swapped latitude and longitude when that lands in Colombia", () => {
    const result = sanitizeAirports([airport("BOG", BOG[1], BOG[0])]);
    expect(result.airports[0].latitude).toBe(4.7);
    expect(result.airports[0].longitude).toBe(-74.15);
    expect(result.correctedCount).toBe(1);
  });

  it("fixes a longitude that lost its minus sign", () => {
    const result = sanitizeAirports([airport("BOG", 4.7, 74.15)]);
    expect(result.airports[0].longitude).toBe(-74.15);
    expect(result.correctedCount).toBe(1);
  });

  it("keeps a valid airport from another hemisphere as is", () => {
    const result = sanitizeAirports([airport("SYD", -33.94, 151.18)]);
    expect(result.airports).toHaveLength(1);
    expect(result.airports[0].latitude).toBe(-33.94);
    expect(result.correctedCount).toBe(0);
  });

  it("does not mutate the input", () => {
    const input = [airport("BOG", "4.70", "-74.15")];
    sanitizeAirports(input);
    expect(input[0].latitude).toBe("4.70");
  });
});
