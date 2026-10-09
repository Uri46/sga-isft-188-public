from typing import Optional

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.http import HttpRequest

from .casos_uso import ServicioAutenticacion


class DNIAuthBackend(ModelBackend):
    """
    Backend de autenticación que permite a Alumnos y Docentes ingresar
    utilizando su número de DNI como identificador y su contraseña (inicialmente 123456789).
    Si se trata de un usuario administrativo tradicional (ej. admin), delega a ModelBackend.
    """

    def authenticate(self, request: Optional[HttpRequest], username: Optional[str] = None,
                     password: Optional[str] = None, **kwargs) -> Optional[User]:
        user = ServicioAutenticacion().autenticar_por_dni(username, password, self.user_can_authenticate)
        if user:
            return user
        # Autenticación con credenciales del sistema (ej. administradores o directivos)
        return super().authenticate(request, username=username, password=password, **kwargs)

