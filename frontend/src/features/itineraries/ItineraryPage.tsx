import { useAirports } from "../airports/useAirports";
import { useAuth } from "../auth/AuthContext";
import { useItineraries } from "./useItineraries";
import { ItineraryForm } from "./ItineraryForm";
import { ItineraryList } from "./ItineraryList";

export function ItineraryPage() {
  const { username, token } = useAuth();
  const { airports } = useAirports();
  const { itineraries, isLoading, error, create, remove } = useItineraries(token);

  if (!username || !token) {
    return <p>Inicia sesión para gestionar tus itinerarios.</p>;
  }

  return (
    <section>
      <h2>Mis itinerarios</h2>
      <ItineraryForm airports={airports} username={username} onSubmit={create} />
      {isLoading && <p>Cargando…</p>}
      {error && <p className="field-error">{error}</p>}
      <ItineraryList itineraries={itineraries} onDelete={remove} />
    </section>
  );
}
