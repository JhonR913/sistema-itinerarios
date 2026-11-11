"""Logica de recordatorios: calculo de la hora de envio y aplicacion de los
eventos Created / Updated / Deleted sobre la tabla `reminders`.

Si el evento trae `departure_at` (instante ISO 8601 con zona), el recordatorio
se envia `REMINDER_LEAD_HOURS` (def. 24) antes de la SALIDA REAL; si la salida
es en menos de ese margen, el aviso queda vencido y se envia de inmediato.
Si el evento no trae hora (eventos antiguos) se usa `travel_date` (FECHA): el
aviso sale `REMINDER_LEAD_HOURS` antes de las 00:00 de esa fecha en
`REMINDER_TIMEZONE` (def. America/Bogota). Todo se guarda en UTC (timestamptz).
Un viaje que ya salio no genera recordatorio.
"""
import os
import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

IATA_RE = re.compile(r"^[A-Za-z0-9/]{2,4}$")


def settings() -> tuple[str, int]:
    return os.environ.get("REMINDER_TIMEZONE", "America/Bogota"), int(os.environ.get("REMINDER_LEAD_HOURS", "24"))


def parse_instant(value) -> Optional[datetime]:
    """ISO 8601 con zona -> datetime UTC. None si no viene. ValueError si es invalido."""
    if value in (None, ""):
        return None
    dt = datetime.fromisoformat(value) if isinstance(value, str) else None
    if dt is None or dt.tzinfo is None:
        raise ValueError("instante invalido: se requiere ISO 8601 con zona horaria")
    return dt.astimezone(timezone.utc)


def compute_remind_at(travel_date: date, tz_name: str, lead_hours: int,
                      departure_at: Optional[datetime] = None) -> datetime:
    base = departure_at or datetime.combine(travel_date, time(0, 0), tzinfo=ZoneInfo(tz_name))
    return (base - timedelta(hours=lead_hours)).astimezone(timezone.utc)


def is_past_trip(travel_date: date, tz_name: str, now: Optional[datetime] = None,
                 departure_at: Optional[datetime] = None) -> bool:
    now = now or datetime.now(timezone.utc)
    if departure_at is not None:
        return departure_at <= now
    return travel_date < now.astimezone(ZoneInfo(tz_name)).date()


def is_valid_email(value: str) -> bool:
    """usuario@dominio.tld sin espacios, usuario <= 64. Sin regex (evita backtracking/ReDoS)."""
    local, at, domain = value.partition("@")
    if not at or not 1 <= len(local) <= 64 or "@" in domain or any(c.isspace() for c in value):
        return False
    return "." in domain[1:-1]


def valid_email(value) -> Optional[str]:
    return value if isinstance(value, str) and len(value) <= 254 and is_valid_email(value) else None


def initial_status(email: Optional[str], travel_date: date, tz_name: str, now: Optional[datetime] = None,
                   departure_at: Optional[datetime] = None) -> str:
    if not email:
        return "SKIPPED"          # sin destinatario
    if is_past_trip(travel_date, tz_name, now, departure_at):
        return "SKIPPED"          # viaje ya pasado
    return "PENDING"


def register_created(cur, payload: dict, event_id: int, now: Optional[datetime] = None) -> None:
    tz_name, lead = settings()
    travel_date = date.fromisoformat(payload["travel_date"])
    departure, arrival = parse_instant(payload.get("departure_at")), parse_instant(payload.get("arrival_at"))
    email = valid_email(payload.get("email"))
    cur.execute(
        """INSERT INTO reminders (itinerary_id, email, nombre_usuario, origin, destination,
                                  origin_city, destination_city, departure_at, arrival_at,
                                  travel_date, remind_at, status, last_event_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (itinerary_id) DO NOTHING""",
        (payload["itinerary_id"], email, payload["nombre_usuario"], payload["origin"], payload["destination"],
         payload.get("origin_city"), payload.get("destination_city"), departure, arrival,
         travel_date, compute_remind_at(travel_date, tz_name, lead, departure),
         initial_status(email, travel_date, tz_name, now, departure), event_id),
    )


def apply_updated(cur, payload: dict, event_id: int, now: Optional[datetime] = None) -> bool:
    """Reprograma. Si ya se habia enviado, vuelve a PENDING (el viaje cambio:
    se reenvia con los datos nuevos). Una fila CANCELLED nunca revive."""
    tz_name, lead = settings()
    travel_date = date.fromisoformat(payload["travel_date"])
    departure, arrival = parse_instant(payload.get("departure_at")), parse_instant(payload.get("arrival_at"))
    past = is_past_trip(travel_date, tz_name, now, departure)
    cur.execute(
        """UPDATE reminders SET
               origin = %s, destination = %s, origin_city = %s, destination_city = %s,
               departure_at = %s, arrival_at = %s, travel_date = %s, remind_at = %s,
               status = CASE WHEN status = 'CANCELLED' THEN 'CANCELLED'
                             WHEN email IS NULL OR %s THEN 'SKIPPED'
                             ELSE 'PENDING' END,
               sent_at = NULL, attempts = 0, last_error = NULL,
               last_event_id = %s, updated_at = now()
           WHERE itinerary_id = %s AND last_event_id < %s""",
        (payload["origin"], payload["destination"], payload.get("origin_city"), payload.get("destination_city"),
         departure, arrival, travel_date,
         compute_remind_at(travel_date, tz_name, lead, departure), past, event_id,
         payload["itinerary_id"], event_id),
    )
    return cur.rowcount == 1


def apply_deleted(cur, payload: dict, event_id: int) -> None:
    """Cancela y borra los datos personales. Si el Created aun no llego deja
    una lapida (CANCELLED) para que el Created tardio no cree el recordatorio."""
    cur.execute(
        """INSERT INTO reminders (itinerary_id, status, last_event_id)
           VALUES (%s, 'CANCELLED', %s)
           ON CONFLICT (itinerary_id) DO UPDATE SET
               status = 'CANCELLED', email = NULL, nombre_usuario = NULL,
               last_event_id = EXCLUDED.last_event_id, updated_at = now()
           WHERE reminders.last_event_id < EXCLUDED.last_event_id""",
        (payload["itinerary_id"], event_id),
    )
