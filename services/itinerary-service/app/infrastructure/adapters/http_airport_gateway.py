import logging
from urllib.parse import quote

import httpx

from app.domain.exceptions import AirportServiceUnavailableError
from app.domain.ports import AirportGateway

logger = logging.getLogger(__name__)


class HttpAirportGateway(AirportGateway):
    def __init__(self, base_url: str, timeout: float = 3.0, client: httpx.Client | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=timeout)

    def exists(self, airport_id: str) -> bool:
        url = f"{self._base_url}/airports/{quote(airport_id, safe='')}"
        try:
            response = self._client.get(url)
        except httpx.HTTPError:
            logger.exception("Airport Service no disponible")
            raise AirportServiceUnavailableError()
        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False
        logger.error("Respuesta inesperada de Airport Service: %s", response.status_code)
        raise AirportServiceUnavailableError()
