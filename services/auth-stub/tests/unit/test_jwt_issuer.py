"""Prueba del adapter real (JwtTokenIssuer) con un secreto de prueba.
No usa red ni Redis: pura criptografia, con la misma libreria (python-jose)
que Itinerary Service usa para VALIDAR, cerrando el circulo de confianza."""
from datetime import datetime, timezone

from jose import jwt

from app.domain.models import UsernameClaim
from app.infrastructure.adapters.jwt_issuer import JwtTokenIssuer

TEST_SECRET = "test-secret-not-for-production"


def test_issued_token_is_valid_hs256_and_carries_username_as_sub():
    issuer = JwtTokenIssuer(TEST_SECRET)
    token = issuer.issue(UsernameClaim(username="jhon.ramirez"))

    # Esto es exactamente lo que hace itinerary-service/app/infrastructure/api/security.py
    # al validar: misma libreria, mismo algoritmo, mismo secreto compartido.
    payload = jwt.decode(token, TEST_SECRET, algorithms=["HS256"])

    assert payload["sub"] == "jhon.ramirez"
    assert "exp" in payload


def test_token_signed_with_wrong_secret_fails_validation():
    issuer = JwtTokenIssuer(TEST_SECRET)
    token = issuer.issue(UsernameClaim(username="jhon.ramirez"))

    from jose.exceptions import JWTError
    import pytest
    with pytest.raises(JWTError):
        jwt.decode(token, "otro-secreto-incorrecto", algorithms=["HS256"])
