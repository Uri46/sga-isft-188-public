"""Reglas de negocio de autenticación: hash PBKDF2, aprovisionamiento por DNI y roles."""
from typing import Optional

from django.contrib.auth.hashers import check_password, is_password_usable, make_password

from .dominio import PASSWORD_PORTAL_POR_DEFECTO, Rol, Usuario
from .repositorio import UsuarioRepositorio


# ---- Hash de contraseñas (PBKDF2-SHA256, el hasher por defecto de Django) ----
def generar_hash_pbkdf2(password: str) -> str:
    return make_password(password, hasher='pbkdf2_sha256')


def verificar_hash(password: str, hash_guardado: str) -> bool:
    return check_password(password, hash_guardado)


class ServicioAutenticacion:
    def __init__(self, repositorio: Optional[UsuarioRepositorio] = None):
        self.repositorio = repositorio or UsuarioRepositorio()

    def autenticar_por_dni(self, username: Optional[str], password: Optional[str], user_can_authenticate):
        """
        Autentica a Alumnos/Docentes usando el DNI como usuario (clave inicial 123456789).
        Devuelve el `User` o None si no corresponde (el backend delega entonces en ModelBackend).
        """
        if not username or not password:
            return None

        persona = self.repositorio.buscar_persona_por_dni(username)
        if not persona:
            return None
        if not (self.repositorio.es_alumno(persona) or self.repositorio.es_docente(persona)):
            return None

        user = self.repositorio.obtener_usuario(persona.dni)
        if not user:
            user = self.repositorio.crear_usuario_portal(persona, generar_hash_pbkdf2(PASSWORD_PORTAL_POR_DEFECTO))
        elif not user.has_usable_password():
            self.repositorio.actualizar_password(user, generar_hash_pbkdf2(PASSWORD_PORTAL_POR_DEFECTO))

        if verificar_hash(password, user.password) and user_can_authenticate(user):
            return user
        return None

    def rol_de(self, user) -> Rol:
        if user.is_superuser or user.is_staff:
            return Rol.DIRECTIVO
        dni = str(user.username).strip()
        if self.repositorio.dni_es_docente(dni):
            return Rol.DOCENTE
        if self.repositorio.dni_es_alumno(dni):
            return Rol.ALUMNO
        return Rol.SIN_ROL

    def usuario_de_dominio(self, user) -> Usuario:
        return Usuario(
            username=str(user.username),
            rol=self.rol_de(user),
            es_staff=user.is_staff,
            es_superusuario=user.is_superuser,
            nombre=user.first_name or None,
            apellido=user.last_name or None,
        )

    @staticmethod
    def ruta_inicial(rol: Rol) -> str:
        """Nombre de URL (namespaced) a la que se redirige tras iniciar sesión."""
        if rol == Rol.DOCENTE:
            return 'portal:docente'
        if rol == Rol.ALUMNO:
            return 'portal:alumno'
        return 'gestion:buscador'

