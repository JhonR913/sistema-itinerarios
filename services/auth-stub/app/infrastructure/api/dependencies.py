from functools import lru_cache

from app.domain.ports import TokenIssuerPort
from app.infrastructure.adapters.jwt_issuer import JwtTokenIssuer
from app.settings import settings


@lru_cache
def get_token_issuer() -> TokenIssuerPort:
    return JwtTokenIssuer(settings.jwt_secret)
