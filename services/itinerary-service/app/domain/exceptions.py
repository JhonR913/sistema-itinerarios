class DomainError(Exception):
    """Base de errores de negocio."""


class SameAirportError(DomainError):
    pass


class InvalidItineraryError(DomainError):
    pass


class AirportNotFoundError(DomainError):
    pass


class ItineraryNotFoundError(DomainError):
    pass


class AirportServiceUnavailableError(DomainError):
    pass
