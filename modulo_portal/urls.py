from django.urls import path

from . import controlador

app_name = 'portal'

urlpatterns = [
    path('alumno/', controlador.portal_alumno, name='alumno'),
    path('docente/', controlador.portal_docente, name='docente'),
]

