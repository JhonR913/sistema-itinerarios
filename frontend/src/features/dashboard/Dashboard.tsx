import { useCallback, useMemo, useState } from "react";
import { Icon } from "../../components/ui/Icon";
import { StateMessage } from "../../components/ui/StateMessage";
import { sanitizeAirports } from "../airports/coordinates";
import { useAirports } from "../airports/useAirports";
import { useAuth } from "../auth/AuthContext";
import { LoginForm } from "../auth/LoginForm";
import { ItineraryDetail } from "../itineraries/ItineraryDetail";
import { ItineraryForm } from "../itineraries/ItineraryForm";
import { ItineraryList } from "../itineraries/ItineraryList";
import { SummaryCards } from "../itineraries/SummaryCards";
import { summarizeItineraries } from "../itineraries/summary";
import { useItineraries } from "../itineraries/useItineraries";
import { MapPanel } from "../map/MapPanel";
import { buildRoutes } from "../map/routes";

/**
 * Composición de la pantalla: carga los datos una sola vez (aeropuertos e
 * itinerarios), mantiene la selección y la reparte entre mapa, lista y
 * detalle para que los tres permanezcan sincronizados.
 */
export function Dashboard() {
  const { username, token } = useAuth();
  const airportsState = useAirports();
  const { airports } = airportsState;
  const itinerariesState = useItineraries(token);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const isLoggedIn = Boolean(username && token);
  const itineraries = useMemo(() => (isLoggedIn ? itinerariesState.itineraries : []), [isLoggedIn, itinerariesState.itineraries]);

  const summary = useMemo(() => (isLoggedIn ? summarizeItineraries(itineraries) : null), [isLoggedIn, itineraries]);
  // Solo se dibujan aeropuertos con coordenadas válidas; el resto se informa en el mapa.
  const located = useMemo(() => sanitizeAirports(airports), [airports]);
  const { routes, unresolved } = useMemo(
    () => buildRoutes(itineraries, located.airports),
    [itineraries, located.airports],
  );

  // Si el itinerario seleccionado ya no existe (eliminado o recarga), no hay selección.
  const selected = itineraries.find((i) => i.id === selectedId) ?? null;

  const select = useCallback((id: string) => setSelectedId(id), []);
  const clearSelection = useCallback(() => setSelectedId(null), []);

  const { remove } = itinerariesState;
  const handleDelete = useCallback(
    async (id: string) => {
      await remove(id);
      setSelectedId((current) => (current === id ? null : current));
    },
    [remove],
  );

  const { create } = itinerariesState;
  const handleCreate = useCallback(
    async (input: Parameters<typeof create>[0]) => {
      await create(input);
      setShowForm(false);
    },
    [create],
  );

  return (
    <div className="dashboard">
      <section className="intro" aria-labelledby="page-title">
        <div>
          <p className="eyebrow">Panel de itinerarios</p>
          <h1 id="page-title">{isLoggedIn ? `Hola, ${username}` : "Planifica tus itinerarios aéreos"}</h1>
          <p className="muted intro__text">
            {isLoggedIn
              ? "Tus rutas guardadas sobre el mapa. Selecciona una para ver sus detalles."
              : "Inicia sesión para ver y crear tus rutas. El mapa muestra los aeropuertos disponibles."}
          </p>
        </div>
        <SummaryCards summary={summary} airportCount={airports.length} />
      </section>

      <div className="workspace">
        <MapPanel
          airports={located.airports}
          receivedAirportCount={airports.length}
          invalidAirportCount={located.invalidCount}
          correctedAirportCount={located.correctedCount}
          isLoading={airportsState.isLoading}
          error={airportsState.error}
          onRetry={airportsState.reload}
          routes={routes}
          unresolvedCount={unresolved.length}
          selectedId={selected?.id ?? null}
          onSelect={select}
          onClearSelection={clearSelection}
        />

        <aside className="side" id="itinerarios" aria-label="Itinerarios">
          {!isLoggedIn && <LoginForm />}

          {isLoggedIn && (
            <>
              {selected && (
                <ItineraryDetail key={selected.id} itinerary={selected} onBack={clearSelection} onDelete={handleDelete} />
              )}

              <section className="card trips" aria-labelledby="trips-title">
                <header className="trips__head">
                  <div>
                    <h2 id="trips-title">Mis itinerarios</h2>
                    <p className="muted trips__count">
                      {itineraries.length === 1 ? "1 itinerario" : `${itineraries.length} itinerarios`}
                    </p>
                  </div>
                  <button
                    type="button"
                    className={`btn btn--sm ${showForm ? "btn--secondary" : "btn--primary"}`}
                    aria-expanded={showForm}
                    onClick={() => setShowForm((open) => !open)}
                  >
                    <Icon name={showForm ? "close" : "plus"} size={16} />
                    {showForm ? "Cerrar" : "Nuevo"}
                  </button>
                </header>

                {showForm && username && (
                  <ItineraryForm airports={airports} username={username} onSubmit={handleCreate} />
                )}

                {itinerariesState.isLoading && itineraries.length === 0 && (
                  <StateMessage variant="loading" title="Cargando tus itinerarios…" />
                )}

                {itinerariesState.error && (
                  <StateMessage
                    variant="error"
                    icon="alert"
                    title="No se pudieron cargar tus itinerarios"
                    action={
                      <button type="button" className="btn btn--secondary btn--sm" onClick={() => void itinerariesState.reload()}>
                        <Icon name="refresh" size={16} /> Reintentar
                      </button>
                    }
                  >
                    {itinerariesState.error}
                  </StateMessage>
                )}

                {!itinerariesState.isLoading && !itinerariesState.error && itineraries.length === 0 && (
                  <StateMessage
                    variant="empty"
                    title="Aún no tienes itinerarios"
                    action={
                      !showForm ? (
                        <button type="button" className="btn btn--primary btn--sm" onClick={() => setShowForm(true)}>
                          <Icon name="plus" size={16} /> Crear el primero
                        </button>
                      ) : undefined
                    }
                  >
                    Crea uno y lo verás dibujado como ruta en el mapa.
                  </StateMessage>
                )}

                {itineraries.length > 0 && (
                  <ItineraryList itineraries={itineraries} selectedId={selected?.id ?? null} onSelect={select} />
                )}
              </section>
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
