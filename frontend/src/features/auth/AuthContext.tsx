import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { authApi, type SessionResponse } from "../../api/authApi";
import { AuthContext } from "./authContextValue";

/** Se renueva el token de acceso un minuto antes de que venza. */
const RENEW_MARGIN_MS = 60_000;

/**
 * El token de acceso (JWT) vive SOLO en memoria. La sesión sobrevive al refrescar la
 * página gracias a una cookie httpOnly que el JavaScript no puede leer: un XSS no
 * se lleva ni el token ni la sesión (nada de localStorage). Al abrir la página se
 * pide un token nuevo con esa cookie; si no hay sesión, se muestra el acceso.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [restoring, setRestoring] = useState(true);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  const startSession = useCallback((next: SessionResponse) => setSession(next), []);

  useEffect(() => {
    let cancelled = false;
    authApi
      .refresh()
      .then((s) => !cancelled && setSession(s))
      .catch(() => undefined) // sin cookie o vencida: simplemente no hay sesión
      .finally(() => !cancelled && setRestoring(false));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    clearTimeout(timer.current);
    if (!session) return;
    const wait = Math.max(session.expires_in_minutes * 60_000 - RENEW_MARGIN_MS, 5_000);
    timer.current = setTimeout(() => {
      authApi
        .refresh()
        .then(setSession)
        .catch(() => setSession(null)); // sesión revocada o vencida: vuelve al acceso
    }, wait);
    return () => clearTimeout(timer.current);
  }, [session]);

  const logout = useCallback(async () => {
    setSession(null);
    await authApi.logout().catch(() => undefined);
  }, []);

  const value = useMemo(
    () => ({
      token: session?.access_token ?? null,
      username: session?.name ?? null,
      email: session?.email ?? null,
      restoring,
      startSession,
      logout,
    }),
    [session, restoring, startSession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
