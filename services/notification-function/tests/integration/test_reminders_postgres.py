"""Recordatorios contra PostgreSQL real + SMTP real (sumidero aiosmtpd).
Se omite sin TEST_DATABASE_URL."""
import json
import os
import socket
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import psycopg2
import pytest
from aiosmtpd.controller import Controller
from alembic import command
from alembic.config import Config

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import handler  # noqa: E402
import mailer  # noqa: E402
import reminder_worker  # noqa: E402

DB_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL no definida")
ROOT = Path(__file__).resolve().parents[2]
TOMORROW = (datetime.now(timezone.utc) + timedelta(days=1)).date()
NEXT_MONTH = (datetime.now(timezone.utc) + timedelta(days=30)).date()


@pytest.fixture(scope="module", autouse=True)
def migrated():
    os.environ["DATABASE_URL"] = DB_URL
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(cfg, "head")


@pytest.fixture(autouse=True)
def clean():
    with psycopg2.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute("TRUNCATE notification_history, reminders RESTART IDENTITY")


class Sink:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):  # noqa: N802 - API de aiosmtpd
        self.messages.append(envelope)
        return "250 OK"


@pytest.fixture
def smtp(monkeypatch):
    sink = Sink()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    controller = Controller(sink, hostname="127.0.0.1", port=port)
    controller.start()
    monkeypatch.setenv("SMTP_HOST", "127.0.0.1")
    monkeypatch.setenv("SMTP_PORT", str(port))
    yield sink
    controller.stop()


def _created(itinerary_id, event_id, travel_date=TOMORROW, email="jhon@example.com"):
    payload = {"itinerary_id": itinerary_id, "nombre_usuario": "Jhon", "origin": "BOG",
               "destination": "MDE", "travel_date": travel_date.isoformat()}
    if email:
        payload["email"] = email
    handler.handle(json.dumps(payload), {"type": handler.CREATED, "message_id": event_id})


def _updated(itinerary_id, event_id, travel_date, destination="CTG"):
    return handler.handle(json.dumps({"itinerary_id": itinerary_id, "origin": "BOG", "destination": destination,
                                      "travel_date": travel_date.isoformat()}),
                          {"type": handler.UPDATED, "message_id": event_id})


def _deleted(itinerary_id, event_id):
    handler.handle(json.dumps({"itinerary_id": itinerary_id}), {"type": handler.DELETED, "message_id": event_id})


def _row(itinerary_id):
    with psycopg2.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT status, email, nombre_usuario, destination, travel_date, attempts, last_event_id "
                    "FROM reminders WHERE itinerary_id = %s", (itinerary_id,))
        return cur.fetchone()


def _send_due():
    return reminder_worker.send_due(DB_URL)


def test_due_reminder_is_sent_once_by_real_smtp_and_marked_sent(smtp):
    i = str(uuid.uuid4())
    _created(i, 1)  # viaje manana + 24 h de antelacion = ya vencido
    assert _send_due() == 1
    assert _send_due() == 0  # no se reenvia
    assert len(smtp.messages) == 1
    env = smtp.messages[0]
    assert env.rcpt_tos == ["jhon@example.com"]
    assert b"BOG - MDE" in env.content and i.encode() in env.content
    assert _row(i)[0] == "SENT"


def test_future_reminder_is_not_sent_yet(smtp):
    i = str(uuid.uuid4())
    _created(i, 1, travel_date=NEXT_MONTH)
    assert _row(i)[0] == "PENDING" and _send_due() == 0 and smtp.messages == []


def test_no_email_means_skipped_and_nothing_is_sent(smtp):
    i = str(uuid.uuid4())
    _created(i, 1, email=None)
    assert _row(i)[0] == "SKIPPED" and _send_due() == 0 and smtp.messages == []


def test_past_trip_is_skipped(smtp):
    i = str(uuid.uuid4())
    _created(i, 1, travel_date=date(2020, 1, 1))
    assert _row(i)[0] == "SKIPPED" and _send_due() == 0


def test_duplicate_created_event_does_not_duplicate_reminder_or_email(smtp):
    i = str(uuid.uuid4())
    _created(i, 1)
    _created(i, 1)
    _send_due()
    _send_due()
    assert len(smtp.messages) == 1


def test_delete_cancels_and_erases_personal_data(smtp):
    i = str(uuid.uuid4())
    _created(i, 1)
    _deleted(i, 2)
    status, email, nombre, *_ = _row(i)
    assert (status, email, nombre) == ("CANCELLED", None, None)
    assert _send_due() == 0 and smtp.messages == []


def test_late_created_cannot_resurrect_a_deleted_itinerary(smtp):
    """Deleted (id 5) llega ANTES que el Created (id 3): queda la lapida."""
    i = str(uuid.uuid4())
    _deleted(i, 5)
    _created(i, 3)
    assert _row(i)[0] == "CANCELLED" and _send_due() == 0


def test_update_reschedules_and_stale_update_is_ignored(smtp):
    i = str(uuid.uuid4())
    _created(i, 1, travel_date=NEXT_MONTH)
    assert _send_due() == 0
    assert _updated(i, 4, TOMORROW)["body"] == "ok"          # adelantar el viaje: vence ya
    assert _updated(i, 3, NEXT_MONTH)["body"].startswith("ignored")  # evento viejo (id menor): se ignora
    assert _row(i)[3] == "CTG" and _row(i)[4] == TOMORROW
    assert _send_due() == 1


def test_update_after_sent_resends_with_new_data(smtp):
    i = str(uuid.uuid4())
    _created(i, 1)
    _send_due()
    _updated(i, 2, TOMORROW, destination="CLO")
    assert _row(i)[0] == "PENDING"
    assert _send_due() == 1
    assert len(smtp.messages) == 2 and b"BOG - CLO" in smtp.messages[1].content


def test_update_of_cancelled_itinerary_stays_cancelled(smtp):
    i = str(uuid.uuid4())
    _created(i, 1)
    _deleted(i, 2)
    _updated(i, 3, TOMORROW)
    assert _row(i)[0] == "CANCELLED"


def test_smtp_failure_retries_then_ends_failed_without_losing_the_row():
    i = str(uuid.uuid4())
    _created(i, 1)

    def broken(_msg):
        raise ConnectionRefusedError("smtp caido")

    for _ in range(reminder_worker.MAX_ATTEMPTS):
        assert reminder_worker.send_due(DB_URL, send=broken) == 0
    status, *_rest, attempts, _ = _row(i)
    assert status == "FAILED" and attempts == reminder_worker.MAX_ATTEMPTS


def test_smtp_recovers_after_a_failure(smtp):
    i = str(uuid.uuid4())
    _created(i, 1)
    assert reminder_worker.send_due(DB_URL, send=lambda m: (_ for _ in ()).throw(OSError("x"))) == 0
    assert _row(i)[0] == "PENDING"
    assert _send_due() == 1 and _row(i)[0] == "SENT"


def test_concurrent_workers_send_each_reminder_once(smtp):
    from concurrent.futures import ThreadPoolExecutor
    for n in range(6):
        _created(str(uuid.uuid4()), n + 1)
    with ThreadPoolExecutor(max_workers=4) as pool:
        counts = list(pool.map(lambda _: _send_due(), range(4)))
    assert sum(counts) == 6 and len(smtp.messages) == 6


# --- Recordatorio relativo a la hora real de salida ----------------------------
def _created_with_time(itinerary_id, event_id, departure, minutes=120):
    payload = {"itinerary_id": itinerary_id, "nombre_usuario": "Jhon", "origin": "BOG", "destination": "VUP",
               "origin_city": "Bogotá", "destination_city": "Valledupar",
               "travel_date": departure.astimezone(timezone(timedelta(hours=-5))).date().isoformat(),
               "departure_at": departure.isoformat(),
               "arrival_at": (departure + timedelta(minutes=minutes)).isoformat(),
               "email": "jhon@example.com"}
    handler.handle(json.dumps(payload), {"type": handler.CREATED, "message_id": event_id})


def _state(itinerary_id):
    with psycopg2.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT status, remind_at, departure_at FROM reminders WHERE itinerary_id=%s", (itinerary_id,))
        return cur.fetchone()


def test_reminder_is_scheduled_24h_before_the_real_departure_time():
    itin = str(uuid.uuid4())
    dep = (datetime.now(timezone.utc) + timedelta(days=10)).replace(hour=11, minute=0, second=0, microsecond=0)
    _created_with_time(itin, 1, dep)
    status, remind_at, stored_dep = _state(itin)
    assert status == "PENDING"
    assert stored_dep == dep
    assert remind_at == dep - timedelta(hours=24)


def test_flight_within_24h_sends_the_alert_right_away_with_time_and_arrival(smtp):
    itin = str(uuid.uuid4())
    dep = (datetime.now(timezone.utc) + timedelta(hours=10)).replace(second=0, microsecond=0)
    _created_with_time(itin, 1, dep)
    assert reminder_worker.send_due(DB_URL) == 1             # remind_at ya vencido -> sale ya
    assert _state(itin)[0] == "SENT"
    body = smtp.messages[0].content.decode()
    local = dep.astimezone(timezone(timedelta(hours=-5)))
    assert "Bogotá (BOG)" in body and "Valledupar (VUP)" in body
    assert f"{local:%H:%M}" in body and "Llegada estimada" in body


def test_already_departed_flight_is_skipped_not_emailed(smtp):
    itin = str(uuid.uuid4())
    _created_with_time(itin, 1, datetime.now(timezone.utc) - timedelta(hours=1))
    assert _state(itin)[0] == "SKIPPED"
    assert reminder_worker.send_due(DB_URL) == 0 and smtp.messages == []


def test_updating_the_departure_time_reschedules_the_reminder():
    itin = str(uuid.uuid4())
    dep = (datetime.now(timezone.utc) + timedelta(days=10)).replace(minute=0, second=0, microsecond=0)
    _created_with_time(itin, 1, dep)
    new_dep = dep + timedelta(days=2, hours=3)
    handler.handle(json.dumps({"itinerary_id": itin, "origin": "BOG", "destination": "VUP",
                               "travel_date": new_dep.date().isoformat(), "departure_at": new_dep.isoformat(),
                               "arrival_at": (new_dep + timedelta(hours=2)).isoformat()}),
                   {"type": handler.UPDATED, "message_id": 2})
    status, remind_at, stored_dep = _state(itin)
    assert status == "PENDING" and stored_dep == new_dep and remind_at == new_dep - timedelta(hours=24)


def test_malformed_departure_goes_to_dlq_not_retried():
    with pytest.raises(handler.InvalidMessageError):
        handler.handle(json.dumps({"itinerary_id": str(uuid.uuid4()), "nombre_usuario": "x", "origin": "BOG",
                                   "destination": "MDE", "travel_date": "2026-12-01",
                                   "departure_at": "2026-12-01T06:00:00"}),   # sin zona
                       {"type": handler.CREATED, "message_id": 1})
