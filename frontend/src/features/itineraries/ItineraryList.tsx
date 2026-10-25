import type { Itinerary } from "../../types/itinerary";

interface ItineraryListProps {
  itineraries: Itinerary[];
  onDelete: (id: string) => void;
}

export function ItineraryList({ itineraries, onDelete }: ItineraryListProps) {
  if (itineraries.length === 0) {
    return <p className="empty-state">Todavía no tienes itinerarios creados.</p>;
  }

  return (
    <ul className="itinerary-list">
      {itineraries.map((itinerary) => (
        <li key={itinerary.id}>
          <span>
            {itinerary.origin.iata_code} → {itinerary.destination.iata_code}
            {" "}· {itinerary.travel_date} · {itinerary.duration_minutes} min
          </span>
          <button onClick={() => onDelete(itinerary.id)} aria-label={`Eliminar itinerario ${itinerary.id}`}>
            Eliminar
          </button>
        </li>
      ))}
    </ul>
  );
}
