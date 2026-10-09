from django.urls import path

from modulo_alumnos import controlador as alumnos_controlador
from modulo_docentes import controlador as docentes_controlador
from . import controlador as gestion_controlador

app_name = 'gestion'

urlpatterns = [
    # Buscador y gestión de alumnos
    path('', alumnos_controlador.buscador, name='buscador'),
    path('api/alumno/<str:dni>/', alumnos_controlador.alumno_detalle_json, name='alumno_detalle_json'),
    path('alumno/<str:dni>/imprimir/', alumnos_controlador.imprimir_estado_academico, name='imprimir_estado_academico'),

    # Docentes
    path('docentes/', docentes_controlador.docentes, name='docentes'),
    path('docentes/alta/', docentes_controlador.alta_docente, name='alta_docente'),
    path('docentes/confirmacion/', docentes_controlador.paso2_confirmacion_docentes, name='paso2_confirmacion_docentes'),
    path('importar-docentes/', docentes_controlador.importar_docentes, name='importar_docentes'),
    path('api/docente/<str:dni>/', docentes_controlador.docente_detalle_json, name='docente_detalle_json'),
    path('docente/<str:dni>/imprimir/', docentes_controlador.imprimir_ficha_docente, name='imprimir_ficha_docente'),

    # Operaciones CRUD modales y administrativas
    path('api/persona-datos/<str:tipo>/<str:identificador>/', gestion_controlador.persona_datos_json, name='persona_datos_json'),
    path('editar/<str:tipo>/<str:identificador>/', gestion_controlador.persona_editar, name='persona_editar'),
    path('eliminar/<str:tipo>/<str:identificador>/', gestion_controlador.persona_eliminar, name='persona_eliminar'),

    # Libro Matriz y plantillas masivas
    path('libro-matriz/', gestion_controlador.descargar_libro_matriz, name='descargar_libro_matriz'),
    path('libro-matriz/<str:codigo_carrera>/', gestion_controlador.descargar_libro_matriz, name='descargar_libro_matriz_carrera'),
    path('plantilla-alumnos/', gestion_controlador.descargar_plantilla_alumnos, name='descargar_plantilla_alumnos'),
    path('importar-alumnos/', gestion_controlador.importar_alumnos, name='importar_alumnos'),
]

