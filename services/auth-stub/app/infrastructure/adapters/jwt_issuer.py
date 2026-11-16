"""Implementa TokenIssuerPort emitiendo JWT HS256. El 'sub' es el id del usuario;
itinerary-service lo lee como user_id (mismo JWT_SECRET, ambos lo validan por
separado -> zero trust). Solo se emite para usuarios con correo VERIFICADO, asi
que el claim `email` es confiable para los recordatorios."""
from datetime import datetime, timedelta, timezone

import jwt

from app.domain.models import User
from app.domain.ports import TokenIssuerPort


class JwtTokenIssuer(TokenIssuerPort):
    def __init__(self, secret: str, ttl_minutes: int = 30):
        self._secret = secret
        self._ttl = ttl_minutes

    def issue(self, user: User) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "iat": now,
            "exp": now + timedelta(minutes=self._ttl),
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")
