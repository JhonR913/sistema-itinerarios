import { apiRequest } from "../lib/httpClient";

export interface SessionResponse {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  name: string;
  email: string;
}

const post = <T>(path: string, body?: unknown) => apiRequest<T>(`/api/auth/${path}`, { method: "POST", body });

export const authApi = {
  register: (email: string, name: string, password: string) => post<void>("register", { email, name, password }),
  verify: (email: string, code: string) => post<SessionResponse>("verify", { email, code }),
  resend: (email: string) => post<void>("resend", { email }),
  login: (email: string, password: string) => post<SessionResponse>("login", { email, password }),
  /** Intercambia la cookie de sesión (httpOnly) por un nuevo token de acceso. */
  refresh: () => post<SessionResponse>("refresh"),
  logout: () => post<void>("logout"),
  forgot: (email: string) => post<void>("forgot", { email }),
  reset: (email: string, code: string, password: string) => post<void>("reset", { email, code, password }),
};
