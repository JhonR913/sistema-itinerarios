from datetime import date

from sqlalchemy import Date, Integer, String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.domain.models import Itinerary
from app.domain.ports import ItineraryRepository


class Base(DeclarativeBase):
    pass


class ItineraryModel(Base):
    __tablename__ = "itineraries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    departure_airport_id: Mapped[str] = mapped_column(String(64))
    arrival_airport_id: Mapped[str] = mapped_column(String(64))
    travel_date: Mapped[date] = mapped_column(Date)
    duration_minutes: Mapped[int] = mapped_column(Integer)


def _to_domain(m: ItineraryModel) -> Itinerary:
    return Itinerary(
        id=m.id,
        username=m.username,
        departure_airport_id=m.departure_airport_id,
        arrival_airport_id=m.arrival_airport_id,
        travel_date=m.travel_date,
        duration_minutes=m.duration_minutes,
    )


class SqlAlchemyItineraryRepository(ItineraryRepository):
    def __init__(self, session: Session) -> None:
        self._s = session

    def add(self, itinerary: Itinerary) -> Itinerary:
        self._s.add(ItineraryModel(**vars(itinerary)))
        self._s.commit()
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
        self._s.commit()
        return itinerary

    def delete(self, itinerary_id: str) -> None:
        m = self._s.get(ItineraryModel, itinerary_id)
        if m:
            self._s.delete(m)
            self._s.commit()
