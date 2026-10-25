"""Pruebas unitarias de SendNotificationFunction (RF-012), con psycopg2
reemplazado por un fake: sin Postgres real. Verifican la idempotencia
(at-least-once del broker, falla ya cubierta por la guia de seguridad:
reintentos de RabbitMQ no deben duplicar el historial)."""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import handler  # noqa: E402


class FakeCursor:
    def __init__(self, existing_itinerary_ids):
        self._existing = existing_itinerary_ids
        self.inserted = []
        self._last_check_id = None

    def execute(self, query, params):
        if "SELECT 1" in query:
            self._last_check_id = params[0]
        elif "INSERT INTO notification_history" in query:
            self.inserted.append(params)

    def fetchone(self):
        return (1,) if self._last_check_id in self._existing else None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def close(self):
        pass


def _payload(itinerary_id="abc-123"):
    return json.dumps({
        "itinerary_id": itinerary_id, "nombre_usuario": "jhon",
        "origin": "BOG", "destination": "MDE", "travel_date": "2026-12-01",
    })


def test_handle_inserts_notification_on_first_delivery():
    fake_cursor = FakeCursor(existing_itinerary_ids=set())
    with patch.object(handler.psycopg2, "connect", return_value=FakeConnection(fake_cursor)):
        result = handler.handle(_payload(), context=None)

    assert result["statusCode"] == 200
    assert len(fake_cursor.inserted) == 1


def test_handle_is_idempotent_on_duplicate_delivery():
    """RabbitMQ puede reentregar el mismo mensaje (at-least-once). El
    handler NO debe insertar un segundo registro."""
    fake_cursor = FakeCursor(existing_itinerary_ids={"abc-123"})
    with patch.object(handler.psycopg2, "connect", return_value=FakeConnection(fake_cursor)):
        result = handler.handle(_payload("abc-123"), context=None)

    assert result["body"] == "already processed"
    assert len(fake_cursor.inserted) == 0
