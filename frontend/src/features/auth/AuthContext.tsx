import { createContext, useContext, useState, type ReactNode } from "react";
import { authApi } from "../../api/authApi";

/**
 * El token vive SOLO en memoria (estado de React), nunca en localStorage
 * ni sessionStorage (guia de seguridad, falla #10: un XSS se lleva
 * cualquier cosa guardada ahi). El costo es que se pierde al refrescar
 * la pagina; para este alcance (Nivel 1) es una decision aceptada, no un
 * descuido — queda documentada en docs/matriz-estado.md.
 */
interface AuthContextValue {
  token: string | null;
  username: string | null;
  login: (username: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);

  const login = async (usernameInput: string) => {
    const response = await authApi.issueToken(usernameInput);
    setToken(response.access_token);
    setUsername(usernameInput);
  };

  const logout = () => {
    setToken(null);
    setUsername(null);
  };

  return (
    <AuthContext.Provider value={{ token, username, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  }
  return ctx;
}
