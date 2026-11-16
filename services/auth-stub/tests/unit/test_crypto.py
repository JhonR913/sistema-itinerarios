from app.infrastructure.adapters.crypto import HmacCodeHasher, ScryptPasswordHasher


def test_password_roundtrip_with_production_parameters():
    h = ScryptPasswordHasher()
    stored = h.hash("clave-segura-123")
    assert stored.startswith("scrypt$32768$8$3$") and "clave-segura" not in stored
    assert h.verify("clave-segura-123", stored)
    assert not h.verify("otra-clave-123", stored)


def test_same_password_gets_different_salt():
    h = ScryptPasswordHasher(n=2 ** 4, r=1, p=1)
    assert h.hash("clave-segura-123") != h.hash("clave-segura-123")


def test_garbage_hash_never_verifies_nor_raises():
    h = ScryptPasswordHasher(n=2 ** 4, r=1, p=1)
    for bad in ("", "x", "scrypt$a$b$c$d$e", "bcrypt$1$2$3$4$5", "scrypt$16$1$1$!!$!!"):
        assert h.verify("lo-que-sea-123", bad) is False


def test_code_digest_depends_on_user_purpose_code_and_key():
    a = HmacCodeHasher("k1")
    assert a.digest("u1", "verify", "123456") == a.digest("u1", "verify", "123456")
    assert len({a.digest("u1", "verify", "123456"), a.digest("u2", "verify", "123456"),
                a.digest("u1", "reset", "123456"), a.digest("u1", "verify", "123457"),
                HmacCodeHasher("k2").digest("u1", "verify", "123456")}) == 5
    assert "123456" not in a.digest("u1", "verify", "123456")
