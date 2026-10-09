from django.apps import AppConfig


class LoginConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modulo_login'
    label = 'login'
    verbose_name = 'Módulo de Inicio de Sesión y Autenticación'

