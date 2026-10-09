from django.urls import path

from . import controlador

app_name = 'carga_alumnos'

urlpatterns = [
    path('', controlador.paso1_carga, name='paso1_carga'),
    path('inicio/', controlador.paso1_carga, name='index'),  # Redirección directa y compatibilidad
    path('confirmacion/', controlador.paso2_confirmacion, name='paso2_confirmacion'),
]

