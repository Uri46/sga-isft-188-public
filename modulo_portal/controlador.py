"""Enrutador/Dashboard según rol (Alumno, Docente)."""
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.csrf import csrf_protect

from core.excepciones import RegistroNoEncontradoError
from modulo_login.decorators import alumno_requerido, docente_requerido
from .casos_uso import ArmarPortalAlumno, ArmarPortalDocente


@alumno_requerido
@csrf_protect
def portal_alumno(request):
    """
    Portal exclusivo para estudiantes.
    Muestra únicamente los datos personales, historial académico ordenado por carrera y año,
    calificaciones parciales y finales, asistencia y docentes a cargo del alumno autenticado.
    """
    try:
        context = ArmarPortalAlumno().ejecutar(str(request.user.username).strip())
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    return render(request, 'portal/alumno_portal.html', context)


@docente_requerido
@csrf_protect
def portal_docente(request):
    """
    Portal exclusivo para docentes.
    Muestra únicamente los datos personales, profesionales y las asignaturas/comisiones
    en las que el docente se encuentra asignado, organizadas por carrera y año.
    """
    try:
        context = ArmarPortalDocente().ejecutar(str(request.user.username).strip())
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    return render(request, 'portal/docente_portal.html', context)

