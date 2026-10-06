from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import JSON, Date, DateTime, Integer, String, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.domain.events import ItineraryCreatedEvent
from app.domain.models import AirportSnapshot, Itinerary
from app.domain.ports import ItineraryRepository

OUTBOX_PENDING = "PENDING"


class Base(DeclarativeBase):
    pass


class ItineraryModel(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    departure_airport_id: Mapped[str] = mapped_column(String(64))
    arrival_airport_id: Mapped[str] = mapped_column(String(64))
    # Snapshot inmutable de los aeropuertos (ADR-006)
    departure_iata: Mapped[str | None] = mapped_column(String(8), nullable=True)
    departure_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    departure_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    arrival_iata: Mapped[str | None] = mapped_column(String(8), nullable=True)
    arrival_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    arrival_city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    travel_date: Mapped[date] = mapped_column(Date)
    duration_minutes: Mapped[int] = mapped_column(Integer)


class OutboxModel(Base):
    """Transactional Outbox: se escribe en la misma transacción que el itinerario."""

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aggregate_id: Mapped[str] = mapped_column(String(36), index=True)
    event_type: Mapped[str] = mapped_column(String(100))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    status: Mapped[str] = mapped_column(String(20), default=OUTBOX_PENDING, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _snapshot(iata: str | None, name: str | None, city: str | None) -> AirportSnapshot | None:
    return AirportSnapshot(iata, name or "", city or "") if iata is not None else None


def _to_domain(m: ItineraryModel) -> Itinerary:
    return Itinerary(
        id=m.id,
        username=m.username,
        departure_airport_id=m.departure_airport_id,
        arrival_airport_id=m.arrival_airport_id,
        travel_date=m.travel_date,
        duration_minutes=m.duration_minutes,
        departure_snapshot=_snapshot(m.departure_iata, m.departure_name, m.departure_city),
        arrival_snapshot=_snapshot(m.arrival_iata, m.arrival_name, m.arrival_city),
    )


def _apply_snapshots(m: ItineraryModel, i: Itinerary) -> None:
    d, a = i.departure_snapshot, i.arrival_snapshot
    m.departure_iata, m.departure_name, m.departure_city = (d.iata_code, d.name, d.city) if d else (None, None, None)
    m.arrival_iata, m.arrival_name, m.arrival_city = (a.iata_code, a.name, a.city) if a else (None, None, None)


class SqlAlchemyItineraryRepository(ItineraryRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, itinerary: Itinerary, event: ItineraryCreatedEvent) -> Itinerary:
        model = ItineraryModel(
            id=itinerary.id,
            username=itinerary.username,
            departure_airport_id=itinerary.departure_airport_id,
            arrival_airport_id=itinerary.arrival_airport_id,
            travel_date=itinerary.travel_date,
            duration_minutes=itinerary.duration_minutes,
        )
        _apply_snapshots(model, itinerary)
        outbox = OutboxModel(
            aggregate_id=itinerary.id,
            event_type=event.event_type,
            payload=event.to_payload(),
            status=OUTBOX_PENDING,
            created_at=datetime.now(timezone.utc),
        )
        try:
            self._s.add_all([model, outbox])
            self._s.commit()  # un solo commit: itinerario + outbox, o ninguno
        except Exception:
            self._s.rollback()
            raise
        return itinerary

    def get_by_id(self, itinerary_id: str) -> Itinerary | None:
        m = self._s.get(ItineraryModel, itinerary_id)
        return _to_domain(m) if m else None

    def list_by_username(self, username: str) -> list[Itinerary]:
        rows = self._s.scalars(select(ItineraryModel).where(ItineraryModel.username == username))
        return [_to_domain(m) for m in rows]

    def update(self, itinerary: Itinerary) -> Itinerary:
        m = self._s.get(ItineraryModel, itinerary.id)
        m.departure_airport_id = itinerary.departure_airport_id
        m.arrival_airport_id = itinerary.arrival_airport_id
        m.travel_date = itinerary.travel_date
        m.duration_minutes = itinerary.duration_minutes
        _apply_snapshots(m, itinerary)
        self._s.commit()
        return itinerary

    def delete(self, itinerary_id: str) -> None:
        m = self._s.get(ItineraryModel, itinerary_id)
        if m:
            self._s.delete(m)
            self._s.commit()
