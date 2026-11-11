import { useEffect, useId, useMemo, useState, type FormEvent } from "react";
import { Icon } from "../../components/ui/Icon";
import { formatDuration } from "../../lib/format";
import {
  describeConflict,
  estimateDurationMinutes,
  formatDateTime,
  nextAvailability,
  nowLocalInputValue,
  toDepartureIso,
} from "../../lib/schedule";
import type { Airport } from "../../types/airport";
import type { CreateItineraryInput, Itinerary } from "../../types/itinerary";

interface ItineraryFormProps {
  airports: Airport[];
  username: string;
  /** Agenda actual del usuario: sirve para avisar de conflictos antes de enviar. */
  itineraries: Itinerary[];
  onSubmit: (input: CreateItineraryInput) => Promise<void>;
}

const INITIAL_DURATION_MINUTES = 90;

export function ItineraryForm({ airports, username, itineraries, onSubmit }: ItineraryFormProps) {
  const uid = useId();
  const [originId, setOriginId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [departure, setDeparture] = useState(""); // "YYYY-MM-DDTHH:mm", hora de Colombia
  const [durationMinutes, setDurationMinutes] = useState(INITIAL_DURATION_MINUTES);
  const [durationEdited, setDurationEdited] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // RN-002, validada tambien en el backend: esto solo mejora la experiencia,
  // no reemplaza la validacion del servidor (guia de seguridad, falla #7).
  const sameAirportSelected = originId !== "" && originId === destinationId;

  const byId = useMemo(() => new Map(airports.map((a) => [a.id, a])), [airports]);
  const origin = byId.get(originId);
  const destination = byId.get(destinationId);

  // La duración se propone a partir de la distancia, hasta que el usuario la edite.
  useEffect(() => {
    if (origin && destination && !durationEdited && origin.id !== destination.id) {
      setDurationMinutes(estimateDurationMinutes(origin, destination));
    }
  }, [origin, destination, durationEdited]);

  const departureMs = departure ? Date.parse(toDepartureIso(departure)) : NaN;
  const arrivalMs = Number.isFinite(departureMs) ? departureMs + durationMinutes * 60_000 : NaN;
  const isPast = Number.isFinite(departureMs) && departureMs <= Date.now();

  // Reglas de agenda: aviso inmediato (el servidor decide en definitiva).
  const conflict = useMemo(() => {
    if (!originId || !destinationId || sameAirportSelected || !Number.isFinite(departureMs) || durationMinutes <= 0) {
      return null;
    }
    return describeConflict({ originId, destinationId, departureMs, durationMinutes }, itineraries);
  }, [originId, destinationId, sameAirportSelected, departureMs, durationMinutes, itineraries]);

  const availability = useMemo(() => nextAvailability(itineraries), [itineraries]);

  function applyAvailability() {
    if (!availability) return;
    setOriginId(availability.airportId);
    // Sugiere salir en cuanto aterrizas (hora de Colombia, redondeada al minuto).
    const local = new Date(Date.parse(availability.availableAt) - 5 * 3_600_000).toISOString().slice(0, 16);
    if (local >= nowLocalInputValue()) setDeparture(local);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({
        nombre_usuario: username,
        origin_airport_id: originId,
        destination_airport_id: destinationId,
        departure_at: toDepartureIso(departure),
        duration_minutes: durationMinutes,
      });
      setOriginId("");
      setDestinationId("");
      setDeparture("");
      setDurationMinutes(INITIAL_DURATION_MINUTES);
      setDurationEdited(false);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "No se pudo crear el itinerario");
    } finally {
      setIsSubmitting(false);
    }
  }

  const options = airports.map((a) => (
    <option key={a.id} value={a.id}>
      {a.city} · {a.name} ({a.iata_code})
    </option>
  ));

  const blocked = sameAirportSelected || isPast || conflict !== null;

  return (
    <form onSubmit={handleSubmit} className="card form" aria-labelledby={`${uid}-title`}>
      <h3 id={`${uid}-title`}>Nuevo vuelo</h3>

      {availability && (
        <p className="form__hint">
          <Icon name="pin" size={15} />
          <span>
            Tu último vuelo llega a <strong>{availability.city}</strong> ({formatDateTime(availability.availableAt)}). Desde ahí puedes
            salir a partir de esa hora.{" "}
            <button type="button" className="link-btn" onClick={applyAvailability}>
              Usar {availability.city} como salida
            </button>
          </span>
        </p>
      )}

      <div className="form__grid">
        <div className="field">
          <label htmlFor={`${uid}-origin`}>Salida</label>
          <select
            id={`${uid}-origin`}
            className="input"
            value={originId}
            onChange={(e) => setOriginId(e.target.value)}
            required
          >
            <option value="" disabled>
              Selecciona un aeropuerto
            </option>
            {options}
          </select>
        </div>

        <div className="field">
          <label htmlFor={`${uid}-destination`}>Llegada</label>
          <select
            id={`${uid}-destination`}
            className={`input${sameAirportSelected ? " input--error" : ""}`}
            value={destinationId}
            onChange={(e) => setDestinationId(e.target.value)}
            aria-invalid={sameAirportSelected ? true : undefined}
            aria-describedby={sameAirportSelected ? `${uid}-same` : undefined}
            required
          >
            <option value="" disabled>
              Selecciona un aeropuerto
            </option>
            {options}
          </select>
        </div>

        <div className="field field--wide">
          <label htmlFor={`${uid}-departure`}>Fecha y hora de salida</label>
          <input
            id={`${uid}-departure`}
            className={`input${isPast ? " input--error" : ""}`}
            type="datetime-local"
            min={nowLocalInputValue()}
            value={departure}
            onChange={(e) => setDeparture(e.target.value)}
            required
          />
          <small className="muted">Hora de Colombia (UTC-5)</small>
        </div>

        <div className="field">
          <label htmlFor={`${uid}-duration`}>Duración (minutos)</label>
          <input
            id={`${uid}-duration`}
            className="input"
            type="number"
            min={1}
            max={2880}
            value={durationMinutes}
            onChange={(e) => {
              setDurationMinutes(Number(e.target.value));
              setDurationEdited(true);
            }}
            required
          />
          <small className="muted">
            {durationEdited ? "Ajustada por ti" : origin && destination ? "Estimada según la distancia" : "Elige salida y llegada"}
          </small>
        </div>
      </div>

      {Number.isFinite(arrivalMs) && !isPast && (
        <p className="form__hint" aria-live="polite">
          <Icon name="clock" size={15} />
          <span>
            Llegas el <strong>{formatDateTime(new Date(arrivalMs).toISOString())}</strong> ({formatDuration(durationMinutes)} de vuelo).
          </span>
        </p>
      )}

      {sameAirportSelected && (
        <p id={`${uid}-same`} className="field__error" role="alert">
          <Icon name="alert" size={15} /> El aeropuerto de salida y llegada no pueden ser el mismo.
        </p>
      )}
      {isPast && (
        <p className="field__error" role="alert">
          <Icon name="alert" size={15} /> La salida debe ser una fecha y hora futura.
        </p>
      )}
      {conflict && (
        <p className="field__error" role="alert">
          <Icon name="alert" size={15} /> {conflict}
        </p>
      )}
      {submitError && (
        <p className="field__error" role="alert">
          <Icon name="alert" size={15} /> {submitError}
        </p>
      )}

      <button type="submit" className="btn btn--primary btn--block" disabled={isSubmitting || blocked}>
        {isSubmitting ? (
          <>
            <span className="spinner spinner--sm" aria-hidden="true" /> Guardando…
          </>
        ) : (
          <>
            <Icon name="plus" size={16} /> Guardar vuelo
          </>
        )}
      </button>
    </form>
  );
}
