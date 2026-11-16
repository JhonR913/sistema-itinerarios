import { createContext, useContext } from "react";
import type { SessionResponse } from "../../api/authApi";

export interface AuthContextValue {
  token: string | null;
  /** Nombre que eligió al registrarse. */
  username: string | null;
  /** Correo VERIFICADO de la cuenta: a él llegan los recordatorios. */
  email: string | null;
  /** true mientras se intenta recuperar la sesión de la cookie al abrir la página. */
  restoring: boolean;
  /** Guarda en memoria la sesión que devolvió el servidor (login o verificación). */
  startSession: (session: SessionResponse) => void;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return ctx;
}
