import { useState } from "react";
import { useAuth } from "./authContextValue";
import { ForgotForm, LoginForm, RegisterForm, ResetForm, VerifyForm, type Screen } from "./AuthForms";

interface State {
  screen: Screen;
  email: string;
  notice: string | null;
}

/** Panel de acceso: login, registro con código por correo y recuperación de contraseña. */
export function AuthPanel() {
  const { startSession } = useAuth();
  const [state, setState] = useState<State>({ screen: "login", email: "", notice: null });

  const go = (screen: Screen, email = state.email, notice?: string) => setState({ screen, email, notice: notice ?? null });
  const common = { email: state.email, notice: state.notice, go };

  switch (state.screen) {
    case "register":
      return <RegisterForm {...common} />;
    case "verify":
      return <VerifyForm {...common} onSession={startSession} />;
    case "forgot":
      return <ForgotForm {...common} />;
    case "reset":
      return <ResetForm {...common} />;
    default:
      return <LoginForm {...common} onSession={startSession} />;
  }
}
