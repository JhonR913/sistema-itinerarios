import { AuthProvider } from "./features/auth/AuthContext";
import { TopBar } from "./features/app-shell/TopBar";
import { Dashboard } from "./features/dashboard/Dashboard";
import "./styles.css";

export function App() {
  return (
    <AuthProvider>
      <a className="skip-link" href="#mapa">
        Saltar al mapa
      </a>
      <TopBar />
      <main className="page">
        <Dashboard />
      </main>
    </AuthProvider>
  );
}
