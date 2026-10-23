"""RF-014. El Auth stub NO gestiona contraseñas ni sesiones: solo valida
que el username no este vacio y emite el JWT."""
import pytest
from jose import jwt

from app.domain.models import UsernameClaim
from app.domain.ports import TokenIssuerPort
from app.application.use_cases import IssueToken


class FakeIssuer(TokenIssuerPort):
    def __init__(self):
        self.issued_claims = []

    def issue(self, claim):
        self.issued_claims.append(claim)
        return f"fake-token-for-{claim.username}"


def test_issue_token_happy_path():
    issuer = FakeIssuer()
    token = IssueToken(issuer).execute("jhon.ramirez")
    assert token == "fake-token-for-jhon.ramirez"
    assert issuer.issued_claims[0].username == "jhon.ramirez"


def test_issue_token_rejects_empty_username():
    issuer = FakeIssuer()
    with pytest.raises(ValueError):
        IssueToken(issuer).execute("   ")
    assert len(issuer.issued_claims) == 0


def test_username_claim_rejects_overly_long_username():
    with pytest.raises(ValueError):
        UsernameClaim(username="x" * 200)
