import pickle
from app.domain.ports import AirportCachePort
import redis


class RedisAirportCache(AirportCachePort):
    def __init__(self, redis_url: str):
        self._client = redis.Redis.from_url(redis_url)

    def get(self, key: str):
        raw = self._client.get(key)
        return pickle.loads(raw) if raw else None

    def set(self, key: str, value, ttl_seconds: int) -> None:
        self._client.set(key, pickle.dumps(value), ex=ttl_seconds)


class InMemoryAirportCache(AirportCachePort):
    """Doble de prueba: usado en tests unitarios, sin Redis real."""
    def __init__(self):
        self._store = {}

    def get(self, key: str):
        return self._store.get(key)

    def set(self, key: str, value, ttl_seconds: int) -> None:
        self._store[key] = value
