"""Manejo centralizado de errores del dominio.

Los casos de uso lanzan estas excepciones y los controladores las traducen
a mensajes de usuario / respuestas HTTP, sin acoplar la lógica de negocio a Django.
"""
from typing import Dict, List, Optional


class SGAError(Exception):
    """Error base de la aplicación."""

    codigo_http = 400

    def __init__(self, mensaje: str = "", detalles: Optional[Dict[str, List[str]]] = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles or {}

    def __str__(self) -> str:
        return self.mensaje


class ValidacionError(SGAError):
    """Datos de entrada inválidos."""


class RegistroDuplicadoError(ValidacionError):
    """Intento de crear un registro que ya existe (DNI, CUIL, código, etc.)."""


class RegistroNoEncontradoError(SGAError):
    codigo_http = 404


class PermisoDenegadoError(SGAError):
    codigo_http = 403


class MetodoNoPermitidoError(SGAError):
    codigo_http = 405


class ErrorImportacion(SGAError):
    """Falla al importar un archivo (Excel)."""


class ReglaNegocioError(SGAError):
    """Violación de una regla de negocio (ej.: borrar materia con cursadas)."""

