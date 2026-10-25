import { Icon } from "../../components/ui/Icon";
import { formatDuration, formatTravelDate } from "../../lib/format";
import type { Itinerary } from "../../types/itinerary";

interface ItineraryListProps {
  itineraries: Itinerary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

/** Lista seleccionable: cada trayecto se reconoce de un vistazo por sus códigos IATA. */
export function ItineraryList({ itineraries, selectedId, onSelect }: ItineraryListProps) {
  return (
    <ul className="trip-list">
      {itineraries.map((itinerary) => {
        const isSelected = itinerary.id === selectedId;
        return (
          <li key={itinerary.id}>
            <button
              type="button"
              className={`trip${isSelected ? " trip--selected" : ""}`}
              aria-pressed={isSelected}
              onClick={() => onSelect(itinerary.id)}
            >
              <span className="trip__route">
                <span className="trip__code">{itinerary.origin.iata_code}</span>
                <span className="trip__line" aria-hidden="true">
                  <Icon name="plane" size={14} />
                </span>
                <span className="visually-hidden"> a </span>
                <span className="trip__code">{itinerary.destination.iata_code}</span>
              </span>
              <span className="trip__cities">
                {itinerary.origin.city} → {itinerary.destination.city}
              </span>
              <span className="trip__meta">
                <span>
                  <Icon name="calendar" size={14} /> {formatTravelDate(itinerary.travel_date)}
                </span>
                <span>
                  <Icon name="clock" size={14} /> {formatDuration(itinerary.duration_minutes)}
                </span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
