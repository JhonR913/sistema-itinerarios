"""Dominio minimalista: el Auth stub NO gestiona identidad completa
(ADR documentado: sin registro, sin contraseñas). Solo emite un JWT a
partir de un nombre de usuario (y, opcionalmente, un correo para los
recordatorios), para poder probar la propagacion de identidad
(RF-014, RF-015) sin construir un servicio de identidad real.

OJO: el correo NO se verifica (no hay confirmacion de propiedad): cualquiera
puede declarar el correo de otra persona. Es una limitacion conocida del stub."""
import re
from dataclasses import dataclass
from typing import Optional

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class UsernameClaim:
    username: str
    email: Optional[str] = None

    def __post_init__(self):
        if not self.username or not self.username.strip():
            raise ValueError("El nombre de usuario no puede estar vacio")
        if len(self.username) > 120:
            raise ValueError("El nombre de usuario es demasiado largo")
        if self.email is not None:
            if len(self.email) > 254 or not _EMAIL_RE.match(self.email):
                raise ValueError("El correo no tiene un formato valido")
