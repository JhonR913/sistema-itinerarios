import { Icon } from "../../components/ui/Icon";
import { useAuth } from "./AuthContext";
import { LOGIN_INPUT_ID } from "./constants";

/** Estado de sesión en la barra superior: usuario real y cierre de sesión, o acceso al login. */
export function SessionMenu() {
  const { username, logout } = useAuth();

  if (!username) {
    return (
      <button
        type="button"
        className="btn btn--on-dark btn--sm"
        onClick={() => document.getElementById(LOGIN_INPUT_ID)?.focus()}
      >
        <Icon name="user" size={16} /> Iniciar sesión
      </button>
    );
  }

  return (
    <div className="session">
      <span className="session__avatar" aria-hidden="true">
        {username.charAt(0).toUpperCase()}
      </span>
      <span className="session__name">
        <span className="visually-hidden">Sesión iniciada como </span>
        {username}
      </span>
      <button type="button" className="btn btn--on-dark btn--sm" onClick={logout}>
        <Icon name="logout" size={16} />
        <span className="session__logout-label">Cerrar sesión</span>
      </button>
    </div>
  );
}
