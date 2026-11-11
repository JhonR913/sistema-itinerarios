"""RedisAirportCache serializa en JSON (no pickle) y tolera un Redis caido."""
import json

import redis

from app.domain.models import Airport
from app.infrastructure.adapters.redis_cache import RedisAirportCache

AIRPORTS = [Airport(id="1", external_id="1", iata_code="BOG", name="El Dorado",
                    city="Bogotá", latitude=4.7, longitude=-74.1)]


class FakeRedis:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, ex=None):
        self.store[key] = value


class BrokenRedis:
    def get(self, key):
        raise redis.ConnectionError("down")

    def set(self, *a, **k):
        raise redis.ConnectionError("down")


def _cache(client):
    cache = RedisAirportCache.__new__(RedisAirportCache)
    cache._client = client
    return cache


def test_roundtrip_is_plain_json_not_pickle():
    fake = FakeRedis()
    cache = _cache(fake)
    cache.set("k", AIRPORTS, 60)
    assert isinstance(json.loads(fake.store["k"]), list)  # legible como JSON
    assert cache.get("k") == AIRPORTS


def test_miss_returns_none():
    assert _cache(FakeRedis()).get("absent") is None


def test_redis_down_is_a_cache_miss_not_an_error():
    cache = _cache(BrokenRedis())
    assert cache.get("k") is None
    cache.set("k", AIRPORTS, 60)  # no lanza
