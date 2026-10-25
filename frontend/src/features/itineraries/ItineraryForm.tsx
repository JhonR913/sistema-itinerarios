import { useId, useState, type FormEvent } from "react";
import { Icon } from "../../components/ui/Icon";
import type { Airport } from "../../types/airport";
import type { CreateItineraryInput } from "../../types/itinerary";

interface ItineraryFormProps {
  airports: Airport[];
  username: string;
  onSubmit: (input: CreateItineraryInput) => Promise<void>;
}

const INITIAL_DURATION_MINUTES = 90;

export function ItineraryForm({ airports, username, onSubmit }: ItineraryFormProps) {
  const uid = useId();
  const [originId, setOriginId] = useState("");
  const [destinationId, setDestinationId] = useState("");
  const [travelDate, setTravelDate] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(INITIAL_DURATION_MINUTES);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // RN-002, validada tambien en el backend: esto solo mejora la experiencia,
  // no reemplaza la validacion del servidor (guia de seguridad, falla #7).
  const sameAirportSelected = originId !== "" && originId === destinationId;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      await onSubmit({
        nombre_usuario: username,
        origin_airport_id: originId,
        destination_airport_id: destinationId,
        travel_date: travelDate,
        duration_minutes: durationMinutes,
      });
      setOriginId("");
      setDestinationId("");
      setTravelDate("");
      setDurationMinutes(INITIAL_DURATION_MINUTES);
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

  return (
    <form onSubmit={handleSubmit} className="card form" aria-labelledby={`${uid}-title`}>
      <h3 id={`${uid}-title`}>Nuevo itinerario</h3>

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

        <div className="field">
          <label htmlFor={`${uid}-date`}>Fecha de viaje</label>
          <input
            id={`${uid}-date`}
            className="input"
            type="date"
            value={travelDate}
            onChange={(e) => setTravelDate(e.target.value)}
            required
          />
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
            onChange={(e) => setDurationMinutes(Number(e.target.value))}
            required
          />
        </div>
      </div>

      {sameAirportSelected && (
        <p id={`${uid}-same`} className="field__error" role="alert">
          <Icon name="alert" size={15} /> El aeropuerto de salida y llegada no pueden ser el mismo.
        </p>
      )}
      {submitError && (
        <p className="field__error" role="alert">
          <Icon name="alert" size={15} /> {submitError}
        </p>
      )}

      <button type="submit" className="btn btn--primary btn--block" disabled={isSubmitting || sameAirportSelected}>
        {isSubmitting ? (
          <>
            <span className="spinner spinner--sm" aria-hidden="true" /> Creando…
          </>
        ) : (
          <>
            <Icon name="plus" size={16} /> Crear itinerario
          </>
        )}
      </button>
    </form>
  );
}
