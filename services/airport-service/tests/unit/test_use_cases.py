"""Casos de prueba unitaria planeados en Plan_de_Pruebas.docx para
Airport Service: UT-001, UT-002, UT-003. Usan un repositorio fake que
implementa AirportRepositoryPort: sin red, sin Redis real."""
import pytest

from app.domain.models import Airport
from app.domain.ports import AirportRepositoryPort
from app.application.use_cases import ListAirports, GetAirportById


class FakeAirportRepository(AirportRepositoryPort):
    def __init__(self, airports):
        self._airports = airports

    def get_all(self):
        return self._airports

    def get_by_id(self, airport_id):
        return next((a for a in self._airports if a.id == airport_id), None)


@pytest.fixture
def sample_airports():
    return [
        Airport(id="1", external_id="101", iata_code="BOG", name="El Dorado",
                 city="Bogotá", latitude=4.70, longitude=-74.14),
        Airport(id="2", external_id="102", iata_code="MDE", name="José María Córdova",
                 city="Medellín", latitude=6.16, longitude=-75.42),
    ]


def test_UT001_airport_rejects_invalid_iata_code():
    """UT-001: Airport rechaza un codigo IATA vacio o invalido."""
    with pytest.raises(ValueError):
        Airport(id="1", external_id="101", iata_code="", name="X",
                 city="Y", latitude=0.0, longitude=0.0)


def test_UT002_list_airports_returns_all(sample_airports):
    """UT-002: ListAirports retorna todos los aeropuertos del repositorio."""
    repo = FakeAirportRepository(sample_airports)
    result = ListAirports(repo).execute()
    assert len(result) == 2
    assert result[0].iata_code == "BOG"


def test_UT003_get_airport_by_id_not_found(sample_airports):
    """UT-003: GetAirportById retorna None cuando el ID no existe."""
    repo = FakeAirportRepository(sample_airports)
    result = GetAirportById(repo).execute("no-existe")
    assert result is None


def test_extra_get_airport_by_id_found(sample_airports):
    """Prueba adicional (no numerada en el plan): confirma el caso feliz
    de GetAirportById, complementario a UT-003."""
    repo = FakeAirportRepository(sample_airports)
    result = GetAirportById(repo).execute("2")
    assert result is not None
    assert result.city == "Medellín"
