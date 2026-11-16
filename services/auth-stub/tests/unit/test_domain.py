import pytest

from app.domain.models import DomainError, InvalidCode, is_valid_email, normalize_email, validate_code_format, \
    validate_name, validate_password


@pytest.mark.parametrize("ok", ["a@b.co", "jhon@example.com", "x.y+z@sub.dominio.org"])
def test_valid_emails(ok):
    assert is_valid_email(ok)


@pytest.mark.parametrize("bad", ["", "no-es-correo", "a@b", "a@.com", "a@b.", "@b.com", "a b@c.com", "a@@b.com"])
def test_invalid_emails(bad):
    assert not is_valid_email(bad)


def test_email_is_normalized_and_length_limited():
    assert normalize_email("  Ana@Example.COM ") == "ana@example.com"
    with pytest.raises(DomainError):
        normalize_email("x" * 260 + "@a.com")


def test_pathological_email_is_linear_time():
    import time
    t = time.perf_counter()
    is_valid_email("a" * 50000 + "@" + "." * 50000)
    assert time.perf_counter() - t < 0.5


def test_name_rules():
    assert validate_name("  Ana   Maria ") == "Ana Maria"
    for bad in ("", "   ", "x" * 121):
        with pytest.raises(DomainError):
            validate_name(bad)


@pytest.mark.parametrize("bad", ["corta", "a" * 129, "aaaaaaaaaaaa", "          ", "ana@example.com"])
def test_weak_passwords_are_rejected(bad):
    with pytest.raises(DomainError) as e:
        validate_password(bad, "ana@example.com")
    assert e.value.code == "WEAK_PASSWORD"


def test_good_password_passes():
    validate_password("clave-segura-123", "ana@example.com")


@pytest.mark.parametrize("bad", ["12345", "1234567", "abcdef", "12 456", ""])
def test_code_format(bad):
    with pytest.raises(InvalidCode):
        validate_code_format(bad)


def test_code_format_ok():
    assert validate_code_format(" 012345 ") == "012345"
