"""Integracion contra PostgreSQL REAL (se omite si no hay TEST_DATABASE_URL).

    TEST_DATABASE_URL=postgresql://user:pw@localhost/itinerary_test pytest tests/integration

Aplica las migraciones Alembic reales y verifica las garantias del patron
Transactional Outbox: atomicidad, entrega con confirm y SKIP LOCKED."""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from alembic import command
from alembic.config import Config
from pika.exceptions import AMQPConnectionError
from sqlalchemy import create_engine, text

from app.domain.models import AirportSnapshot, DomainEvent, Itinerary
from app.infrastructure.adapters import outbox_worker
from app.infrastructure.adapters.postgres_repository import PostgresItineraryRepository

DB_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL no definida")

ROOT = Path(__file__).resolve().parents[2]
BOG = AirportSnapshot("1", "BOG", "El Dorado", "Bogota")
MDE = AirportSnapshot("2", "MDE", "JMC", "Medellin")


@pytest.fixture(scope="module")
def engine():
    os.environ["DATABASE_URL"] = DB_URL
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(cfg, "head")
    eng = create_engine(DB_URL)
    yield eng
    eng.dispose()


@pytest.fixture(autouse=True)
def clean(engine):
    with engine.begin() as c:
        c.execute(text("TRUNCATE itineraries, outbox RESTART IDENTITY"))


def _itinerary(user="u1"):
    return Itinerary(nombre_usuario="jhon", origin=BOG, destination=MDE,
                     departure_at=datetime.now(timezone.utc) + timedelta(days=30), duration_minutes=90, user_id=user)


def _event(it):
    return DomainEvent("ItineraryCreatedEvent", it.id, {"itinerary_id": it.id, "nombre_usuario": "jhon",
                                                       "origin": "BOG", "destination": "MDE", "travel_date": "2026-12-01"})


def _count(engine, table, where="true"):
    with engine.connect() as c:
        return c.execute(text(f"SELECT count(*) FROM {table} WHERE {where}")).scalar()  # noqa: S608 - constantes de prueba


def test_save_with_event_persists_itinerary_and_pending_event(engine):
    repo = PostgresItineraryRepository(DB_URL)
    it = _itinerary()
    repo.save_with_event(it, _event(it))
    assert _count(engine, "itineraries") == 1
    assert _count(engine, "outbox", "status='PENDING'") == 1
    assert repo.get_by_id(it.id, "u1").destination.iata_code == "MDE"
    assert repo.get_by_id(it.id, "otro") is None


def test_failure_writing_event_rolls_back_the_itinerary(engine):
    """Double Write Problem: si el evento no se puede guardar, tampoco
    debe quedar el itinerario."""
    repo = PostgresItineraryRepository(DB_URL)
    it = _itinerary()
    bad_event = DomainEvent("ItineraryCreatedEvent", "no-es-un-uuid", {})
    with pytest.raises(Exception):
        repo.save_with_event(it, bad_event)
    assert _count(engine, "itineraries") == 0
    assert _count(engine, "outbox") == 0


def test_relay_publishes_with_properties_and_marks_published(engine):
    repo = PostgresItineraryRepository(DB_URL)
    it = _itinerary()
    repo.save_with_event(it, _event(it))
    channel = MagicMock()

    assert outbox_worker.relay_once(engine, channel) == 1

    kwargs = channel.basic_publish.call_args.kwargs
    assert kwargs["routing_key"] == "itinerary.events" and kwargs["mandatory"] is True
    assert json.loads(kwargs["body"])["itinerary_id"] == it.id
    assert kwargs["properties"].type == "ItineraryCreatedEvent"
    assert kwargs["properties"].delivery_mode == 2
    with engine.connect() as c:
        row = c.execute(text("SELECT status, attempts, published_at FROM outbox")).one()
    assert row.status == "PUBLISHED" and row.attempts == 1 and row.published_at is not None
    assert outbox_worker.relay_once(engine, channel) == 0  # nada pendiente, no republica


def test_broker_failure_keeps_event_pending_for_retry(engine):
    repo = PostgresItineraryRepository(DB_URL)
    it = _itinerary()
    repo.save_with_event(it, _event(it))
    channel = MagicMock()
    channel.basic_publish.side_effect = AMQPConnectionError("broker caido")
    with pytest.raises(AMQPConnectionError):
        outbox_worker.relay_once(engine, channel)
    assert _count(engine, "outbox", "status='PENDING'") == 1

    channel.basic_publish.side_effect = None  # el broker vuelve
    assert outbox_worker.relay_once(engine, channel) == 1
    assert _count(engine, "outbox", "status='PUBLISHED'") == 1


def test_skip_locked_lets_two_relays_work_without_double_publishing(engine):
    repo = PostgresItineraryRepository(DB_URL)
    for _ in range(2):
        it = _itinerary()
        repo.save_with_event(it, _event(it))

    # Relay A mantiene bloqueada la primera fila mientras relay B corre.
    with engine.connect() as holder:
        trans = holder.begin()
        holder.execute(text("SELECT id FROM outbox ORDER BY id LIMIT 1 FOR UPDATE")).one()
        channel_b = MagicMock()
        published = outbox_worker.relay_once(engine, channel_b)
        trans.rollback()
    assert published == 1  # B tomo la fila libre y NO se bloqueo con la de A
    sent = json.loads(channel_b.basic_publish.call_args.kwargs["body"])["itinerary_id"]
    with engine.connect() as c:
        status = {r.id: r.status for r in c.execute(text("SELECT id, status FROM outbox"))}
    assert status == {1: "PENDING", 2: "PUBLISHED"} and sent


def test_unserializable_payload_ends_failed_after_max_attempts(engine):
    with engine.begin() as c:
        c.execute(text("INSERT INTO outbox (aggregate_id, event_type, payload) VALUES (:a, 'X', '{}')"),
                  {"a": str(uuid.uuid4())})
    original = outbox_worker._body
    outbox_worker._body = MagicMock(side_effect=TypeError("no serializable"))
    try:
        outbox_worker.relay_once(engine, MagicMock(), batch_size=outbox_worker.MAX_ATTEMPTS + 2)
    finally:
        outbox_worker._body = original
    with engine.connect() as c:
        row = c.execute(text("SELECT status, attempts, last_error FROM outbox")).one()
    assert row.status == "FAILED" and row.attempts == outbox_worker.MAX_ATTEMPTS and "TypeError" in row.last_error


def test_run_drains_a_backlog_larger_than_one_batch_without_sleeping(engine):
    """Regresion: antes el relay dormia tras cada lote de 20 (~10 eventos/s)."""
    repo = PostgresItineraryRepository(DB_URL)
    for _ in range(45):
        it = _itinerary()
        repo.save_with_event(it, _event(it))
    channel = MagicMock()
    connection = MagicMock()
    waits = []
    connection.process_data_events.side_effect = lambda time_limit: waits.append(time_limit)
    from unittest.mock import patch
    with patch.object(outbox_worker.pika, "BlockingConnection", return_value=connection), \
            patch.object(outbox_worker, "declare_topology"):
        connection.channel.return_value = channel
        outbox_worker.run(DB_URL, "amqp://x", poll_interval_seconds=2.0, stop_after=3)
    assert _count(engine, "outbox", "status='PUBLISHED'") == 45
    assert waits[:2] == [0, 0]  # dos lotes llenos seguidos sin dormir


def test_update_and_delete_write_their_events_atomically(engine):
    repo = PostgresItineraryRepository(DB_URL)
    it = _itinerary()
    repo.save_with_event(it, _event(it))
    it.duration_minutes = 120
    repo.update_with_event(it, DomainEvent("ItineraryUpdatedEvent", it.id, {"itinerary_id": it.id}))
    assert repo.delete_with_event(it.id, "otro", DomainEvent("ItineraryDeletedEvent", it.id, {})) is False
    assert repo.delete_with_event(it.id, "u1", DomainEvent("ItineraryDeletedEvent", it.id, {"itinerary_id": it.id})) is True
    with engine.connect() as c:
        types = [r[0] for r in c.execute(text("SELECT event_type FROM outbox ORDER BY id"))]
    assert types == ["ItineraryCreatedEvent", "ItineraryUpdatedEvent", "ItineraryDeletedEvent"]


def test_update_of_someone_elses_itinerary_writes_no_event(engine):
    repo = PostgresItineraryRepository(DB_URL)
    it = _itinerary("u1")
    repo.save_with_event(it, _event(it))
    it.user_id = "intruso"
    repo.update_with_event(it, DomainEvent("ItineraryUpdatedEvent", it.id, {}))
    assert _count(engine, "outbox") == 1


# --- Agenda del viajero contra PostgreSQL real --------------------------------
import threading  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402

from app.domain.scheduling import ScheduleConflictError, check_schedule  # noqa: E402

VUP = AirportSnapshot("4", "VUP", "Alfonso Lopez", "Valledupar")
TUN = AirportSnapshot("5", "TUN", "Tunja Test", "Tunja")
T0 = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=30)


def _flight(origin, destination, start, minutes=120, user="u1"):
    return Itinerary(nombre_usuario="jhon", origin=origin, destination=destination,
                     departure_at=start, duration_minutes=minutes, user_id=user)


def _save(repo, it, slow=False):
    def check(existing):
        check_schedule(it, existing)
        if slow:
            time.sleep(0.05)     # valida OK y tarda: ensancha la ventana de carrera
    repo.save_with_event(it, _event(it), schedule_check=check)


def test_schedule_rules_enforced_in_db_and_rejected_flight_leaves_no_trace(engine):
    repo = PostgresItineraryRepository(DB_URL)
    _save(repo, _flight(BOG, VUP, T0))                                # 6:00-8:00 (relativo)
    with pytest.raises(ScheduleConflictError) as e:
        _save(repo, _flight(TUN, BOG, T0 + timedelta(hours=1)))       # en pleno vuelo
    assert e.value.code == "OVERLAP"
    with pytest.raises(ScheduleConflictError) as e:
        _save(repo, _flight(TUN, BOG, T0 + timedelta(hours=3)))       # no estas en Tunja
    assert e.value.code == "ORIGIN_MISMATCH"
    _save(repo, _flight(VUP, BOG, T0 + timedelta(hours=2)))           # llegas y sales de inmediato
    assert _count(engine, "itineraries") == 2
    assert _count(engine, "outbox") == 2                              # rechazados: ni fila ni evento


def test_concurrent_conflicting_requests_only_one_wins(engine):
    """Carrera clasica: dos peticiones simultaneas que juntas se traslapan.
    El lock por usuario dentro de la transaccion hace que solo una se guarde."""
    repo = PostgresItineraryRepository(DB_URL)
    attempts = [_flight(BOG, VUP, T0 + timedelta(minutes=m)) for m in range(0, 120, 10)]
    barrier = threading.Barrier(len(attempts))

    def run(it):
        barrier.wait()                       # todos entran en el mismo instante
        try:
            _save(repo, it, slow=True)
            return "ok"
        except ScheduleConflictError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=len(attempts)) as pool:
        results = list(pool.map(run, attempts))
    assert results.count("ok") == 1, results
    assert _count(engine, "itineraries") == 1


def test_departure_at_roundtrip_and_ordering(engine):
    repo = PostgresItineraryRepository(DB_URL)
    later = _flight(VUP, BOG, T0 + timedelta(days=2))
    first = _flight(BOG, VUP, T0)
    _save(repo, first)
    _save(repo, later)
    listed = repo.list_by_user("u1")
    assert [i.id for i in listed] == [first.id, later.id]            # orden por salida
    assert listed[0].departure_at == first.departure_at and listed[0].arrival_at == first.arrival_at


def test_migration_0003_backfills_existing_rows(engine):
    """Una fila 'vieja' (sin departure_at) se migra a las 00:00 de Bogota."""
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.downgrade(cfg, "0002_outbox_delivery_tracking")
    with engine.begin() as c:
        c.execute(text("""INSERT INTO itineraries (id, nombre_usuario, user_id, origin_airport_id, origin_iata,
            origin_name, origin_city, destination_airport_id, destination_iata, destination_name, destination_city,
            travel_date, duration_minutes) VALUES (gen_random_uuid(), 'v', 'old', '1','BOG','a','Bogota','2','MDE','b','Medellin',
            '2026-12-01', 60)"""))
    command.upgrade(cfg, "head")
    with engine.connect() as c:
        dep = c.execute(text("SELECT departure_at FROM itineraries WHERE user_id='old'")).scalar()
    assert dep == datetime(2026, 12, 1, 5, 0, tzinfo=timezone.utc)    # 00:00 UTC-5
