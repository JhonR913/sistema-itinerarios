from typing import List, Optional

from sqlalchemy import create_engine, text

from app.domain.models import Itinerary, AirportSnapshot
from app.domain.ports import ItineraryRepositoryPort


class PostgresItineraryRepository(ItineraryRepositoryPort):
    def __init__(self, database_url: str):
        self._engine = create_engine(database_url)

    def save(self, itinerary: Itinerary) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO itineraries
                        (id, nombre_usuario, user_id, origin_airport_id, origin_iata,
                         origin_name, origin_city, destination_airport_id, destination_iata,
                         destination_name, destination_city, travel_date, duration_minutes, created_at)
                    VALUES
                        (:id, :nombre_usuario, :user_id, :origin_id, :origin_iata,
                         :origin_name, :origin_city, :dest_id, :dest_iata,
                         :dest_name, :dest_city, :travel_date, :duration_minutes, :created_at)
                """),
                self._itinerary_to_params(itinerary),
            )

    def update(self, itinerary: Itinerary) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE itineraries SET
                        origin_airport_id=:origin_id, origin_iata=:origin_iata,
                        origin_name=:origin_name, origin_city=:origin_city,
                        destination_airport_id=:dest_id, destination_iata=:dest_iata,
                        destination_name=:dest_name, destination_city=:dest_city,
                        travel_date=:travel_date, duration_minutes=:duration_minutes
                    WHERE id=:id AND user_id=:user_id
                """),
                self._itinerary_to_params(itinerary),
            )

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
                text("SELECT * FROM itineraries WHERE user_id = :user_id ORDER BY created_at DESC"),
                {"user_id": user_id},
            ).mappings().all()
        return [self._row_to_itinerary(r) for r in rows]

    def delete(self, itinerary_id: str, user_id: str) -> bool:
        with self._engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM itineraries WHERE id = :id AND user_id = :user_id"),
                {"id": itinerary_id, "user_id": user_id},
            )
        return result.rowcount > 0

    @staticmethod
    def _itinerary_to_params(itinerary: Itinerary) -> dict:
        return {
            "id": itinerary.id, "nombre_usuario": itinerary.nombre_usuario,
            "user_id": itinerary.user_id,
            "origin_id": itinerary.origin.airport_id, "origin_iata": itinerary.origin.iata_code,
            "origin_name": itinerary.origin.name, "origin_city": itinerary.origin.city,
            "dest_id": itinerary.destination.airport_id, "dest_iata": itinerary.destination.iata_code,
            "dest_name": itinerary.destination.name, "dest_city": itinerary.destination.city,
            "travel_date": itinerary.travel_date, "duration_minutes": itinerary.duration_minutes,
            "created_at": itinerary.created_at,
        }

    @staticmethod
    def _row_to_itinerary(row) -> Itinerary:
        return Itinerary(
            id=row["id"], nombre_usuario=row["nombre_usuario"], user_id=row["user_id"],
            origin=AirportSnapshot(row["origin_airport_id"], row["origin_iata"], row["origin_name"], row["origin_city"]),
            destination=AirportSnapshot(row["destination_airport_id"], row["destination_iata"], row["destination_name"], row["destination_city"]),
            travel_date=row["travel_date"], duration_minutes=row["duration_minutes"],
            created_at=row["created_at"],
        )
