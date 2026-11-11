"""Pruebas unitarias del handler con psycopg2 reemplazado por un fake (sin
Postgres). Verifican idempotencia, despacho por tipo y rechazo de mensajes
invalidos. La semantica SQL real se prueba en tests/integration."""
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import handler  # noqa: E402

UUID_1 = "6f1c1e5e-6f0f-4c6d-9f3b-2f6d0a1b2c3d"


class FakeCursor:
    def __init__(self, existing_notifications=()):
        self._existing = set(existing_notifications)
        self.executed = []   # (sql, params)
        self.rowcount = -1

    def execute(self, query, params=None):
        self.executed.append((query, params))
        if "INSERT INTO notification_history" in query:
            assert "ON CONFLICT (itinerary_id) DO NOTHING" in query
            if params[0] in self._existing:
                self.rowcount = 0
            else:
                self._existing.add(params[0])
                self.rowcount = 1
        else:
            self.rowcount = 1

    def tables(self, kind):
        return [p for q, p in self.executed if kind in q]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def close(self):
        self.closed = True


@pytest.fixture(autouse=True)
def _db_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")


def _payload(itinerary_id=UUID_1, **overrides):
    data = {"itinerary_id": itinerary_id, "nombre_usuario": "jhon",
            "origin": "BOG", "destination": "MDE", "travel_date": "2026-12-01"}
    data.update(overrides)
    return json.dumps(data)


def _run(raw, context=None, existing=()):
    cursor = FakeCursor(existing)
    conn = FakeConnection(cursor)
    with patch.object(handler.psycopg2, "connect", return_value=conn):
        result = handler.handle(raw, context)
    return result, cursor, conn


def test_created_registers_notification_and_reminder():
    result, cursor, conn = _run(_payload(email="jhon@example.com"), {"type": handler.CREATED, "message_id": "7"})
    assert result == {"statusCode": 200, "body": "ok"}
    assert len(cursor.tables("INSERT INTO notification_history")) == 1
    reminder = cursor.tables("INSERT INTO reminders")[0]
    assert reminder[0] == UUID_1 and reminder[1] == "jhon@example.com" and reminder[-1] == 7
    assert reminder[-2] == "PENDING" or reminder[-2] == "SKIPPED"  # segun la fecha actual
    assert conn.closed


def test_created_without_context_defaults_to_created_for_backward_compatibility():
    result, cursor, _ = _run(_payload())
    assert result["body"] == "ok" and len(cursor.tables("INSERT INTO reminders")) == 1


def test_created_without_email_skips_the_reminder():
    _, cursor, _ = _run(_payload(), {"type": handler.CREATED, "message_id": 1})
    assert cursor.tables("INSERT INTO reminders")[0][1] is None
    assert cursor.tables("INSERT INTO reminders")[0][-2] == "SKIPPED"


def test_invalid_email_is_ignored_not_fatal():
    _, cursor, _ = _run(_payload(email="no es correo\nBcc: x@y.com"), {"type": handler.CREATED, "message_id": 1})
    assert cursor.tables("INSERT INTO reminders")[0][1] is None


def test_duplicate_created_is_reported_and_does_not_duplicate_history():
    result, cursor, _ = _run(_payload(), {"type": handler.CREATED, "message_id": 1}, existing={UUID_1})
    assert result["body"] == "already processed"


def test_same_created_twice_yields_single_notification():
    cursor = FakeCursor()
    with patch.object(handler.psycopg2, "connect", side_effect=lambda *_, **__: FakeConnection(cursor)):
        first = handler.handle(_payload(), {"type": handler.CREATED, "message_id": 1})
        second = handler.handle(_payload(), {"type": handler.CREATED, "message_id": 1})
    assert first["body"] == "ok" and second["body"] == "already processed"


def test_accepts_bytes_as_delivered_by_pika():
    result, _, _ = _run(_payload().encode("utf-8"), {"type": handler.CREATED, "message_id": 1})
    assert result["body"] == "ok"


def test_updated_reschedules_and_deleted_cancels():
    upd = json.dumps({"itinerary_id": UUID_1, "origin": "BOG", "destination": "CTG", "travel_date": "2026-12-09"})
    result, cursor, _ = _run(upd, {"type": handler.UPDATED, "message_id": 9})
    assert result["body"] == "ok" and "UPDATE reminders" in cursor.executed[0][0]
    dele = json.dumps({"itinerary_id": UUID_1})
    result, cursor, _ = _run(dele, {"type": handler.DELETED, "message_id": 10})
    assert "'CANCELLED'" in cursor.executed[0][0] and "email = NULL" in cursor.executed[0][0]


@pytest.mark.parametrize("raw,ctx", [
    ("esto no es json", None),
    ("[]", None),
    ("null", None),
    (json.dumps({"itinerary_id": UUID_1}), None),  # faltan campos
    (_payload(travel_date="31/12/2026"), None),     # fecha invalida
    (_payload(origin="BOGOTA-MUY-LARGO"), None),    # IATA invalido
    (_payload(), {"type": "OtroEvento", "message_id": 1}),                    # tipo desconocido
    (json.dumps({"itinerary_id": UUID_1}), {"type": handler.DELETED}),        # falta message_id
    (json.dumps({"itinerary_id": UUID_1}), {"type": handler.DELETED, "message_id": "abc"}),
])
def test_invalid_messages_raise_invalid_message_error_without_touching_db(raw, ctx):
    with patch.object(handler.psycopg2, "connect") as connect:
        with pytest.raises(handler.InvalidMessageError):
            handler.handle(raw, ctx)
    connect.assert_not_called()
