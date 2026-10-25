from abc import ABC, abstractmethod
from .models import UsernameClaim


class TokenIssuerPort(ABC):
    """Puerto: quien implemente esto decide el algoritmo y el secreto.
    El dominio no sabe que es JWT ni HS256."""

    @abstractmethod
    def issue(self, claim: UsernameClaim) -> str:
        ...
