"""Calculo de la hora de recordatorio, zonas horarias y estados iniciales."""
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import mailer  # noqa: E402
import reminders  # noqa: E402


def test_remind_at_is_24h_before_local_midnight_stored_in_utc_bogota():
    # Bogota = UTC-5 (sin horario de verano): 00:00 del 2026-12-01 local = 05:00 UTC.
    # 24 h antes -> 2026-11-30 05:00 UTC.
    r = reminders.compute_remind_at(date(2026, 12, 1), "America/Bogota", 24)
    assert r == datetime(2026, 11, 30, 5, 0, tzinfo=timezone.utc)


def test_timezone_changes_the_instant():
    bog = reminders.compute_remind_at(date(2026, 12, 1), "America/Bogota", 24)
    mad = reminders.compute_remind_at(date(2026, 12, 1), "Europe/Madrid", 24)  # UTC+1 en diciembre
    assert mad == datetime(2026, 11, 29, 23, 0, tzinfo=timezone.utc)
    assert mad < bog


def test_dst_is_respected_for_zones_that_have_it():
    # Nueva York: verano (UTC-4) en julio, invierno (UTC-5) en enero.
    assert reminders.compute_remind_at(date(2026, 7, 10), "America/New_York", 0).hour == 4
    assert reminders.compute_remind_at(date(2026, 1, 10), "America/New_York", 0).hour == 5


def test_lead_hours_is_configurable():
    r = reminders.compute_remind_at(date(2026, 12, 1), "America/Bogota", 48)
    assert r == datetime(2026, 11, 29, 5, 0, tzinfo=timezone.utc)


def test_past_trip_uses_local_date_not_utc_date():
    # 2026-12-02 02:00 UTC = 2026-12-01 21:00 en Bogota -> el 12-01 AUN no es pasado.
    now = datetime(2026, 12, 2, 2, 0, tzinfo=timezone.utc)
    assert reminders.is_past_trip(date(2026, 12, 1), "America/Bogota", now) is False
    assert reminders.is_past_trip(date(2026, 11, 30), "America/Bogota", now) is True


def test_initial_status_rules():
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    assert reminders.initial_status("a@b.co", date(2026, 12, 1), "America/Bogota", now) == "PENDING"
    assert reminders.initial_status(None, date(2026, 12, 1), "America/Bogota", now) == "SKIPPED"
    assert reminders.initial_status("a@b.co", date(2026, 10, 1), "America/Bogota", now) == "SKIPPED"


@pytest.mark.parametrize("bad", [None, "", "sin-arroba", "a@b", "a b@c.com", "x@y.com\nBcc: z@w.com", 5, "a" * 260 + "@b.com",
                                 "a@b.co\n", "a@@b.co", "@b.co", "a@.co", "a@b.", "a" * 65 + "@b.co", "a@b .co"])
def test_valid_email_rejects_garbage_and_header_injection(bad):
    assert reminders.valid_email(bad) is None


@pytest.mark.parametrize("good", ["jhon@example.com", "a@b.co", "primer.apellido+tag@sub.dominio.com.co", "a" * 64 + "@b.co", "a@b..c"])
def test_valid_email_accepts_normal_address(good):
    assert reminders.valid_email(good) == good


def test_valid_email_is_linear_on_pathological_input():
    import time
    t0 = time.perf_counter()
    assert reminders.valid_email("a@" + "." * 50_000 + "!" * 50_000 + " ") is None
    assert time.perf_counter() - t0 < 0.5


def test_reminder_email_content_and_headers():
    msg = mailer.build_reminder("itinerarios@localhost", "jhon@example.com", "Jhon", "BOG", "MDE",
                                date(2026, 12, 1), "abc-123", "America/Bogota")
    assert msg["To"] == "jhon@example.com" and "BOG - MDE" in msg["Subject"]
    assert msg["X-Itinerary-Id"] == "abc-123"
    body = msg.get_content()
    assert "Jhon" in body and "2026-12-01" in body and "America/Bogota" in body


def test_header_injection_in_subject_fields_is_rejected_by_the_library():
    with pytest.raises(ValueError):
        mailer.build_reminder("a@b.co", "x@y.co", "n", "BOG\nBcc: evil@x.com", "MDE", date(2026, 12, 1), "id", "UTC")
