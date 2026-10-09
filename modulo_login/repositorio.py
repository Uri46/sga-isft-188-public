"""Acceso a datos de usuarios (auth.User) y de las personas asociadas a un DNI."""
import re
from typing import Optional

from django.contrib.auth.models import User

from modulo_base_datos.models import Alumno, Docente, Persona


class UsuarioRepositorio:
    # ---- Personas / perfiles ----
    def buscar_persona_por_dni(self, username: str) -> Optional[Persona]:
        dni_candidato = re.sub(r'[^\d]', '', str(username).strip())
        persona = None
        if dni_candidato:
            persona = Persona.objects.filter(dni=dni_candidato).first()
        if not persona:
            persona = Persona.objects.filter(dni=str(username).strip()).first()
        return persona

    def es_alumno(self, persona: Persona) -> bool:
        return Alumno.objects.filter(persona=persona).exists()

    def es_docente(self, persona: Persona) -> bool:
        return Docente.objects.filter(persona=persona).exists()

    def dni_es_docente(self, dni: str) -> bool:
        return Docente.objects.filter(persona__dni=dni).exists()

    def dni_es_alumno(self, dni: str) -> bool:
        return Alumno.objects.filter(persona__dni=dni).exists()

    # ---- Cuentas de usuario ----
    def obtener_usuario(self, username: str) -> Optional[User]:
        return User.objects.filter(username=username).first()

    def crear_usuario_portal(self, persona: Persona, password_hash: str) -> User:
        user = User(
            username=persona.dni,
            first_name=(persona.nombre or '')[:150],
            last_name=(persona.apellido or '')[:150],
            email=(persona.mail or '')[:254],
            is_staff=False,
            is_superuser=False,
            is_active=True,
        )
        user.password = password_hash
        user.save()
        return user

    def actualizar_password(self, user: User, password_hash: str) -> None:
        user.password = password_hash
        user.save()

