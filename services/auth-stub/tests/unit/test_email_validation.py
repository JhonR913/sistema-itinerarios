import time

import pytest

from app.domain.models import UsernameClaim


@pytest.mark.parametrize("good", ["jhon@example.com", "a@b.co", "primer.apellido+tag@sub.dominio.com.co"])
def test_accepts_valid_email(good):
    assert UsernameClaim("jhon", good).email == good


@pytest.mark.parametrize("bad", ["sin-arroba", "a@b", "a b@c.com", "a@b.co\n", "a@@b.co", "@b.co", "a@.co", "a@b.", "a" * 255 + "@b.co"])
def test_rejects_invalid_email(bad):
    with pytest.raises(ValueError):
        UsernameClaim("jhon", bad)


def test_validation_is_linear_on_pathological_input():
    t0 = time.perf_counter()
    with pytest.raises(ValueError):
        UsernameClaim("jhon", "a@" + "." * 50_000 + "!" * 50_000 + " ")
    assert time.perf_counter() - t0 < 0.5
