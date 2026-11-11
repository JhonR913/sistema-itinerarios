"""Dominio puro. Invariantes de negocio RN-001 a RN-008
(Documento_Requerimientos.docx seccion 5)."""
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

# Todos los aeropuertos del sistema (API Colombia) estan en UTC-5, sin DST.
LOCAL_TZ = ZoneInfo("America/Bogota")


class InvalidItineraryError(ValueError):
    """Error de dominio. La capa API lo traduce a HTTP 422."""


@dataclass(frozen=True)
class DomainEvent:
    """Evento de dominio a publicar. Se persiste en la tabla outbox dentro
    de la MISMA transaccion que el agregado (Transactional Outbox), y un
    relay independiente lo entrega al broker."""
    event_type: str
    aggregate_id: str
    payload: dict


@dataclass(frozen=True)
class AirportSnapshot:
    """Referencia de valor (ADR-006): copia inmutable, no el agregado
    completo. Ver Documento_Arquitectura.docx seccion 5."""
    airport_id: str
    iata_code: str
    name: str
    city: str


@dataclass
class Itinerary:
    nombre_usuario: str
    origin: AirportSnapshot
    destination: AirportSnapshot
    departure_at: datetime          # instante de salida (aware; se guarda en UTC)
    duration_minutes: int
    user_id: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not isinstance(self.departure_at, datetime) or self.departure_at.tzinfo is None:
            raise InvalidItineraryError("La salida debe incluir fecha y hora con zona horaria.")
        self.departure_at = self.departure_at.astimezone(timezone.utc)
        if self.origin.airport_id == self.destination.airport_id:
            raise InvalidItineraryError(
                "El aeropuerto de salida y el de llegada no pueden ser el mismo."
            )
        if self.duration_minutes <= 0:
            raise InvalidItineraryError("La duracion debe ser un entero positivo.")
        if not self.nombre_usuario or not self.nombre_usuario.strip():
            raise InvalidItineraryError("El nombre de usuario es obligatorio.")
        if not self.user_id or not self.user_id.strip():
            raise InvalidItineraryError("El itinerario debe estar asociado a un usuario autenticado.")

    def update_route(self, origin: AirportSnapshot, destination: AirportSnapshot) -> None:
        if origin.airport_id == destination.airport_id:
            raise InvalidItineraryError(
                "El aeropuerto de salida y el de llegada no pueden ser el mismo."
            )
        self.origin = origin
        self.destination = destination

    @property
    def arrival_at(self) -> datetime:
        return self.departure_at + timedelta(minutes=self.duration_minutes)

    @property
    def travel_date(self) -> date:
        """Fecha local (America/Bogota) de la salida."""
        return self.departure_at.astimezone(LOCAL_TZ).date()

    def reschedule(self, departure_at: datetime) -> None:
        if departure_at.tzinfo is None:
            raise InvalidItineraryError("La salida debe incluir fecha y hora con zona horaria.")
        self.departure_at = departure_at.astimezone(timezone.utc)
