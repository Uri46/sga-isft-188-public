from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from .dominio import Rol
from .casos_uso import ServicioAutenticacion


def _rol(request) -> Rol:
    return ServicioAutenticacion().rol_de(request.user)


def directivo_requerido(view_func):
    """
    Permite acceso únicamente a directivos / personal administrativo (is_staff o is_superuser).
    Si un docente o alumno intenta acceder, es redirigido a su respectivo portal.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login:login')}?next={request.path}")

        rol = _rol(request)
        if rol == Rol.DIRECTIVO:
            return view_func(request, *args, **kwargs)
        if rol == Rol.DOCENTE:
            messages.warning(request, "Acceso restringido. Has sido redirigido a tu portal docente.")
            return redirect('portal:docente')
        if rol == Rol.ALUMNO:
            messages.warning(request, "Acceso restringido. Has sido redirigido a tu portal de estudiante.")
            return redirect('portal:alumno')

        messages.error(request, "No posees permisos de directivo para acceder a este módulo.")
        return redirect('login:login')

    return _wrapped_view


def docente_requerido(view_func):
    """
    Permite acceso a docentes (o directivos).
    Si un alumno intenta acceder, es redirigido a su portal de alumno.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login:login')}?next={request.path}")

        rol = _rol(request)
        if rol in (Rol.DIRECTIVO, Rol.DOCENTE):
            return view_func(request, *args, **kwargs)
        if rol == Rol.ALUMNO:
            messages.warning(request, "Esta sección es exclusiva para docentes. Te hemos redirigido a tu portal.")
            return redirect('portal:alumno')
        return redirect('login:login')

    return _wrapped_view


def alumno_requerido(view_func):
    """
    Permite acceso a alumnos (o directivos).
    Si un docente intenta acceder, es redirigido a su portal docente.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('login:login')}?next={request.path}")

        rol = _rol(request)
        if rol in (Rol.DIRECTIVO, Rol.ALUMNO):
            return view_func(request, *args, **kwargs)
        if rol == Rol.DOCENTE:
            messages.warning(request, "Esta sección es exclusiva para estudiantes. Te hemos redirigido a tu portal.")
            return redirect('portal:docente')
        return redirect('login:login')

    return _wrapped_view


def autenticacion_requerida(view_func=None):
    decorator = login_required(login_url='login:login')
    if view_func is None:
        return decorator
    return decorator(view_func)

