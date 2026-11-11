from fastapi.testclient import TestClient
import jwt

from app.main import app
from app.settings import settings

client = TestClient(app)


def test_issue_token_returns_bearer_jwt_with_sub_and_exp():
    r = client.post("/api/auth/token", json={"username": "jhon"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["expires_in_minutes"] == 60
    claims = jwt.decode(body["access_token"], settings.jwt_secret, algorithms=["HS256"])
    assert claims["sub"] == "jhon" and "exp" in claims


def test_blank_or_missing_username_is_422():
    assert client.post("/api/auth/token", json={"username": ""}).status_code == 422
    assert client.post("/api/auth/token", json={"username": "   "}).status_code == 422
    assert client.post("/api/auth/token", json={}).status_code == 422


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_email_is_optional_and_goes_into_the_token_when_given():
    r = client.post("/api/auth/token", json={"username": "jhon", "email": "jhon@example.com"})
    claims = jwt.decode(r.json()["access_token"], settings.jwt_secret, algorithms=["HS256"])
    assert claims["email"] == "jhon@example.com"
    r = client.post("/api/auth/token", json={"username": "jhon"})
    assert "email" not in jwt.decode(r.json()["access_token"], settings.jwt_secret, algorithms=["HS256"])


def test_invalid_email_is_422():
    for bad in ("no-es-correo", "a@b", "x" * 260 + "@a.com"):
        assert client.post("/api/auth/token", json={"username": "jhon", "email": bad}).status_code == 422
