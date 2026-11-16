"""Adaptadores criptograficos con la biblioteca estandar (sin dependencias nuevas)."""
import base64
import hashlib
import hmac
import secrets

from app.domain.ports import CodeHasherPort, PasswordHasherPort

# Parametros OWASP para scrypt (N=2^15, r=8, p=3). Van dentro del hash para poder subirlos despues.
_N, _R, _P = 2 ** 15, 8, 3
_MAXMEM = 128 * 1024 * 1024


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=_MAXMEM, dklen=32)


class ScryptPasswordHasher(PasswordHasherPort):
    def __init__(self, n: int = _N, r: int = _R, p: int = _P):
        self._n, self._r, self._p = n, r, p

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = _scrypt(password, salt, self._n, self._r, self._p)
        b64 = lambda raw: base64.b64encode(raw).decode()  # noqa: E731
        return f"scrypt${self._n}${self._r}${self._p}${b64(salt)}${b64(digest)}"

    def verify(self, password: str, stored_hash: str) -> bool:
        try:
            scheme, n, r, p, salt_b64, digest_b64 = stored_hash.split("$")
            if scheme != "scrypt":
                return False
            expected = base64.b64decode(digest_b64)
            actual = _scrypt(password, base64.b64decode(salt_b64), int(n), int(r), int(p))
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(actual, expected)


class HmacCodeHasher(CodeHasherPort):
    """HMAC-SHA256 con clave del servidor: un volcado de la base no permite
    recuperar los codigos con una tabla de 10^6 entradas."""

    def __init__(self, key: str):
        self._key = f"auth-code:{key}".encode()

    def digest(self, user_id: str, purpose: str, code: str) -> str:
        return hmac.new(self._key, f"{user_id}:{purpose}:{code}".encode(), hashlib.sha256).hexdigest()
