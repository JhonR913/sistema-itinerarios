from app.domain.models import UsernameClaim
from app.domain.ports import TokenIssuerPort


class IssueToken:
    def __init__(self, issuer: TokenIssuerPort):
        self._issuer = issuer

    def execute(self, username: str) -> str:
        claim = UsernameClaim(username=username)  # valida en __post_init__
        return self._issuer.issue(claim)
