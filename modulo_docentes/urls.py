from django.urls import path
from . import controlador

app_name = 'docentes'

urlpatterns = [
    path('', controlador.docentes, name='docentes_list'),
    path('alta/', controlador.alta_docente, name='alta'),
    path('confirmacion/', controlador.paso2_confirmacion_docentes, name='confirmacion'),
    path('importar/', controlador.importar_docentes, name='importar'),
    path('api/<str:dni>/', controlador.docente_detalle_json, name='detalle_json'),
    path('<str:dni>/imprimir/', controlador.imprimir_ficha_docente, name='imprimir'),
]

