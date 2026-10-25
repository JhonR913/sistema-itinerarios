from typing import Optional

import httpx
import pybreaker
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

from app.domain.models import AirportSnapshot
from app.domain.ports import AirportGatewayPort

airport_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)


class AirportServiceUnavailableError(ConnectionError):
    pass


class AirportHttpAdapter(AirportGatewayPort):
    def __init__(self, base_url: str, http_client: Optional[httpx.Client] = None):
        self._base_url = base_url
        self._client = http_client or httpx.Client(timeout=3.0)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential_jitter(initial=0.5, max=4))
    def _fetch(self, airport_id: str) -> Optional[dict]:
        response = self._client.get(f"{self._base_url}/api/airports/{airport_id}")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def get_airport_snapshot(self, airport_id: str) -> Optional[AirportSnapshot]:
        try:
            data = airport_breaker.call(self._fetch, airport_id)
        except pybreaker.CircuitBreakerError:
            raise AirportServiceUnavailableError(
                "Airport Service no disponible (circuit breaker abierto)"
            )
        if data is None:
            return None
        return AirportSnapshot(
            airport_id=data["id"], iata_code=data["iata_code"],
            name=data["name"], city=data["city"],
        )
