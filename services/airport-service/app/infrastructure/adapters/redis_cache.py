"""Cache Redis. Se serializa en JSON (no pickle): deserializar pickle de un
Redis comprometido permite ejecucion remota de codigo (hotspot de Sonar)."""
import json
from dataclasses import asdict, is_dataclass

import redis

from app.domain.models import Airport
from app.domain.ports import AirportCachePort


def _encode(value) -> str:
    if isinstance(value, list):
        return json.dumps([asdict(v) if is_dataclass(v) else v for v in value])
    raise TypeError("RedisAirportCache solo almacena listas de Airport")


def _decode(raw) -> list:
    return [Airport(**item) for item in json.loads(raw)]


class RedisAirportCache(AirportCachePort):
    def __init__(self, redis_url: str):
        self._client = redis.Redis.from_url(redis_url, socket_timeout=2, socket_connect_timeout=2)

    def get(self, key: str):
        try:
            raw = self._client.get(key)
        except redis.RedisError:
            return None  # Redis caido = cache miss, no error para el usuario
        return _decode(raw) if raw else None

    def set(self, key: str, value, ttl_seconds: int) -> None:
        try:
            self._client.set(key, _encode(value), ex=ttl_seconds)
        except redis.RedisError:
            pass  # sin cache el servicio sigue funcionando


class InMemoryAirportCache(AirportCachePort):
    """Doble de prueba: usado en tests unitarios, sin Redis real."""
    def __init__(self):
        self._store = {}

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key: str, value, ttl_seconds: int) -> None:
        self._store[key] = value
