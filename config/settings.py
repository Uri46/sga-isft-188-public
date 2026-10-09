"""Django settings para la arquitectura sga_modular del Sistema de Gestión Académica (ISFT N° 188)."""

import os
from pathlib import Path
from modulo_base_datos.conexion import construir_databases

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    # Generar clave de respaldo efímera si no está definida en desarrollo
    SECRET_KEY = 'insecure-dev-key-change-me-in-production-only-for-local-testing'

# Por defecto en producción DEBUG es False; se habilita explícitamente con DEBUG=True en .env
DEBUG = os.environ.get('DEBUG', 'False').lower() in ['true', '1', 'yes']

# ALLOWED_HOSTS seguro por defecto (localhost y loopback). En producción se configura mediante variable de entorno.
hosts_env = os.environ.get('ALLOWED_HOSTS', '')
if hosts_env:
    ALLOWED_HOSTS = [h.strip() for h in hosts_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', '[::1]', 'testserver']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Módulos del SGA Modular
    'modulo_base_datos.apps.BaseDatosConfig',
    'modulo_login.apps.LoginConfig',
    'modulo_alumnos.apps.CargaAlumnosConfig',
    'modulo_docentes.apps.ModuloDocentesConfig',
    'modulo_carreras.apps.CarrerasConfig',
    'modulo_gestion.apps.ModuloGestionConfig',
    'modulo_portal.apps.PortalConfig',
]

AUTHENTICATION_BACKENDS = [
    'modulo_login.backends.DNIAuthBackend',
    'django.contrib.auth.backends.ModelBackend',
]

LOGIN_URL = 'login:login'
LOGIN_REDIRECT_URL = 'gestion:buscador'
LOGOUT_REDIRECT_URL = 'login:login'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'capa_presentacion' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'

# Configuración de Base de Datos desacoplada y centralizada
DATABASES = construir_databases(BASE_DIR)

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'es-ar'
TIME_ZONE = 'America/Argentina/Buenos_Aires'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'capa_presentacion' / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

csrf_trusted_env = os.environ.get('CSRF_TRUSTED_ORIGINS', '')
if csrf_trusted_env:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in csrf_trusted_env.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        'https://*.up.railway.app',
        'https://*.onrender.com',
        'https://*.fly.dev',
        'https://*.herokuapp.com',
        'http://localhost:8000',
        'http://127.0.0.1:8000',
        'http://localhost:3000',
    ]

