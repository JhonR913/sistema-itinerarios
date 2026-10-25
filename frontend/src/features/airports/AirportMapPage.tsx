import { Suspense, lazy } from "react";
import { useAirports } from "./useAirports";

// Plotly.js pesa varios MB: se separa en su propio chunk y solo se
// descarga cuando el usuario realmente ve el mapa, no en el bundle inicial.
const AirportMap = lazy(() => import("./AirportMap").then((m) => ({ default: m.AirportMap })));

export function AirportMapPage() {
  const { airports, isLoading, error, reload } = useAirports();

  if (isLoading) {
    return <p>Cargando aeropuertos…</p>;
  }

  if (error) {
    return (
      <div className="error-state">
        <p>{error}</p>
        <button onClick={reload}>Reintentar</button>
      </div>
    );
  }

  return (
    <section>
      <h2>Aeropuertos de Colombia</h2>
      <Suspense fallback={<p>Cargando mapa…</p>}>
        <AirportMap airports={airports} />
      </Suspense>
    </section>
  );
}
