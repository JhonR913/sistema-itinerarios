"""Almacen durable de aeropuertos en PostgreSQL (airport_db). Es la
segunda capa de resiliencia, por debajo de Redis: si Redis no tiene nada
(fresco ni 'stale') y el circuito hacia API Colombia esta abierto, el
Adapter todavia puede servir datos desde aqui en vez de fallar.
RNF-SEC-004: SQLAlchemy con sentencias parametrizadas, sin concatenar SQL."""
from typing import List, Optional

from sqlalchemy import create_engine, text

from app.domain.models import Airport


class PostgresAirportStore:
    def __init__(self, database_url: str):
        self._engine = create_engine(database_url)

    def upsert_many(self, airports: List[Airport]) -> None:
        if not airports:
            return
        with self._engine.begin() as conn:
            for a in airports:
                conn.execute(
                    text("""
                        INSERT INTO airports (id, external_id, iata_code, name, city, latitude, longitude, cached_at)
                        VALUES (:id, :external_id, :iata_code, :name, :city, :latitude, :longitude, now())
                        ON CONFLICT (id) DO UPDATE SET
                            external_id = EXCLUDED.external_id,
                            iata_code = EXCLUDED.iata_code,
                            name = EXCLUDED.name,
                            city = EXCLUDED.city,
                            latitude = EXCLUDED.latitude,
                            longitude = EXCLUDED.longitude,
                            cached_at = now()
                    """),
                    {
                        "id": a.id, "external_id": a.external_id, "iata_code": a.iata_code,
                        "name": a.name, "city": a.city, "latitude": a.latitude, "longitude": a.longitude,
                    },
                )

    def get_all(self) -> List[Airport]:
        with self._engine.connect() as conn:
            rows = conn.execute(text("SELECT * FROM airports")).mappings().all()
        return [self._row_to_airport(r) for r in rows]

    def get_by_id(self, airport_id: str) -> Optional[Airport]:
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT * FROM airports WHERE id = :id"), {"id": airport_id}
            ).mappings().first()
        return self._row_to_airport(row) if row else None

    @staticmethod
    def _row_to_airport(row) -> Airport:
        return Airport(
            id=row["id"], external_id=row["external_id"], iata_code=row["iata_code"],
            name=row["name"], city=row["city"],
            latitude=float(row["latitude"]), longitude=float(row["longitude"]),
        )
