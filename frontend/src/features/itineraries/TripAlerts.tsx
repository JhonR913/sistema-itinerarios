import { Icon } from "../../components/ui/Icon";
import { formatDateTime, timeUntil } from "../../lib/schedule";
import type { Itinerary } from "../../types/itinerary";

interface TripAlertsProps {
  /** Próximo vuelo que aún no sale (ver summarizeItineraries). */
  next: Itinerary | null;
  /** ¿Inició sesión con correo? Sin correo no hay recordatorios por email. */
  hasEmail: boolean;
  now?: Date;
}

const SOON_HOURS = 48;

/** Avisos sobre tu próximo vuelo y sobre el estado de los recordatorios por correo. */
export function TripAlerts({ next, hasEmail, now = new Date() }: TripAlertsProps) {
  if (!next) return null;
  const remaining = timeUntil(next.departure_at, now);
  const hoursLeft = (Date.parse(next.departure_at) - now.getTime()) / 3_600_000;
  const soon = remaining !== null && hoursLeft <= SOON_HOURS;
  const route = `${next.origin.iata_code} → ${next.destination.iata_code}`;

  return (
    <section className="card alerts" aria-label="Alertas de viaje">
      {soon && (
        <p className="alert alert--soon" role="status">
          <Icon name="plane" size={16} />
          <span>
            Tu vuelo <strong>{route}</strong> sale {remaining} ({formatDateTime(next.departure_at)}).
          </span>
        </p>
      )}
      {hasEmail ? (
        <p className="alert alert--ok">
          <Icon name="clock" size={16} />
          <span>Te enviaremos un recordatorio por correo 24 h antes de cada salida.</span>
        </p>
      ) : (
        <p className="alert alert--warn">
          <Icon name="alert" size={16} />
          <span>Sin correo no podemos enviarte recordatorios. Cierra sesión y vuelve a entrar indicando tu correo.</span>
        </p>
      )}
    </section>
  );
}
