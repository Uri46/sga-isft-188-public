from django.urls import path

from . import controlador

app_name = 'carreras'

urlpatterns = [
    path('', controlador.carreras_listado, name='carreras_list'),
    path('alta/', controlador.alta_carrera, name='alta_carrera'),
    path('alta/matriz/', controlador.alta_carrera_matriz, name='alta_carrera_matriz'),
    path('api/<str:codigo_carrera>/detalle/', controlador.carrera_detalle_json, name='carrera_detalle_json'),
    path('<str:codigo_carrera>/editar/', controlador.carrera_editar, name='carrera_editar'),
    path('<str:codigo_carrera>/eliminar/', controlador.carrera_eliminar, name='carrera_eliminar'),
    path('<str:codigo_carrera>/imprimir/', controlador.imprimir_plan_estudio, name='imprimir_plan_estudio'),
    path('<str:codigo_carrera>/materias/agregar/', controlador.materia_agregar_carrera, name='materia_agregar'),
    path('<str:codigo_carrera>/materias/<int:id_plan>/editar/', controlador.materia_editar_carrera, name='materia_editar'),
    path('<str:codigo_carrera>/materias/<int:id_plan>/eliminar/', controlador.materia_eliminar_carrera, name='materia_eliminar'),
]

