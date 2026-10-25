import { useCallback, useEffect, useState } from "react";
import { itineraryApi } from "../../api/itineraryApi";
import { ApiError } from "../../lib/httpClient";
import type { CreateItineraryInput, Itinerary } from "../../types/itinerary";

interface UseItinerariesResult {
  itineraries: Itinerary[];
  isLoading: boolean;
  error: string | null;
  create: (input: CreateItineraryInput) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export function useItineraries(token: string | null): UseItinerariesResult {
  const [itineraries, setItineraries] = useState<Itinerary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      setItineraries(await itineraryApi.listMine(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar tus itinerarios");
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const create = async (input: CreateItineraryInput) => {
    if (!token) throw new Error("Debes iniciar sesión primero");
    await itineraryApi.create(input, token);
    await load();
  };

  const remove = async (id: string) => {
    if (!token) throw new Error("Debes iniciar sesión primero");
    await itineraryApi.remove(id, token);
    await load();
  };

  return { itineraries, isLoading, error, create, remove };
}
