import { useEffect, useState } from "react";
import { airportApi } from "../../api/airportApi";
import { ApiError } from "../../lib/httpClient";
import type { Airport } from "../../types/airport";

interface UseAirportsResult {
  airports: Airport[];
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

export function useAirports(): UseAirportsResult {
  const [airports, setAirports] = useState<Airport[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await airportApi.listAll();
        if (!cancelled) {
          setAirports(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "No se pudo cargar la lista de aeropuertos");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  return { airports, isLoading, error, reload: () => setReloadToken((n) => n + 1) };
}
