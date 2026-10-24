import { AuthProvider } from "./features/auth/AuthContext";
import { LoginForm } from "./features/auth/LoginForm";
import { AirportMapPage } from "./features/airports/AirportMapPage";
import { ItineraryPage } from "./features/itineraries/ItineraryPage";
import "./styles.css";

export function App() {
  return (
    <AuthProvider>
      <div className="app-shell">
        <header>
          <h1>Sistema de Itinerarios Personales</h1>
          <LoginForm />
        </header>
        <main>
          <AirportMapPage />
          <ItineraryPage />
        </main>
      </div>
    </AuthProvider>
  );
}
