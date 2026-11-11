"""Regla de agenda del viajero (dominio puro).

Un viajero no puede estar en dos lugares a la vez. Dado el vuelo candidato y
los demas vuelos del mismo usuario:

  1. OVERLAP        - no puede traslaparse en el tiempo con otro vuelo
                      (salir a las 7 en Tunja si estas en vuelo 6-8).
  2. ORIGIN_MISMATCH - el origen debe ser el destino del vuelo inmediatamente
                      anterior (tras aterrizar en Valledupar solo puedes salir
                      de Valledupar).
  3. NEXT_MISMATCH  - el destino debe ser el origen del vuelo inmediatamente
                      siguiente (para poder tomarlo).

`min_connection_minutes` es el margen minimo entre llegar y volver a salir
(0 por defecto: aterrizar a las 8:00 permite salir a las 8:00).
"""
from datetime import timedelta
from typing import Iterable

from .models import Itinerary, LOCAL_TZ


class ScheduleConflictError(Exception):
    """El vuelo no es coherente con la agenda del usuario (HTTP 409)."""

    def __init__(self, code: str, message: str, conflicting_itinerary_id: str):
        super().__init__(message)
        self.code = code
        self.conflicting_itinerary_id = conflicting_itinerary_id


def _fmt(dt) -> str:
    return dt.astimezone(LOCAL_TZ).strftime("%d/%m/%Y %H:%M")


def _describe(it: Itinerary) -> str:
    return (f"{it.origin.city} ({it.origin.iata_code}) -> {it.destination.city} "
            f"({it.destination.iata_code}), {_fmt(it.departure_at)} a {_fmt(it.arrival_at)}")


def check_schedule(candidate: Itinerary, existing: Iterable[Itinerary],
                   min_connection_minutes: int = 0) -> None:
    buf = timedelta(minutes=min_connection_minutes)
    others = sorted((e for e in existing if e.id != candidate.id), key=lambda e: e.departure_at)

    for e in others:
        if candidate.departure_at < e.arrival_at + buf and e.departure_at < candidate.arrival_at + buf:
            raise ScheduleConflictError(
                "OVERLAP",
                f"Este vuelo se cruza con otro tuyo: {_describe(e)}. "
                + (f"Debe haber al menos {min_connection_minutes} min entre vuelos." if buf else ""),
                e.id)

    before = [e for e in others if e.arrival_at + buf <= candidate.departure_at]
    if before:
        prev = max(before, key=lambda e: e.arrival_at)
        if prev.destination.airport_id != candidate.origin.airport_id:
            raise ScheduleConflictError(
                "ORIGIN_MISMATCH",
                f"Tu vuelo anterior llega a {prev.destination.city} ({prev.destination.iata_code}) "
                f"el {_fmt(prev.arrival_at)}; no puedes salir desde {candidate.origin.city} "
                f"({candidate.origin.iata_code}) sin haber estado alli.",
                prev.id)

    after = [e for e in others if candidate.arrival_at + buf <= e.departure_at]
    if after:
        nxt = min(after, key=lambda e: e.departure_at)
        if nxt.origin.airport_id != candidate.destination.airport_id:
            raise ScheduleConflictError(
                "NEXT_MISMATCH",
                f"Tu siguiente vuelo sale de {nxt.origin.city} ({nxt.origin.iata_code}) "
                f"el {_fmt(nxt.departure_at)}; este vuelo termina en {candidate.destination.city} "
                f"({candidate.destination.iata_code}) y no podrias tomarlo.",
                nxt.id)
