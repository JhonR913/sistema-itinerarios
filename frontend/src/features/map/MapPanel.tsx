import { Suspense, lazy, useState } from "react";
import { Icon } from "../../components/ui/Icon";
import { StateMessage } from "../../components/ui/StateMessage";
import { usePrefersReducedMotion } from "../../lib/usePrefersReducedMotion";
import type { Airport } from "../../types/airport";
import { MapLegend } from "./MapLegend";
import type { MapRoute } from "./routes";

// Plotly.js pesa varios MB: se separa en su propio chunk y solo se
// descarga cuando el usuario realmente ve el mapa, no en el bundle inicial.
const AirportMap = lazy(() => import("../airports/AirportMap").then((m) => ({ default: m.AirportMap })));

interface MapPanelProps {
  /** Aeropuertos con coordenadas válidas. */
  airports: Airport[];
  /** Cuántos aeropuertos entregó el API, antes de validar coordenadas. */
  receivedAirportCount: number;
  invalidAirportCount: number;
  correctedAirportCount: number;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
  routes: MapRoute[];
  unresolvedCount: number;
  selectedId: string | null;
  onSelect: (itineraryId: string) => void;
  onClearSelection: () => void;
}

export function MapPanel({
  airports,
  receivedAirportCount,
  invalidAirportCount,
  correctedAirportCount,
  isLoading,
  error,
  onRetry,
  routes,
  unresolvedCount,
  selectedId,
  onSelect,
  onClearSelection,
}: MapPanelProps) {
  const [animationOn, setAnimationOn] = useState(true);
  const [viewResetKey, setViewResetKey] = useState(0);
  const prefersReducedMotion = usePrefersReducedMotion();
  const animationEnabled = animationOn && !prefersReducedMotion;
  const noneLocated = receivedAirportCount > 0 && airports.length === 0;
  const hasSelection = selectedId !== null && routes.some((r) => r.itinerary.id === selectedId);

  function resetView() {
    onClearSelection();
    setViewResetKey((n) => n + 1);
  }

  return (
    <section className="map-panel" id="mapa" aria-labelledby="map-title">
      <h2 id="map-title" className="visually-hidden">
        Mapa de aeropuertos e itinerarios
      </h2>

      <div className="map-canvas">
        {isLoading && <StateMessage variant="loading" title="Cargando aeropuertos…" />}

        {!isLoading && error && (
          <StateMessage
            variant="error"
            icon="alert"
            title="No se pudieron cargar los aeropuertos"
            action={
              <button type="button" className="btn btn--secondary btn--sm" onClick={onRetry}>
                <Icon name="refresh" size={16} /> Reintentar
              </button>
            }
          >
            {error}
          </StateMessage>
        )}

        {!isLoading && !error && noneLocated && (
          <StateMessage variant="error" icon="alert" title="No se pudo ubicar ningún aeropuerto">
            El servicio entregó {receivedAirportCount} aeropuertos, pero ninguno con coordenadas válidas.
          </StateMessage>
        )}

        {!isLoading && !error && !noneLocated && (
          <Suspense fallback={<StateMessage variant="loading" title="Cargando mapa…" />}>
            <AirportMap
              airports={airports}
              routes={routes}
              selectedId={selectedId}
              onSelect={onSelect}
              animationEnabled={animationEnabled}
              viewResetKey={viewResetKey}
            />
          </Suspense>
        )}
      </div>

      {!isLoading && !error && airports.length > 0 && (
        <>
          <div className="map-controls">
            <button type="button" className="map-chip" onClick={resetView}>
              <Icon name="globe" size={16} /> Vista general
            </button>
            {routes.length > 0 && (
              <button
                type="button"
                className="map-chip"
                aria-pressed={animationEnabled}
                disabled={prefersReducedMotion}
                title={
                  prefersReducedMotion
                    ? "Animación desactivada por la preferencia de movimiento reducido del sistema"
                    : undefined
                }
                onClick={() => setAnimationOn((on) => !on)}
              >
                <Icon name={animationEnabled ? "pause" : "play"} size={16} />
                {animationEnabled ? "Pausar avión" : "Animar avión"}
              </button>
            )}
          </div>

          <MapLegend hasRoutes={routes.length > 0} hasSelection={hasSelection} />

          {(invalidAirportCount > 0 || correctedAirportCount > 0) && (
            <p className="map-note map-note--top" role="status">
              <Icon name="alert" size={15} />
              {[
                invalidAirportCount > 0 && `${invalidAirportCount} sin coordenadas válidas (no se muestran)`,
                correctedAirportCount > 0 && `${correctedAirportCount} con coordenadas corregidas`,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}

          {unresolvedCount > 0 && (
            <p className="map-note" role="status">
              <Icon name="alert" size={15} />
              {unresolvedCount === 1
                ? "1 itinerario no se dibuja: no se encontraron las coordenadas de sus aeropuertos."
                : `${unresolvedCount} itinerarios no se dibujan: no se encontraron las coordenadas de sus aeropuertos.`}
            </p>
          )}
        </>
      )}
    </section>
  );
}
