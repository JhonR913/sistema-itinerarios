"""Dominio minimalista: el Auth stub NO gestiona identidad completa
(ADR documentado: sin registro, sin contraseñas). Solo emite un JWT a
partir de un nombre de usuario (y, opcionalmente, un correo para los
recordatorios), para poder probar la propagacion de identidad
(RF-014, RF-015) sin construir un servicio de identidad real.

OJO: el correo NO se verifica (no hay confirmacion de propiedad): cualquiera
puede declarar el correo de otra persona. Es una limitacion conocida del stub."""
from dataclasses import dataclass
from typing import Optional


def _is_valid_email(value: str) -> bool:
    """usuario@dominio.tld sin espacios. Sin expresion regular a proposito: el
    patron clasico con dos grupos "cualquier cosa menos @ y espacio" separados por
    un punto tiene backtracking super-lineal (ReDoS)."""
    local, at, domain = value.partition("@")
    if not at or not local or "@" in domain or any(c.isspace() for c in value):
        return False
    return "." in domain[1:-1]   # un punto que no sea el primero ni el ultimo del dominio


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
            if len(self.email) > 254 or not _is_valid_email(self.email):
                raise ValueError("El correo no tiene un formato valido")
