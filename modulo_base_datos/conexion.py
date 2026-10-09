"""Configuración de conexión a la base de datos (PostgreSQL con fallback a SQLite).

`construir_databases` conserva exactamente la lógica original de settings.py y
`registrar_foreign_keys_sqlite` garantiza que SQLite aplique las Foreign Keys.
"""
import os
import urllib.parse as urlparse
from pathlib import Path
from typing import Any, Dict, Optional

_ENGINE_PG = 'django.db.backends.postgresql'


def _config_postgres(nombre, usuario, password, host, puerto) -> Dict[str, Any]:
    return {
        'ENGINE': _ENGINE_PG,
        'NAME': nombre,
        'USER': usuario,
        'PASSWORD': password,
        'HOST': host,
        'PORT': puerto,
    }


def _postgres_disponible(nombre, usuario, password, host, puerto) -> bool:
    try:
        import psycopg2
        conn = psycopg2.connect(dbname=nombre, user=usuario, password=password,
                                host=host, port=puerto, connect_timeout=2)
        conn.close()
        return True
    except Exception:
        return False


def construir_databases(base_dir: Path, env: Optional[Dict[str, str]] = None) -> Dict[str, Dict[str, Any]]:
    """Devuelve el dict DATABASES. Prioridad: DATABASE_URL > variables DB_* > SQLite local."""
    env = os.environ if env is None else env

    database_url = env.get('DATABASE_URL')
    if database_url:
        try:
            url = urlparse.urlparse(database_url)
            return {'default': _config_postgres(url.path[1:], url.username, url.password,
                                                url.hostname, url.port or 5432)}
        except Exception:
            pass

    db_engine = env.get('DB_ENGINE', '')
    nombre = env.get('DB_NAME')
    usuario = env.get('DB_USER')
    password = env.get('DB_PASSWORD')
    host = env.get('DB_HOST', 'localhost')
    puerto = env.get('DB_PORT', '5432')

    if db_engine in ('postgresql', _ENGINE_PG) and nombre and usuario and password and _postgres_disponible(nombre, usuario, password, host, puerto):
        return {'default': _config_postgres(nombre, usuario, password, host, puerto)}

    return {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': base_dir / 'db.sqlite3',
        }
    }


def registrar_foreign_keys_sqlite() -> None:
    """Activa `PRAGMA foreign_keys = ON` en cada conexión SQLite nueva."""
    from django.db.backends.signals import connection_created

    def _activar(sender, connection, **kwargs):
        if connection.vendor == 'sqlite':
            connection.cursor().execute('PRAGMA foreign_keys = ON;')

    connection_created.connect(_activar, dispatch_uid='sga_sqlite_foreign_keys')

