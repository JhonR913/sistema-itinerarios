import { formatDuration, formatTravelDate } from "../../lib/format";
import type { ItinerarySummary } from "./summary";

interface SummaryCardsProps {
  /** null cuando no hay sesión: solo se muestra el dato público de aeropuertos. */
  summary: ItinerarySummary | null;
  airportCount: number;
}

interface Stat {
  label: string;
  value: string;
  hint?: string;
}

/** Métricas compactas derivadas solo de datos reales; si no hay dato, no hay tarjeta. */
export function SummaryCards({ summary, airportCount }: SummaryCardsProps) {
  const stats: Stat[] = [];

  if (summary) {
    stats.push({
      label: "Itinerarios",
      value: String(summary.total),
      hint: summary.total === 1 ? "guardado" : "guardados",
    });
    if (summary.next) {
      stats.push({
        label: "Próximo viaje",
        value: `${summary.next.origin.iata_code} → ${summary.next.destination.iata_code}`,
        hint: formatTravelDate(summary.next.travel_date),
      });
    }
    if (summary.total > 0) {
      stats.push({
        label: "Aeropuertos en tus rutas",
        value: String(summary.distinctAirports),
      });
      stats.push({ label: "Tiempo de vuelo planificado", value: formatDuration(summary.totalMinutes) });
    }
  }

  if (airportCount > 0) {
    stats.push({ label: "Aeropuertos disponibles", value: String(airportCount) });
  }

  if (stats.length === 0) return null;

  return (
    <ul className="stats" aria-label="Resumen">
      {stats.map((stat) => (
        <li key={stat.label} className="stat">
          <span className="stat__label">{stat.label}</span>
          <span className="stat__value">{stat.value}</span>
          {stat.hint && <span className="stat__hint">{stat.hint}</span>}
        </li>
      ))}
    </ul>
  );
}
