"""Controlador web para operaciones administrativas del sistema (Libro Matriz, plantillas, edición modal)."""
import logging
from django.http import HttpResponse, JsonResponse, Http404
from django.views.decorators.csrf import csrf_protect

from config.contenedor import contenedor
from core.excepciones import ErrorImportacion, RegistroNoEncontradoError, SGAError
from modulo_login.decorators import directivo_requerido

logger = logging.getLogger(__name__)


@directivo_requerido
@csrf_protect
def descargar_libro_matriz(request, codigo_carrera=None):
    """Descarga el Libro Matriz oficial en formato Excel (.xlsx) para la carrera solicitada."""
    try:
        cod = codigo_carrera or request.GET.get('carrera') or request.POST.get('carrera')
        excel_stream, filename = contenedor.generar_libro_matriz.ejecutar(cod)
        response = HttpResponse(
            excel_stream.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    except Exception as e:
        logger.error(f"Error generando libro matriz: {e}", exc_info=True)
        return HttpResponse(
            f"Error al generar el Libro Matriz: {str(e)}",
            status=500,
            content_type="text/plain; charset=utf-8"
        )


@directivo_requerido
def descargar_plantilla_alumnos(request):
    """Descarga la plantilla Excel (.xlsx) oficial formateada para la carga de alumnos."""
    excel_stream, filename = contenedor.generar_plantilla_alumnos.ejecutar()
    response = HttpResponse(
        excel_stream.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@directivo_requerido
@csrf_protect
def importar_alumnos(request):
    """Procesa la subida de un archivo Excel (.xlsx/.xls) para importar o actualizar alumnos."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido. Se requiere POST.'}, status=405)

    try:
        archivo = request.FILES.get('archivo_excel')
        resultado = contenedor.importar_alumnos.ejecutar(archivo)
        return JsonResponse(resultado)
    except ErrorImportacion as e:
        return JsonResponse({'success': False, 'mensaje': str(e)}, status=400)


@directivo_requerido
def persona_datos_json(request, tipo, identificador):
    """Retorna los datos de una persona (alumno o docente) en formato JSON para el modal de edición."""
    try:
        data = contenedor.consultar_persona.ejecutar(tipo, identificador)
        return JsonResponse(data)
    except RegistroNoEncontradoError as e:
        return JsonResponse({'success': False, 'mensaje': str(e)}, status=404)


@directivo_requerido
@csrf_protect
def persona_editar(request, tipo, identificador):
    """Endpoint modular para procesar la edición de Alumnos y Docentes."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)

    try:
        valido, mensaje, errores = contenedor.editar_persona.ejecutar(tipo, identificador, request.POST)
        if valido:
            return JsonResponse({'success': True, 'mensaje': mensaje})
        return JsonResponse({'success': False, 'mensaje': mensaje, 'errores': errores}, status=400)
    except RegistroNoEncontradoError as e:
        return JsonResponse({'success': False, 'mensaje': str(e)}, status=404)
    except SGAError as e:
        return JsonResponse({'success': False, 'mensaje': str(e)}, status=400)


@directivo_requerido
@csrf_protect
def persona_eliminar(request, tipo, identificador):
    """Endpoint modular para eliminación segura de Alumnos y Docentes con confirmación."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)

    try:
        mensaje = contenedor.eliminar_persona.ejecutar(tipo, identificador)
        return JsonResponse({'success': True, 'mensaje': mensaje})
    except RegistroNoEncontradoError as e:
        return JsonResponse({'success': False, 'mensaje': str(e)}, status=404)
    except SGAError as e:
        return JsonResponse({'success': False, 'mensaje': str(e)}, status=400)

