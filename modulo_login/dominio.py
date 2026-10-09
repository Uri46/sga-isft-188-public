"""Entidades del dominio de autenticación."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional

PASSWORD_PORTAL_POR_DEFECTO = '123456789'


class Rol(str, Enum):
    DIRECTIVO = 'directivo'   # is_staff / is_superuser
    DOCENTE = 'docente'
    ALUMNO = 'alumno'
    SIN_ROL = 'sin_rol'


@dataclass(frozen=True)
class Usuario:
    """Vista de dominio de un usuario autenticable (independiente del modelo ORM)."""
    username: str
    rol: Rol
    es_staff: bool = False
    es_superusuario: bool = False
    nombre: Optional[str] = None
    apellido: Optional[str] = None

    @property
    def es_directivo(self) -> bool:
        return self.es_staff or self.es_superusuario

