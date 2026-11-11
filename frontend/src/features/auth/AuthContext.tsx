import { useState, type ReactNode } from "react";
import { authApi } from "../../api/authApi";
import { AuthContext } from "./authContextValue";

/**
 * El token vive SOLO en memoria (estado de React), nunca en localStorage
 * ni sessionStorage (guia de seguridad, falla #10: un XSS se lleva
 * cualquier cosa guardada ahi). El costo es que se pierde al refrescar
 * la pagina; para este alcance (Nivel 1) es una decision aceptada, no un
 * descuido — queda documentada en docs/matriz-estado.md.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);

  const login = async (usernameInput: string, emailInput?: string) => {
    const response = await authApi.issueToken(usernameInput, emailInput);
    setToken(response.access_token);
    setUsername(usernameInput);
    setEmail(emailInput?.trim() ? emailInput.trim() : null);
  };

  const logout = () => {
    setToken(null);
    setUsername(null);
    setEmail(null);
  };

  return (
    <AuthContext.Provider value={{ token, username, email, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
