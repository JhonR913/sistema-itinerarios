"""Repositorios PostgreSQL (SQLAlchemy Core, siempre con parametros enlazados)."""
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from app.domain.models import CodeRecord, DomainError, User
from app.domain.ports import CodeRepositoryPort, SessionRepositoryPort, UserRepositoryPort


def make_engine(database_url: str):
    return create_engine(database_url, pool_pre_ping=True, pool_timeout=5,
                         connect_args={"connect_timeout": 3, "options": "-c statement_timeout=5000"})


_SELECT_USER_BY_EMAIL = text("SELECT id::text AS id, email, name, password_hash, verified_at, failed_logins, locked_until "
                             "FROM users WHERE email = :e")
_SELECT_USER_BY_ID = text("SELECT id::text AS id, email, name, password_hash, verified_at, failed_logins, locked_until "
                          "FROM users WHERE id = CAST(:i AS uuid)")


def _user(row) -> User:
    return User(id=row["id"], email=row["email"], name=row["name"], password_hash=row["password_hash"],
                verified_at=row["verified_at"], failed_logins=row["failed_logins"], locked_until=row["locked_until"])


class PostgresUserRepository(UserRepositoryPort):
    def __init__(self, engine):
        self._engine = engine

    def get_by_email(self, email: str) -> Optional[User]:
        with self._engine.connect() as conn:
            row = conn.execute(_SELECT_USER_BY_EMAIL, {"e": email}).mappings().first()
        return _user(row) if row else None

    def get_by_id(self, user_id: str) -> Optional[User]:
        with self._engine.connect() as conn:
            row = conn.execute(_SELECT_USER_BY_ID, {"i": user_id}).mappings().first()
        return _user(row) if row else None

    def create(self, user: User) -> None:
        try:
            with self._engine.begin() as conn:
                conn.execute(text(
                    "INSERT INTO users (id, email, name, password_hash) VALUES (CAST(:i AS uuid), :e, :n, :p)"),
                    {"i": user.id, "e": user.email, "n": user.name, "p": user.password_hash})
        except IntegrityError as exc:  # dos registros simultaneos del mismo correo
            raise DomainError("No pudimos completar el registro. Intenta de nuevo", "CONFLICT") from exc

    def reset_unverified(self, user_id: str, name: str, password_hash: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("UPDATE users SET name = :n, password_hash = :p "
                              "WHERE id = CAST(:i AS uuid) AND verified_at IS NULL"),
                         {"i": user_id, "n": name, "p": password_hash})

    def mark_verified(self, user_id: str, now: datetime) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("UPDATE users SET verified_at = COALESCE(verified_at, :now) WHERE id = CAST(:i AS uuid)"),
                         {"i": user_id, "now": now})

    def set_password(self, user_id: str, password_hash: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("UPDATE users SET password_hash = :p WHERE id = CAST(:i AS uuid)"),
                         {"i": user_id, "p": password_hash})

    def register_failed_login(self, user_id: str, now: datetime, max_failures: int, lock_until: datetime) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("""
                UPDATE users SET
                    locked_until = CASE WHEN failed_logins + 1 >= :mx THEN :lock ELSE locked_until END,
                    failed_logins = CASE WHEN failed_logins + 1 >= :mx THEN 0 ELSE failed_logins + 1 END
                WHERE id = CAST(:i AS uuid)"""), {"i": user_id, "mx": max_failures, "lock": lock_until})

    def clear_failed_logins(self, user_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("UPDATE users SET failed_logins = 0, locked_until = NULL WHERE id = CAST(:i AS uuid)"),
                         {"i": user_id})


class PostgresCodeRepository(CodeRepositoryPort):
    def __init__(self, engine):
        self._engine = engine

    def create(self, user_id: str, purpose: str, code_hash: str, expires_at: datetime, now: datetime) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("UPDATE auth_codes SET consumed_at = :now WHERE user_id = CAST(:u AS uuid) "
                              "AND purpose = :p AND consumed_at IS NULL"), {"u": user_id, "p": purpose, "now": now})
            conn.execute(text("INSERT INTO auth_codes (user_id, purpose, code_hash, expires_at, created_at) "
                              "VALUES (CAST(:u AS uuid), :p, :h, :e, :now)"),
                         {"u": user_id, "p": purpose, "h": code_hash, "e": expires_at, "now": now})

    def latest_active(self, user_id: str, purpose: str, now: datetime) -> Optional[CodeRecord]:
        with self._engine.connect() as conn:
            row = conn.execute(text("""
                SELECT id::text AS id, user_id::text AS user_id, purpose, code_hash, expires_at, attempts
                FROM auth_codes
                WHERE user_id = CAST(:u AS uuid) AND purpose = :p AND consumed_at IS NULL AND expires_at > :now
                ORDER BY created_at DESC LIMIT 1"""), {"u": user_id, "p": purpose, "now": now}).mappings().first()
        if not row:
            return None
        return CodeRecord(row["id"], row["user_id"], row["purpose"], row["code_hash"], row["expires_at"],
                          row["attempts"], False)

    def register_attempt(self, code_id: str, max_attempts: int) -> bool:
        with self._engine.begin() as conn:
            row = conn.execute(text("UPDATE auth_codes SET attempts = attempts + 1 WHERE id = CAST(:i AS uuid) "
                                    "AND consumed_at IS NULL AND attempts < :mx RETURNING id"),
                               {"i": code_id, "mx": max_attempts}).first()
        return row is not None

    def consume(self, code_id: str) -> bool:
        with self._engine.begin() as conn:
            row = conn.execute(text("UPDATE auth_codes SET consumed_at = now() WHERE id = CAST(:i AS uuid) "
                                    "AND consumed_at IS NULL RETURNING id"), {"i": code_id}).first()
        return row is not None

    def count_since(self, since: datetime, user_id: Optional[str] = None, purpose: Optional[str] = None) -> int:
        sql = "SELECT count(*) FROM auth_codes WHERE created_at >= :s"
        params: dict = {"s": since}
        if user_id is not None:
            sql += " AND user_id = CAST(:u AS uuid)"
            params["u"] = user_id
        if purpose is not None:
            sql += " AND purpose = :p"
            params["p"] = purpose
        with self._engine.connect() as conn:
            return int(conn.execute(text(sql), params).scalar_one())

    def last_created_at(self, user_id: str, purpose: str) -> Optional[datetime]:
        with self._engine.connect() as conn:
            return conn.execute(text("SELECT max(created_at) FROM auth_codes "
                                     "WHERE user_id = CAST(:u AS uuid) AND purpose = :p"),
                                {"u": user_id, "p": purpose}).scalar_one()


class PostgresSessionRepository(SessionRepositoryPort):
    def __init__(self, engine):
        self._engine = engine

    def create(self, user_id: str, token_hash: str, expires_at: datetime, now: datetime) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("INSERT INTO auth_sessions (user_id, token_hash, expires_at, created_at) "
                              "VALUES (CAST(:u AS uuid), :h, :e, :now)"),
                         {"u": user_id, "h": token_hash, "e": expires_at, "now": now})
            conn.execute(text("DELETE FROM auth_sessions WHERE expires_at < :now - interval '7 days'"), {"now": now})

    def find_user_id(self, token_hash: str, now: datetime) -> Optional[str]:
        with self._engine.connect() as conn:
            row = conn.execute(text("SELECT user_id::text FROM auth_sessions WHERE token_hash = :h "
                                    "AND revoked_at IS NULL AND expires_at > :now"), {"h": token_hash, "now": now}).first()
        return row[0] if row else None

    def revoke(self, token_hash: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("UPDATE auth_sessions SET revoked_at = now() WHERE token_hash = :h AND revoked_at IS NULL"),
                         {"h": token_hash})

    def revoke_all(self, user_id: str) -> None:
        with self._engine.begin() as conn:
            conn.execute(text("UPDATE auth_sessions SET revoked_at = now() "
                              "WHERE user_id = CAST(:u AS uuid) AND revoked_at IS NULL"), {"u": user_id})
