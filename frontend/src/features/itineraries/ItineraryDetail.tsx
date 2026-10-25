import { useState } from "react";
import { Icon } from "../../components/ui/Icon";
import { formatDuration, formatTravelDate } from "../../lib/format";
import type { Itinerary } from "../../types/itinerary";

interface ItineraryDetailProps {
  itinerary: Itinerary;
  onBack: () => void;
  onDelete: (id: string) => Promise<void>;
}

/** Panel contextual del itinerario seleccionado, con eliminación en dos pasos. */
export function ItineraryDetail({ itinerary, onBack, onDelete }: ItineraryDetailProps) {
  const [confirming, setConfirming] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function confirmDelete() {
    setIsDeleting(true);
    setError(null);
    try {
      await onDelete(itinerary.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo eliminar el itinerario");
      setIsDeleting(false);
      setConfirming(false);
    }
  }

  return (
    <article className="card detail" aria-labelledby="detail-title">
      <header className="detail__head">
        <p className="eyebrow">Itinerario seleccionado</p>
        <button type="button" className="icon-btn" onClick={onBack} aria-label="Volver a la vista general">
          <Icon name="close" size={18} />
        </button>
      </header>

      <h3 id="detail-title" className="visually-hidden">
        Itinerario de {itinerary.origin.city} a {itinerary.destination.city}
      </h3>

      <div className="detail__route" aria-hidden="true">
        <div>
          <span className="detail__code">{itinerary.origin.iata_code}</span>
          <span className="detail__city">{itinerary.origin.city}</span>
        </div>
        <Icon name="arrow" size={22} />
        <div>
          <span className="detail__code">{itinerary.destination.iata_code}</span>
          <span className="detail__city">{itinerary.destination.city}</span>
        </div>
      </div>

      <dl className="detail__facts">
        <div>
          <dt>Salida desde</dt>
          <dd>{itinerary.origin.name}</dd>
        </div>
        <div>
          <dt>Llegada a</dt>
          <dd>{itinerary.destination.name}</dd>
        </div>
        <div>
          <dt>Fecha</dt>
          <dd>{formatTravelDate(itinerary.travel_date, "long")}</dd>
        </div>
        <div>
          <dt>Duración</dt>
          <dd>{formatDuration(itinerary.duration_minutes)}</dd>
        </div>
      </dl>

      {error && (
        <p className="field__error" role="alert">
          <Icon name="alert" size={15} /> {error}
        </p>
      )}

      <div className="detail__actions">
        <button type="button" className="btn btn--secondary btn--sm" onClick={onBack}>
          <Icon name="globe" size={16} /> Vista general
        </button>

        {!confirming ? (
          <button type="button" className="btn btn--danger-quiet btn--sm" onClick={() => setConfirming(true)}>
            <Icon name="trash" size={16} /> Eliminar
          </button>
        ) : (
          <span className="detail__confirm" role="group" aria-label="Confirmar eliminación">
            <button type="button" className="btn btn--danger btn--sm" onClick={confirmDelete} disabled={isDeleting}>
              {isDeleting ? "Eliminando…" : "Sí, eliminar"}
            </button>
            <button
              type="button"
              className="btn btn--secondary btn--sm"
              onClick={() => setConfirming(false)}
              disabled={isDeleting}
            >
              Cancelar
            </button>
          </span>
        )}
      </div>
    </article>
  );
}
