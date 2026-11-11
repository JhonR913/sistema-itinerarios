from typing import Optional

from app.domain.models import UsernameClaim
from app.domain.ports import TokenIssuerPort


class IssueToken:
    def __init__(self, issuer: TokenIssuerPort):
        self._issuer = issuer

    def execute(self, username: str, email: Optional[str] = None) -> str:
        claim = UsernameClaim(username=username, email=email or None)  # valida en __post_init__
        return self._issuer.issue(claim)
