import { useState, type FormEvent } from "react";
import type { Airport } from "../../types/airport";
import type { CreateItineraryInput } from "../../types/itinerary";

interface ItineraryFormProps {
  airports: Airport[];
  username: string;
  onSubmit: (input: CreateItineraryInput) => Promise<void>;
}

const INITIAL_DURATION_MINUTES = 90;

export function ItineraryForm({ airports, username, onSubmit }: ItineraryFormProps) {
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

  return (
    <form onSubmit={handleSubmit} className="itinerary-form">
      <label>
        Salida
        <select value={originId} onChange={(e) => setOriginId(e.target.value)} required>
          <option value="" disabled>Selecciona un aeropuerto</option>
          {airports.map((a) => (
            <option key={a.id} value={a.id}>{a.name} ({a.iata_code})</option>
          ))}
        </select>
      </label>

      <label>
        Llegada
        <select value={destinationId} onChange={(e) => setDestinationId(e.target.value)} required>
          <option value="" disabled>Selecciona un aeropuerto</option>
          {airports.map((a) => (
            <option key={a.id} value={a.id}>{a.name} ({a.iata_code})</option>
          ))}
        </select>
      </label>

      <label>
        Fecha de viaje
        <input type="date" value={travelDate} onChange={(e) => setTravelDate(e.target.value)} required />
      </label>

      <label>
        Duración (minutos)
        <input
          type="number"
          min={1}
          max={2880}
          value={durationMinutes}
          onChange={(e) => setDurationMinutes(Number(e.target.value))}
          required
        />
      </label>

      {sameAirportSelected && (
        <p className="field-error">El aeropuerto de salida y llegada no pueden ser el mismo.</p>
      )}
      {submitError && <p className="field-error">{submitError}</p>}

      <button type="submit" disabled={isSubmitting || sameAirportSelected}>
        {isSubmitting ? "Creando…" : "Crear itinerario"}
      </button>
    </form>
  );
}
