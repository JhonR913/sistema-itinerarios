"""Dominio minimalista: el Auth stub NO gestiona identidad completa
(ADR documentado: sin registro, sin contraseñas). Solo emite un JWT a
partir de un nombre de usuario, para poder probar la propagacion de
identidad (RF-014, RF-015) sin construir un servicio de identidad real."""
from dataclasses import dataclass


@dataclass(frozen=True)
class UsernameClaim:
    username: str

    def __post_init__(self):
        if not self.username or not self.username.strip():
            raise ValueError("El nombre de usuario no puede estar vacio")
        if len(self.username) > 120:
            raise ValueError("El nombre de usuario es demasiado largo")
