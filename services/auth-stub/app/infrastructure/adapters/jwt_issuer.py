"""Implementa TokenIssuerPort emitiendo JWT HS256. El 'sub' del token es
el username; Itinerary Service lo lee como user_id (ver
app/infrastructure/api/security.py en itinerary-service: mismo
JWT_SECRET, ambos lo validan de forma independiente -> zero trust)."""
from datetime import datetime, timedelta, timezone

from jose import jwt

from app.domain.models import UsernameClaim
from app.domain.ports import TokenIssuerPort

TOKEN_TTL_MINUTES = 60


class JwtTokenIssuer(TokenIssuerPort):
    def __init__(self, secret: str):
        self._secret = secret

    def issue(self, claim: UsernameClaim) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": claim.username,
            "iat": now,
            "exp": now + timedelta(minutes=TOKEN_TTL_MINUTES),
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")
