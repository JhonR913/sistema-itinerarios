import { useState, type FormEvent } from "react";
import { useAuth } from "./AuthContext";

export function LoginForm() {
  const { username, login, logout } = useAuth();
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await login(input);
      setInput("");
    } catch {
      setError("No se pudo iniciar sesión. Intenta de nuevo.");
    }
  }

  if (username) {
    return (
      <div className="session-bar">
        <span>Sesión: {username}</span>
        <button onClick={logout}>Cerrar sesión</button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <input
        type="text"
        placeholder="Tu nombre de usuario"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        required
      />
      <button type="submit">Entrar</button>
      {error && <p className="field-error">{error}</p>}
    </form>
  );
}
