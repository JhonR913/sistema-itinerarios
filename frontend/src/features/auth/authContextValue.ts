import { createContext, useContext } from "react";

export interface AuthContextValue {
  token: string | null;
  username: string | null;
  /** Correo con el que se inició sesión (solo en memoria); habilita los recordatorios. */
  email: string | null;
  login: (username: string, email?: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return ctx;
}
