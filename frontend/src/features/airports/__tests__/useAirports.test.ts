import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useAirports } from "../useAirports";

const SAMPLE_AIRPORTS = [
  { id: "1", iata_code: "BOG", name: "El Dorado", city: "Bogotá", latitude: 4.7, longitude: -74.1 },
];

describe("useAirports", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: async () => SAMPLE_AIRPORTS,
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads airports and exposes them once the fetch resolves", async () => {
    const { result } = renderHook(() => useAirports());

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.airports).toEqual(SAMPLE_AIRPORTS);
    expect(result.current.error).toBeNull();
  });

  it("exposes an error message when the request fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        json: async () => ({ detail: "Airport Service no disponible" }),
      }),
    );

    const { result } = renderHook(() => useAirports());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("Airport Service no disponible");
    expect(result.current.airports).toEqual([]);
  });
});
