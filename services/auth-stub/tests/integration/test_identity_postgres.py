"""Integracion contra PostgreSQL REAL (se omite si no hay TEST_DATABASE_URL).

    TEST_DATABASE_URL=postgresql://user:pw@localhost/auth_test pytest tests/integration

Aplica la migracion Alembic real y recorre el flujo completo con los repositorios
SQL: registro -> codigo -> verificacion -> sesion -> olvido de contrasena."""
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from app.application.use_cases import IdentityPolicy
from app.domain.models import DomainError, InvalidCode, User
from app.infrastructure.adapters.crypto import HmacCodeHasher, ScryptPasswordHasher
from app.infrastructure.adapters.jwt_issuer import JwtTokenIssuer
from app.infrastructure.adapters.postgres_repository import (
    PostgresCodeRepository, PostgresSessionRepository, PostgresUserRepository, make_engine,
)
from app.infrastructure.api.dependencies import build_container
from tests.fakes import SECRET, FakeClock, RecordingSender

DB_URL = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DB_URL, reason="TEST_DATABASE_URL no definida")
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def engine():
    os.environ["DATABASE_URL"] = DB_URL
    eng = make_engine(DB_URL)
    with eng.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS auth_sessions, auth_codes, users, alembic_version CASCADE"))
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def stack(engine):
    clock, sender = FakeClock(), RecordingSender()
    clock.now = datetime.now(timezone.utc)   # la base compara con now() en algunas consultas
    users, codes, sessions = PostgresUserRepository(engine), PostgresCodeRepository(engine), PostgresSessionRepository(engine)
    policy = IdentityPolicy()
    c = build_container(users, codes, sessions, sender, ScryptPasswordHasher(n=2 ** 4, r=1, p=1),
                        HmacCodeHasher(SECRET), JwtTokenIssuer(SECRET), policy, clock=clock)
    return c, sender, clock, users, codes


def _email():
    return f"u{uuid.uuid4().hex[:10]}@example.com"


def test_migration_is_idempotent_and_reversible(engine):
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(cfg, "head")   # ya aplicada: no falla
    with engine.connect() as conn:
        tables = {r[0] for r in conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public'"))}
    assert {"users", "auth_codes", "auth_sessions"} <= tables


def test_full_flow_against_postgres(stack):
    c, sender, clock, users, _ = stack
    email = _email()
    c.register.execute(email, "Ana", "clave-segura-123")
    assert users.get_by_email(email).verified_at is None
    tokens = c.verify.execute(email, sender.last_code(email))
    assert users.get_by_email(email).is_verified
    assert c.refresh.execute(tokens.session_token).email == email
    assert c.login.execute(email, "clave-segura-123").session_token != tokens.session_token
    c.logout.execute(tokens.session_token)
    with pytest.raises(DomainError):
        c.refresh.execute(tokens.session_token)
    clock.advance(seconds=61)
    c.forgot.execute(email)
    c.reset.execute(email, sender.last_code(email, "reset"), "nueva-clave-segura-9")
    assert c.login.execute(email, "nueva-clave-segura-9")


def test_email_is_unique_even_under_a_race(stack):
    _, _, _, users, _ = stack
    email = _email()
    users.create(User(str(uuid.uuid4()), email, "A", "h"))
    with pytest.raises(DomainError):
        users.create(User(str(uuid.uuid4()), email, "B", "h"))


def test_email_must_be_stored_lowercase(engine):
    with pytest.raises(Exception):
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO users (id,email,name,password_hash) VALUES (:i,'MAYUS@Example.com','x','h')"),
                         {"i": str(uuid.uuid4())})


def test_attempt_counter_is_atomic_under_parallel_guesses(stack):
    """100 hilos adivinando a la vez NO pueden superar el tope de 5 intentos."""
    _, _, _, users, codes = stack
    uid = str(uuid.uuid4())
    users.create(User(uid, _email(), "A", "h"))
    now = datetime.now(timezone.utc)
    codes.create(uid, "verify", "x" * 64, now + timedelta(minutes=10), now)
    rec = codes.latest_active(uid, "verify", now)
    granted, lock = [], threading.Lock()

    def guess():
        ok = codes.register_attempt(rec.id, 5)
        with lock:
            granted.append(ok)

    threads = [threading.Thread(target=guess) for _ in range(100)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert granted.count(True) == 5


def test_code_can_only_be_consumed_once_in_parallel(stack):
    _, _, _, users, codes = stack
    uid = str(uuid.uuid4())
    users.create(User(uid, _email(), "A", "h"))
    now = datetime.now(timezone.utc)
    codes.create(uid, "verify", "y" * 64, now + timedelta(minutes=10), now)
    rec = codes.latest_active(uid, "verify", now)
    results = []
    threads = [threading.Thread(target=lambda: results.append(codes.consume(rec.id))) for _ in range(20)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert results.count(True) == 1


def test_expired_and_consumed_codes_are_not_active(stack):
    _, _, _, users, codes = stack
    uid = str(uuid.uuid4())
    users.create(User(uid, _email(), "A", "h"))
    now = datetime.now(timezone.utc)
    codes.create(uid, "verify", "z" * 64, now - timedelta(seconds=1), now - timedelta(minutes=11))
    assert codes.latest_active(uid, "verify", now) is None


def test_failed_login_lock_in_sql(stack):
    _, _, _, users, _ = stack
    uid, email = str(uuid.uuid4()), _email()
    users.create(User(uid, email, "A", "h"))
    now = datetime.now(timezone.utc)
    for _ in range(5):
        users.register_failed_login(uid, now, 5, now + timedelta(minutes=15))
    u = users.get_by_email(email)
    assert u.locked_until is not None and u.failed_logins == 0
    users.clear_failed_logins(uid)
    assert users.get_by_email(email).locked_until is None


def test_wrong_code_against_postgres_is_invalid(stack):
    c, sender, _, _, _ = stack
    email = _email()
    c.register.execute(email, "Ana", "clave-segura-123")
    real = sender.last_code(email)
    with pytest.raises(InvalidCode):
        c.verify.execute(email, "000000" if real != "000000" else "111111")
