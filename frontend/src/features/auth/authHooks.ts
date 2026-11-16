import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../lib/httpClient";

/** Mensaje legible para el usuario: el del servidor si lo hay, uno genérico si no. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError && (error.status < 500 || error.status === 503)) return error.message;
  return "No se pudo completar la acción. Intenta de nuevo en un momento.";
}

/** Envío con estado de carga y error (evita repetir el mismo try/catch en cada formulario). */
export function useSubmit() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const run = useCallback(async (action: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }, []);
  return { busy, error, setError, run };
}

/** Cuenta atrás en segundos (para reenviar el código). */
export function useCountdown(initial: number) {
  const [left, setLeft] = useState(initial);
  useEffect(() => {
    if (left <= 0) return;
    const id = setTimeout(() => setLeft((s) => s - 1), 1000);
    return () => clearTimeout(id);
  }, [left]);
  return { left, restart: () => setLeft(initial) };
}
