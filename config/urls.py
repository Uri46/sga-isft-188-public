import os
from pathlib import Path
from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse, FileResponse


def favicon_view(request):
    base_dir = Path(__file__).resolve().parent.parent
    favicon_path = base_dir / 'capa_presentacion' / 'static' / 'favicon.png'
    if favicon_path.exists():
        return FileResponse(open(favicon_path, 'rb'), content_type="image/png")
    return HttpResponse("", status=204)


urlpatterns = [
    path('favicon.ico', favicon_view, name='favicon'),
    path('favicon.png', favicon_view, name='favicon_png'),
    path('', include('modulo_login.urls')),
    path('', include('modulo_gestion.urls')),
    path('carga-alumnos/', include('modulo_alumnos.urls')),
    path('carreras/', include('modulo_carreras.urls')),
    path('portal/', include('modulo_portal.urls')),
]

if os.environ.get('ENABLE_ADMIN', 'False').lower() in ['true', '1']:
    urlpatterns.append(path('admin/', admin.site.urls))

