from typing import Optional

import httpx
import pybreaker
from tenacity import RetryError, retry, stop_after_attempt, wait_exponential_jitter

from app.domain.models import AirportSnapshot
from app.domain.ports import AirportGatewayPort

airport_breaker = pybreaker.CircuitBreaker(fail_max=3, reset_timeout=30)


class AirportServiceUnavailableError(ConnectionError):
    pass


class AirportHttpAdapter(AirportGatewayPort):
    def __init__(self, base_url: str, http_client: Optional[httpx.Client] = None, timeout: float = 2.0):
        self._base_url = base_url
        self._client = http_client or httpx.Client(timeout=timeout)

    # 2 intentos x timeout: la peticion del usuario queda acotada (~2*timeout + espera).
    @retry(stop=stop_after_attempt(2), wait=wait_exponential_jitter(initial=0.3, max=1))
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
        except (httpx.HTTPError, RetryError) as exc:
            # Timeout, conexion rechazada o 5xx tras agotar los reintentos: antes
            # escapaba como RetryError y la API respondia 500 hasta abrir el circuito.
            raise AirportServiceUnavailableError(f"Airport Service no disponible ({type(exc).__name__})") from exc
        if data is None:
            return None
        return AirportSnapshot(
            airport_id=data["id"], iata_code=data["iata_code"],
            name=data["name"], city=data["city"],
        )
