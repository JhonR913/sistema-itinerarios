"""Idempotencia REAL contra PostgreSQL (se omite sin TEST_DATABASE_URL):
dos entregas concurrentes del mismo evento producen una sola fila."""
import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg2
import pytest
from alembic import command
from alembic.config import Config

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import handler  # noqa: E402

DB_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL no definida")
ROOT = Path(__file__).resolve().parents[2]
CTX = {"type": "ItineraryCreatedEvent", "message_id": 1}


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
    yield


def _msg(itinerary_id):
    return json.dumps({"itinerary_id": itinerary_id, "nombre_usuario": "jhon", "origin": "BOG", "destination": "MDE", "travel_date": "2026-12-01"})


def _rows():
    with psycopg2.connect(DB_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT itinerary_id::text, channel, status FROM notification_history")
        return cur.fetchall()


def test_first_delivery_registers_history_and_duplicate_is_ignored():
    itinerary_id = str(uuid.uuid4())
    assert handler.handle(_msg(itinerary_id), CTX)["body"] == "ok"
    assert handler.handle(_msg(itinerary_id), CTX)["body"] == "already processed"
    assert _rows() == [(itinerary_id, "log-simulado", "SENT")]


def test_concurrent_deliveries_create_exactly_one_row():
    itinerary_id = str(uuid.uuid4())
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: handler.handle(_msg(itinerary_id), CTX)["body"], range(8)))
    assert results.count("ok") == 1 and results.count("already processed") == 7
    assert len(_rows()) == 1


def test_non_uuid_itinerary_id_is_permanent_error():
    with pytest.raises(handler.InvalidMessageError):
        handler.handle(_msg("no-es-uuid"), CTX)
