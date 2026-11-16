"""Contrato HTTP con dobles en memoria: codigos de estado, cookie de sesion y
ausencia de enumeracion de cuentas."""
import jwt
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.api.dependencies import get_container
from app.infrastructure.api.routes import SESSION_COOKIE
from app.main import app
from tests.fakes import SECRET, World

EMAIL, PW = "ana@example.com", "clave-segura-123"


@pytest.fixture
def world():
    w = World()
    app.dependency_overrides[get_container] = lambda: w.container
    yield w
    app.dependency_overrides.clear()


@pytest.fixture
def client(world):
    return TestClient(app, base_url="https://testserver")


def _register(client, world, email=EMAIL):
    r = client.post("/api/auth/register", json={"email": email, "name": "Ana", "password": PW})
    assert r.status_code == 202
    return world.sender.last_code(email)


def test_health():
    assert TestClient(app).get("/health").json() == {"status": "ok"}


def test_full_flow_register_verify_refresh_logout(client, world):
    code = _register(client, world)
    r = client.post("/api/auth/verify", json={"email": EMAIL, "code": code})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer" and body["email"] == EMAIL and body["name"] == "Ana"
    assert jwt.decode(body["access_token"], SECRET, algorithms=["HS256"])["email"] == EMAIL
    assert r.headers["cache-control"] == "no-store"
    set_cookie = r.headers["set-cookie"].lower()
    assert SESSION_COOKIE in set_cookie and "httponly" in set_cookie and "samesite=strict" in set_cookie
    assert "path=/api/auth" in set_cookie

    assert client.post("/api/auth/refresh").status_code == 200     # el cliente reenvia la cookie
    assert client.post("/api/auth/logout").status_code == 204
    assert client.post("/api/auth/refresh").status_code == 401


def test_refresh_without_cookie_is_401(client):
    r = client.post("/api/auth/refresh")
    assert r.status_code == 401 and r.json()["code"] == "INVALID_SESSION"


def test_login_before_verification_is_403_with_code(client, world):
    _register(client, world)
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PW})
    assert r.status_code == 403 and r.json()["code"] == "EMAIL_NOT_VERIFIED"


def test_login_wrong_password_is_401_and_sets_no_cookie(client, world):
    world.register_verified()
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": "mala-clave-123456"})
    assert r.status_code == 401 and "set-cookie" not in r.headers


def test_login_ok(client, world):
    world.register_verified()
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PW})
    assert r.status_code == 200 and SESSION_COOKIE in r.headers["set-cookie"]


def test_registration_responses_do_not_reveal_existing_accounts(client, world):
    world.register_verified()
    existing = client.post("/api/auth/register", json={"email": EMAIL, "name": "X", "password": PW})
    fresh = client.post("/api/auth/register", json={"email": "otra@example.com", "name": "X", "password": PW})
    assert existing.status_code == fresh.status_code == 202 and existing.json() == fresh.json()
    a = client.post("/api/auth/resend", json={"email": EMAIL})
    b = client.post("/api/auth/resend", json={"email": "nadie@example.com"})
    c = client.post("/api/auth/forgot", json={"email": "nadie@example.com"})
    assert a.status_code == b.status_code == c.status_code == 202 and a.json() == b.json() == c.json()


def test_validation_errors_do_not_leak_details(client):
    r = client.post("/api/auth/register", json={"email": "malo", "name": "Ana", "password": PW})
    assert r.status_code == 422 and r.json()["code"] == "INVALID_EMAIL"
    r = client.post("/api/auth/register", json={"email": EMAIL, "name": "Ana", "password": "corta"})
    assert r.json()["code"] == "WEAK_PASSWORD"
    assert client.post("/api/auth/register", json={}).status_code == 422
    assert client.post("/api/auth/register", json={"email": EMAIL, "name": "A", "password": "x" * 500}).status_code == 422


def test_bad_code_is_400(client, world):
    _register(client, world)
    r = client.post("/api/auth/verify", json={"email": EMAIL, "code": "abc"})
    assert r.status_code == 400 and r.json()["code"] == "INVALID_CODE"


def test_smtp_down_is_503_without_internals(client, world):
    world.sender.fail = True
    r = client.post("/api/auth/register", json={"email": EMAIL, "name": "Ana", "password": PW})
    assert r.status_code == 503 and r.json()["code"] == "EMAIL_DELIVERY_FAILED"


def test_account_lock_is_429(client, world):
    world.register_verified()
    for _ in range(5):
        client.post("/api/auth/login", json={"email": EMAIL, "password": "mala-clave-123456"})
    r = client.post("/api/auth/login", json={"email": EMAIL, "password": PW})
    assert r.status_code == 429 and r.json()["code"] == "TOO_MANY_REQUESTS"


def test_reset_flow_over_http(client, world):
    world.register_verified()
    world.clock.advance(seconds=61)
    assert client.post("/api/auth/forgot", json={"email": EMAIL}).status_code == 202
    code = world.sender.last_code(EMAIL, "reset")
    r = client.post("/api/auth/reset", json={"email": EMAIL, "code": code, "password": "nueva-clave-segura-9"})
    assert r.status_code == 204
    assert client.post("/api/auth/login", json={"email": EMAIL, "password": "nueva-clave-segura-9"}).status_code == 200


def test_the_old_unauthenticated_token_endpoint_is_gone(client):
    assert client.post("/api/auth/token", json={"username": "x"}).status_code in (404, 405)
