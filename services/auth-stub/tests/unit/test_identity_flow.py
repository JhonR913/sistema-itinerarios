from datetime import timedelta

import jwt
import pytest

from app.application.use_cases import IdentityPolicy, hash_session_token
from app.domain.models import (
    DomainError, EmailDeliveryFailed, EmailNotVerified, InvalidCode, InvalidCredentials, InvalidSession,
    TooManyRequests,
)
from tests.fakes import SECRET, World

EMAIL, PW = "ana@example.com", "clave-segura-123"


def test_register_sends_a_code_and_does_not_log_in():
    w = World()
    w.container.register.execute("  Ana@Example.com ", "Ana", PW)
    assert w.sender.codes[0]["to"] == EMAIL and len(w.sender.codes[0]["code"]) == 6
    assert w.users.get_by_email(EMAIL).verified_at is None
    assert PW not in w.users.get_by_email(EMAIL).password_hash
    with pytest.raises(EmailNotVerified):
        w.container.login.execute(EMAIL, PW)


def test_code_is_stored_hashed_not_in_clear():
    w = World()
    w.container.register.execute(EMAIL, "Ana", PW)
    assert w.sender.last_code(EMAIL) not in w.codes.rows[0]["code_hash"]


def test_verify_marks_user_and_returns_a_session_with_the_expected_claims():
    w = World()
    tokens = w.register_verified()
    claims = jwt.decode(tokens.access_token, SECRET, algorithms=["HS256"])
    user = w.users.get_by_email(EMAIL)
    assert claims["sub"] == user.id and claims["email"] == EMAIL and claims["name"] == "Ana" and "exp" in claims
    assert user.is_verified and tokens.session_token


def test_wrong_code_is_rejected_and_attempts_are_capped():
    w = World()
    w.container.register.execute(EMAIL, "Ana", PW)
    real = w.sender.last_code(EMAIL)
    wrong = "000000" if real != "000000" else "111111"
    for _ in range(5):
        with pytest.raises(InvalidCode):
            w.container.verify.execute(EMAIL, wrong)
    with pytest.raises(InvalidCode):   # el codigo correcto tampoco sirve tras agotar los intentos
        w.container.verify.execute(EMAIL, real)


def test_code_is_single_use():
    w = World()
    w.register_verified()
    with pytest.raises(InvalidCode):
        w.container.verify.execute(EMAIL, w.sender.last_code(EMAIL))


def test_code_expires():
    w = World()
    w.container.register.execute(EMAIL, "Ana", PW)
    w.clock.advance(minutes=11)
    with pytest.raises(InvalidCode):
        w.container.verify.execute(EMAIL, w.sender.last_code(EMAIL))


def test_unknown_email_gets_the_same_error_as_a_wrong_code():
    with pytest.raises(InvalidCode):
        World().container.verify.execute("nadie@example.com", "123456")


def test_registering_an_existing_verified_email_reveals_nothing_and_does_not_change_the_account():
    w = World()
    w.register_verified()
    old_hash = w.users.get_by_email(EMAIL).password_hash
    w.container.register.execute(EMAIL, "Intruso", "otra-clave-muy-larga")
    assert w.users.get_by_email(EMAIL).password_hash == old_hash and w.users.get_by_email(EMAIL).name == "Ana"
    assert w.sender.notices == [EMAIL]
    assert len(w.sender.codes) == 1   # no se envia un segundo codigo


def test_registering_an_existing_email_survives_a_smtp_failure_silently():
    w = World()
    w.register_verified()
    w.sender.fail = True
    w.container.register.execute(EMAIL, "Ana", PW)


def test_reregistering_an_unverified_email_replaces_name_and_password():
    w = World()
    w.container.register.execute(EMAIL, "Intruso", "clave-del-intruso-1")
    w.clock.advance(minutes=2)
    w.container.register.execute(EMAIL, "Ana", PW)
    w.container.verify.execute(EMAIL, w.sender.last_code(EMAIL))
    assert w.users.get_by_email(EMAIL).name == "Ana"
    assert w.container.login.execute(EMAIL, PW)
    with pytest.raises(InvalidCredentials):
        w.container.login.execute(EMAIL, "clave-del-intruso-1")


def test_smtp_failure_on_registration_is_reported():
    w = World()
    w.sender.fail = True
    with pytest.raises(EmailDeliveryFailed):
        w.container.register.execute(EMAIL, "Ana", PW)


def test_invalid_registration_input():
    w = World()
    for args in (("malo", "Ana", PW), (EMAIL, "  ", PW), (EMAIL, "Ana", "corta")):
        with pytest.raises(DomainError):
            w.container.register.execute(*args)
    assert not w.sender.codes


def test_login_ok_after_verification():
    w = World()
    w.register_verified()
    t = w.container.login.execute("ANA@example.com", PW)
    assert t.email == EMAIL and t.session_token


def test_login_failures_are_indistinguishable():
    w = World()
    w.register_verified()
    for email, pw in ((EMAIL, "mala-clave-123456"), ("otro@example.com", PW), ("no-es-correo", PW)):
        with pytest.raises(InvalidCredentials) as e:
            w.container.login.execute(email, pw)
        assert e.value.message == "Correo o contraseña incorrectos"


def test_account_locks_after_repeated_failures_even_with_the_right_password():
    w = World()
    w.register_verified()
    for _ in range(5):
        with pytest.raises(InvalidCredentials):
            w.container.login.execute(EMAIL, "mala-clave-123456")
    with pytest.raises(TooManyRequests):
        w.container.login.execute(EMAIL, PW)
    w.clock.advance(minutes=16)
    assert w.container.login.execute(EMAIL, PW)


def test_successful_login_clears_the_failure_counter():
    w = World()
    w.register_verified()
    for _ in range(4):
        with pytest.raises(InvalidCredentials):
            w.container.login.execute(EMAIL, "mala-clave-123456")
    w.container.login.execute(EMAIL, PW)
    assert w.users.get_by_email(EMAIL).failed_logins == 0


def test_resend_is_throttled_but_always_answers_the_same():
    w = World()
    w.container.register.execute(EMAIL, "Ana", PW)
    w.container.resend.execute(EMAIL)            # dentro de los 60 s: se ignora
    assert len(w.sender.codes) == 1
    w.clock.advance(seconds=61)
    w.container.resend.execute(EMAIL)
    assert len(w.sender.codes) == 2
    w.container.resend.execute("nadie@example.com")   # no existe: no falla ni envia
    assert len(w.sender.codes) == 2


def test_a_new_code_invalidates_the_previous_one():
    w = World()
    w.container.register.execute(EMAIL, "Ana", PW)
    first = w.sender.last_code(EMAIL)
    w.clock.advance(seconds=61)
    w.container.resend.execute(EMAIL)
    second = w.sender.last_code(EMAIL)
    if first != second:
        with pytest.raises(InvalidCode):
            w.container.verify.execute(EMAIL, first)
    assert w.container.verify.execute(EMAIL, second)


def test_hourly_cap_per_user():
    w = World(IdentityPolicy(max_codes_per_hour=3))
    w.container.register.execute(EMAIL, "Ana", PW)
    for _ in range(5):
        w.clock.advance(seconds=61)
        w.container.resend.execute(EMAIL)
    assert len(w.sender.codes) == 3


def test_global_cap_protects_the_smtp_quota():
    w = World(IdentityPolicy(max_codes_per_hour_global=2))
    w.container.register.execute("a@example.com", "A", PW)
    w.container.register.execute("b@example.com", "B", PW)
    with pytest.raises(TooManyRequests):
        w.container.register.execute("c@example.com", "C", PW)
    assert len(w.sender.codes) == 2
    w.clock.advance(hours=1, minutes=1)
    w.container.register.execute("c@example.com", "C", PW)


def test_refresh_returns_new_access_token_for_a_valid_session_only():
    w = World()
    t = w.register_verified()
    r = w.container.refresh.execute(t.session_token)
    assert jwt.decode(r.access_token, SECRET, algorithms=["HS256"])["email"] == EMAIL
    for bad in (None, "", "token-inventado"):
        with pytest.raises(InvalidSession):
            w.container.refresh.execute(bad)


def test_session_expires_and_logout_revokes_it():
    w = World()
    t = w.register_verified()
    w.container.logout.execute(t.session_token)
    with pytest.raises(InvalidSession):
        w.container.refresh.execute(t.session_token)
    t2 = w.container.login.execute(EMAIL, PW)
    w.clock.advance(days=15)
    with pytest.raises(InvalidSession):
        w.container.refresh.execute(t2.session_token)


def test_session_token_is_stored_hashed():
    w = World()
    t = w.register_verified()
    assert t.session_token not in w.sessions.rows and hash_session_token(t.session_token) in w.sessions.rows


def test_forgot_and_reset_password_revokes_sessions_and_old_password():
    w = World()
    t = w.register_verified()
    w.clock.advance(seconds=61)
    w.container.forgot.execute(EMAIL)
    code = w.sender.last_code(EMAIL, "reset")
    w.container.reset.execute(EMAIL, code, "nueva-clave-segura-9")
    with pytest.raises(InvalidSession):
        w.container.refresh.execute(t.session_token)
    with pytest.raises(InvalidCredentials):
        w.container.login.execute(EMAIL, PW)
    assert w.container.login.execute(EMAIL, "nueva-clave-segura-9")


def test_forgot_for_unknown_or_unverified_email_sends_nothing():
    w = World()
    w.container.forgot.execute("nadie@example.com")
    w.container.register.execute(EMAIL, "Ana", PW)
    n = len(w.sender.codes)
    w.container.forgot.execute(EMAIL)
    assert len(w.sender.codes) == n


def test_forgot_swallows_smtp_failures():
    w = World()
    w.register_verified()
    w.clock.advance(seconds=61)
    w.sender.fail = True
    w.container.forgot.execute(EMAIL)


def test_reset_rejects_weak_password_and_a_verify_code():
    w = World()
    w.register_verified()
    w.clock.advance(seconds=61)
    w.container.forgot.execute(EMAIL)
    code = w.sender.last_code(EMAIL, "reset")
    with pytest.raises(DomainError):
        w.container.reset.execute(EMAIL, code, "corta")
    with pytest.raises(InvalidCode):
        w.container.reset.execute("nadie@example.com", code, "nueva-clave-segura-9")


def test_a_verification_code_cannot_be_used_to_reset_a_password():
    w = World()
    w.container.register.execute(EMAIL, "Ana", PW)
    code = w.sender.last_code(EMAIL)
    with pytest.raises(InvalidCode):
        w.container.reset.execute(EMAIL, code, "nueva-clave-segura-9")
