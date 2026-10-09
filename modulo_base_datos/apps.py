from django.apps import AppConfig


class BaseDatosConfig(AppConfig):
    """
    Conserva el label histórico 'gestion' para mantener intactas las tablas
    (gestion_persona, gestion_alumno, ...), las migraciones y los fixtures existentes.
    """
    name = 'modulo_base_datos'
    label = 'gestion'
    verbose_name = 'Base de Datos del SGA'

    def ready(self):
        from .conexion import registrar_foreign_keys_sqlite
        registrar_foreign_keys_sqlite()

