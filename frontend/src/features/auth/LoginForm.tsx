import { useState, type FormEvent } from "react";
import { Icon } from "../../components/ui/Icon";
import { useAuth } from "./AuthContext";
import { LOGIN_INPUT_ID } from "./constants";

/** Panel de acceso. Solo se muestra sin sesión; el contrato con /api/auth/token no cambia. */
export function LoginForm() {
  const { login } = useAuth();
  const [input, setInput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const username = input.trim();
    if (!username) {
      setError("Escribe tu nombre de usuario para continuar.");
      return;
    }
    setError(null);
    setIsSubmitting(true);
    try {
      await login(username);
      setInput("");
    } catch {
      setError("No se pudo iniciar sesión. Intenta de nuevo.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="card login" noValidate aria-labelledby="login-title">
      <span className="login__badge" aria-hidden="true">
        <Icon name="plane" size={22} />
      </span>
      <h2 id="login-title">Inicia sesión</h2>
      <p className="muted">Entra con tu nombre de usuario para ver y crear tus itinerarios sobre el mapa.</p>

      <div className="field">
        <label htmlFor={LOGIN_INPUT_ID}>Nombre de usuario</label>
        <input
          id={LOGIN_INPUT_ID}
          className={`input${error ? " input--error" : ""}`}
          type="text"
          autoComplete="username"
          placeholder="Tu nombre de usuario"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? "login-error" : undefined}
          disabled={isSubmitting}
        />
        {error && (
          <p id="login-error" className="field__error" role="alert">
            <Icon name="alert" size={15} /> {error}
          </p>
        )}
      </div>

      <button type="submit" className="btn btn--primary btn--block" disabled={isSubmitting}>
        {isSubmitting ? (
          <>
            <span className="spinner spinner--sm" aria-hidden="true" /> Entrando…
          </>
        ) : (
          "Entrar"
        )}
      </button>
    </form>
  );
}
