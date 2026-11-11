import json
from typing import List, Optional

from app.domain.ports import ScheduleCheck

from sqlalchemy import create_engine, text

from app.domain.models import Itinerary, AirportSnapshot, DomainEvent
from app.domain.ports import ItineraryRepositoryPort

_INSERT_ITINERARY = text("""
    INSERT INTO itineraries
        (id, nombre_usuario, user_id, origin_airport_id, origin_iata,
         origin_name, origin_city, destination_airport_id, destination_iata,
         destination_name, destination_city, travel_date, departure_at, duration_minutes, created_at)
    VALUES
        (:id, :nombre_usuario, :user_id, :origin_id, :origin_iata,
         :origin_name, :origin_city, :dest_id, :dest_iata,
         :dest_name, :dest_city, :travel_date, :departure_at, :duration_minutes, :created_at)
""")

_INSERT_OUTBOX = text("""
    INSERT INTO outbox (aggregate_id, event_type, payload, status, created_at)
    VALUES (:aggregate_id, :event_type, CAST(:payload AS JSONB), 'PENDING', now())
""")


class PostgresItineraryRepository(ItineraryRepositoryPort):
    def __init__(self, database_url: str):
        self._engine = create_engine(database_url, pool_pre_ping=True, pool_timeout=5, connect_args={"connect_timeout": 3, "options": "-c statement_timeout=5000"})

    def _lock_and_check(self, conn, itinerary: Itinerary, schedule_check: Optional[ScheduleCheck]) -> None:
        """Serializa las escrituras de un mismo usuario (lock transaccional) y
        valida su agenda con lo ya confirmado: dos peticiones concurrentes no
        pueden crear vuelos que juntos serian incoherentes."""
        if schedule_check is None:
            return
        conn.execute(text("SELECT pg_advisory_xact_lock(hashtext(:u))"), {"u": itinerary.user_id})
        rows = conn.execute(
            text("SELECT * FROM itineraries WHERE user_id = :u ORDER BY departure_at"),
            {"u": itinerary.user_id}).mappings().all()
        schedule_check([self._row_to_itinerary(r) for r in rows])

    def save_with_event(self, itinerary: Itinerary, event: DomainEvent,
                        schedule_check: Optional[ScheduleCheck] = None) -> None:
        # Una sola transaccion: si cualquiera de los dos INSERT falla, ninguno
        # queda persistido (resuelve el Double Write Problem).
        with self._engine.begin() as conn:
            self._lock_and_check(conn, itinerary, schedule_check)
            conn.execute(_INSERT_ITINERARY, self._itinerary_to_params(itinerary))
            self._insert_event(conn, event)

    @staticmethod
    def _insert_event(conn, event: DomainEvent) -> None:
        conn.execute(_INSERT_OUTBOX, {
            "aggregate_id": event.aggregate_id,
            "event_type": event.event_type,
            "payload": json.dumps(event.payload),
        })

    def update_with_event(self, itinerary: Itinerary, event: DomainEvent,
                          schedule_check: Optional[ScheduleCheck] = None) -> None:
        with self._engine.begin() as conn:
            self._lock_and_check(conn, itinerary, schedule_check)
            result = conn.execute(
                text("""
                    UPDATE itineraries SET
                        origin_airport_id=:origin_id, origin_iata=:origin_iata,
                        origin_name=:origin_name, origin_city=:origin_city,
                        destination_airport_id=:dest_id, destination_iata=:dest_iata,
                        destination_name=:dest_name, destination_city=:dest_city,
                        travel_date=:travel_date, departure_at=:departure_at, duration_minutes=:duration_minutes
                    WHERE id=:id AND user_id=:user_id
                """),
                self._itinerary_to_params(itinerary),
            )
            if result.rowcount > 0:
                self._insert_event(conn, event)

    def get_by_id(self, itinerary_id: str, user_id: str) -> Optional[Itinerary]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM itineraries WHERE id = :id AND user_id = :user_id"),
                {"id": itinerary_id, "user_id": user_id},
            ).mappings().first()
        return self._row_to_itinerary(row) if row else None

    def list_by_user(self, user_id: str) -> List[Itinerary]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text("SELECT * FROM itineraries WHERE user_id = :user_id ORDER BY departure_at"),
                {"user_id": user_id},
            ).mappings().all()
        return [self._row_to_itinerary(r) for r in rows]

    def delete_with_event(self, itinerary_id: str, user_id: str, event: DomainEvent) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM itineraries WHERE id = :id AND user_id = :user_id"),
                {"id": itinerary_id, "user_id": user_id},
            )
            deleted = result.rowcount > 0
            if deleted:
                self._insert_event(conn, event)
        return deleted

    @staticmethod
    def _itinerary_to_params(itinerary: Itinerary) -> dict:
        return {
            "id": itinerary.id, "nombre_usuario": itinerary.nombre_usuario,
            "user_id": itinerary.user_id,
            "origin_id": itinerary.origin.airport_id, "origin_iata": itinerary.origin.iata_code,
            "origin_name": itinerary.origin.name, "origin_city": itinerary.origin.city,
            "dest_id": itinerary.destination.airport_id, "dest_iata": itinerary.destination.iata_code,
            "dest_name": itinerary.destination.name, "dest_city": itinerary.destination.city,
            "travel_date": itinerary.travel_date, "departure_at": itinerary.departure_at,
            "duration_minutes": itinerary.duration_minutes,
            "created_at": itinerary.created_at,
        }

    @staticmethod
    def _row_to_itinerary(row) -> Itinerary:
        return Itinerary(
            id=str(row["id"]), nombre_usuario=row["nombre_usuario"], user_id=row["user_id"],
            origin=AirportSnapshot(row["origin_airport_id"], row["origin_iata"], row["origin_name"], row["origin_city"]),
            destination=AirportSnapshot(row["destination_airport_id"], row["destination_iata"], row["destination_name"], row["destination_city"]),
            departure_at=row["departure_at"], duration_minutes=row["duration_minutes"],
            created_at=row["created_at"],
        )
