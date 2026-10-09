"""Matriz de carga por lotes almacenada en la sesión (Paso 1 -> Paso 2 de alumnos y docentes)."""
from typing import Any, Dict, List, Optional


class MatrizSesion:
    """
    Lista de registros pendientes de confirmar, persistida en `request.session`.
    Es compartida por los flujos de registro interactivo (Alumnos y Docentes).
    """

    def __init__(self, session, clave: str, clave_edicion: str):
        self.session = session
        self.clave = clave
        self.clave_edicion = clave_edicion

    def obtener(self) -> List[Dict[str, Any]]:
        data = self.session.get(self.clave, [])
        if isinstance(data, dict):
            return [data] if data else []
        if isinstance(data, list):
            return data
        return []

    def guardar(self, lista: List[Dict[str, Any]]) -> None:
        self.session[self.clave] = lista
        self.session.modified = True

    def duplicado_en_lote(self, campo: str, valor: Any) -> bool:
        return any(item.get(campo) == valor for item in self.obtener())

    def agregar(self, dato: Dict[str, Any]) -> None:
        lista = self.obtener()
        lista.append(dato)
        self.guardar(lista)

    def extraer(self, indice: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Quita un registro (el último si no se indica índice) y lo deja para edición."""
        lista = self.obtener()
        if not lista:
            return None
        if indice is None:
            elegido = lista.pop()
        elif 0 <= indice < len(lista):
            elegido = lista.pop(indice)
        else:
            return None
        self.session[self.clave] = lista
        self.session[self.clave_edicion] = elegido
        self.session.modified = True
        return elegido

    def quitar(self, indice: int) -> Optional[Dict[str, Any]]:
        lista = self.obtener()
        if 0 <= indice < len(lista):
            eliminado = lista.pop(indice)
            self.guardar(lista)
            return eliminado
        return None

    def tomar_edicion(self) -> Optional[Dict[str, Any]]:
        datos = self.session.pop(self.clave_edicion, None)
        if datos:
            self.session.modified = True
        return datos

    def vaciar(self, incluir_edicion: bool = False) -> None:
        self.session.pop(self.clave, None)
        if incluir_edicion:
            self.session.pop(self.clave_edicion, None)
        self.session.modified = True

