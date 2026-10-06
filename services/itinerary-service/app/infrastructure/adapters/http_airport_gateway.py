import logging
from urllib.parse import quote

import httpx

from app.domain.exceptions import AirportServiceUnavailableError
from app.domain.models import AirportSnapshot
from app.domain.ports import AirportGateway

logger = logging.getLogger(__name__)


class HttpAirportGateway(AirportGateway):
    def __init__(self, base_url: str, timeout: float = 3.0, client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)

    def find(self, airport_id: str) -> AirportSnapshot | None:
        url = f"{self._base_url}/airports/{quote(airport_id, safe='')}"
        try:
            response = self._client.get(url)
        except httpx.HTTPError:
            logger.exception("Airport Service no disponible")
            raise AirportServiceUnavailableError()
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            logger.error("Respuesta inesperada de Airport Service: %s", response.status_code)
            raise AirportServiceUnavailableError()
        try:
            data = response.json()
            return AirportSnapshot(
                iata_code=str(data["iata_code"]),
                name=str(data["name"]),
                city=str(data["city"]),
            )
        except (ValueError, KeyError, TypeError):
            logger.error("Respuesta de Airport Service con formato inesperado")
            raise AirportServiceUnavailableError()
