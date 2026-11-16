"""Dobles en memoria de los puertos (rapidos, sin red ni base de datos)."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.application.use_cases import IdentityPolicy
from app.domain.models import CodeRecord, EmailDeliveryFailed, User
from app.domain.ports import (
    CodeRepositoryPort, EmailSenderPort, SessionRepositoryPort, UserRepositoryPort,
)
from app.infrastructure.adapters.crypto import HmacCodeHasher, ScryptPasswordHasher
from app.infrastructure.adapters.jwt_issuer import JwtTokenIssuer
from app.infrastructure.api.dependencies import build_container

SECRET = "unit-test-secret-not-for-production"


class FakeClock:
    def __init__(self):
        self.now = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kw) -> None:
        self.now += timedelta(**kw)


class MemUsers(UserRepositoryPort):
    def __init__(self):
        self.rows: Dict[str, User] = {}

    def get_by_email(self, email):
        return next((u for u in self.rows.values() if u.email == email), None)

    def get_by_id(self, user_id):
        return self.rows.get(user_id)

    def create(self, user):
        self.rows[user.id] = user

    def _upd(self, user_id, **kw):
        u = self.rows[user_id]
        self.rows[user_id] = User(**{**u.__dict__, **kw})

    def reset_unverified(self, user_id, name, password_hash):
        self._upd(user_id, name=name, password_hash=password_hash)

    def mark_verified(self, user_id, now):
        if not self.rows[user_id].verified_at:
            self._upd(user_id, verified_at=now)

    def set_password(self, user_id, password_hash):
        self._upd(user_id, password_hash=password_hash)

    def register_failed_login(self, user_id, now, max_failures, lock_until):
        u = self.rows[user_id]
        if u.failed_logins + 1 >= max_failures:
            self._upd(user_id, failed_logins=0, locked_until=lock_until)
        else:
            self._upd(user_id, failed_logins=u.failed_logins + 1)

    def clear_failed_logins(self, user_id):
        self._upd(user_id, failed_logins=0, locked_until=None)


class MemCodes(CodeRepositoryPort):
    def __init__(self):
        self.rows: List[dict] = []

    def create(self, user_id, purpose, code_hash, expires_at, now):
        for r in self.rows:
            if r["user_id"] == user_id and r["purpose"] == purpose and not r["consumed"]:
                r["consumed"] = True
        self.rows.append(dict(id=str(uuid.uuid4()), user_id=user_id, purpose=purpose, code_hash=code_hash,
                              expires_at=expires_at, attempts=0, consumed=False, created_at=now))

    def latest_active(self, user_id, purpose, now) -> Optional[CodeRecord]:
        live = [r for r in self.rows if r["user_id"] == user_id and r["purpose"] == purpose
                and not r["consumed"] and r["expires_at"] > now]
        if not live:
            return None
        r = max(live, key=lambda x: x["created_at"])
        return CodeRecord(r["id"], r["user_id"], r["purpose"], r["code_hash"], r["expires_at"], r["attempts"], False)

    def _by_id(self, code_id):
        return next(r for r in self.rows if r["id"] == code_id)

    def register_attempt(self, code_id, max_attempts):
        r = self._by_id(code_id)
        if r["consumed"] or r["attempts"] >= max_attempts:
            return False
        r["attempts"] += 1
        return True

    def consume(self, code_id):
        r = self._by_id(code_id)
        if r["consumed"]:
            return False
        r["consumed"] = True
        return True

    def count_since(self, since, user_id=None, purpose=None):
        return sum(1 for r in self.rows if r["created_at"] >= since
                   and (user_id is None or r["user_id"] == user_id) and (purpose is None or r["purpose"] == purpose))

    def last_created_at(self, user_id, purpose):
        times = [r["created_at"] for r in self.rows if r["user_id"] == user_id and r["purpose"] == purpose]
        return max(times) if times else None


class MemSessions(SessionRepositoryPort):
    def __init__(self):
        self.rows: Dict[str, dict] = {}

    def create(self, user_id, token_hash, expires_at, now):
        self.rows[token_hash] = dict(user_id=user_id, expires_at=expires_at, revoked=False)

    def find_user_id(self, token_hash, now):
        r = self.rows.get(token_hash)
        return r["user_id"] if r and not r["revoked"] and r["expires_at"] > now else None

    def revoke(self, token_hash):
        if token_hash in self.rows:
            self.rows[token_hash]["revoked"] = True

    def revoke_all(self, user_id):
        for r in self.rows.values():
            if r["user_id"] == user_id:
                r["revoked"] = True


class RecordingSender(EmailSenderPort):
    def __init__(self):
        self.codes: List[dict] = []
        self.notices: List[str] = []
        self.fail = False

    def send_code(self, to, name, code, purpose, ttl_minutes):
        if self.fail:
            raise EmailDeliveryFailed()
        self.codes.append(dict(to=to, name=name, code=code, purpose=purpose))

    def send_existing_account_notice(self, to, name):
        if self.fail:
            raise EmailDeliveryFailed()
        self.notices.append(to)

    def last_code(self, to: str, purpose: str = "verify") -> str:
        return [c["code"] for c in self.codes if c["to"] == to and c["purpose"] == purpose][-1]


class World:
    """Todo el sistema de identidad armado con dobles; el reloj es controlable."""

    def __init__(self, policy: Optional[IdentityPolicy] = None):
        self.clock = FakeClock()
        self.users, self.codes, self.sessions = MemUsers(), MemCodes(), MemSessions()
        self.sender = RecordingSender()
        self.policy = policy or IdentityPolicy()
        self.container = build_container(
            self.users, self.codes, self.sessions, self.sender, ScryptPasswordHasher(n=2 ** 4, r=1, p=1),
            HmacCodeHasher(SECRET), JwtTokenIssuer(SECRET, self.policy.access_ttl_minutes), self.policy,
            clock=self.clock)

    def register_verified(self, email="ana@example.com", name="Ana", password="clave-segura-123"):
        self.container.register.execute(email, name, password)
        return self.container.verify.execute(email, self.sender.last_code(email))
