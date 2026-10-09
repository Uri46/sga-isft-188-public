"""Interfaz HTTP del módulo de carreras (listado, alta en dos pasos, plan de estudios)."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect

from config.contenedor import contenedor
from core.excepciones import RegistroNoEncontradoError, SGAError
from modulo_login.decorators import directivo_requerido
from django.http import Http404
from .dominio import CLAVE_SESION_CARRERA, CLAVE_SESION_MATRIZ
from .casos_uso import RegistrarCarrera, normalizar_page_size
from .forms import CarreraEditForm, CarreraForm


def _es_ajax(request) -> bool:
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')


def _json_error(e: SGAError):
    return JsonResponse({'success': False, 'mensaje': str(e)}, status=e.codigo_http)


@directivo_requerido
def carreras_listado(request):
    """
    Vista principal del módulo de carreras: listado, búsqueda avanzada,
    filtros por estado de materias y ordenamiento con paginación.
    """
    if request.GET.get('limpiar') == '1' or (request.method == 'POST' and request.POST.get('limpiar') == '1'):
        request.session.pop('carreras_filtros_guardados', None)
        return redirect('carreras:carreras_list')

    if request.method == 'POST':
        request.session['carreras_filtros_guardados'] = {
            'q': request.POST.get('q', '').strip(),
            'con_materias': request.POST.get('con_materias', 'todas'),
            'orden': request.POST.get('orden', 'nombre'),
            'page_size': request.POST.get('page_size', '10'),
            'page': request.POST.get('page', '1'),
        }
        return redirect('carreras:carreras_list')

    filtros_guardados = request.session.get('carreras_filtros_guardados', {})
    query = request.GET.get('q', filtros_guardados.get('q', '')).strip()
    con_materias = request.GET.get('con_materias', filtros_guardados.get('con_materias', 'todas'))
    orden = request.GET.get('orden', filtros_guardados.get('orden', 'nombre'))
    page_req = request.GET.get('page', filtros_guardados.get('page', 1))
    page_size = normalizar_page_size(request.GET.get('page_size', filtros_guardados.get('page_size', 10)))

    carreras = contenedor.listar_carreras.ejecutar(query, con_materias, orden)
    paginator = Paginator(carreras, page_size)
    page_obj = paginator.get_page(page_req)

    return render(request, 'carreras/carreras_list.html', {
        'query': query,
        'con_materias': con_materias,
        'orden': orden,
        'page_size': page_size,
        'page_obj': page_obj,
        'carreras': page_obj.object_list,
        'total_resultados': paginator.count,
    })


@directivo_requerido
def carrera_detalle_json(request, codigo_carrera: str):
    """Endpoint JSON con el expediente de la carrera y su plan de estudios agrupado por año."""
    try:
        return JsonResponse(contenedor.detalle_carrera.ejecutar(codigo_carrera))
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))


@directivo_requerido
@csrf_protect
def alta_carrera(request):
    """
    Paso 1: Formulario para ingresar los datos generales de la nueva carrera.
    Almacena el borrador en la sesión y avanza al Paso 2 (Matriz de Materias).
    """
    borrador = request.session.get(CLAVE_SESION_CARRERA, {})

    if request.method == 'POST':
        form = CarreraForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data.copy()
            request.session[CLAVE_SESION_CARRERA] = cleaned
            request.session.modified = True
            return redirect('carreras:alta_carrera_matriz')
    else:
        form = CarreraForm(initial=borrador)

    return render(request, 'carreras/alta_carrera.html', {
        'form': form,
        'hay_borrador': bool(borrador),
    })


@directivo_requerido
@csrf_protect
def alta_carrera_matriz(request):
    """
    Paso 2: Matriz interactiva de asignaturas agrupadas por año de carrera.
    Permite cargar y editar las materias ordenadas por año y guardar de forma atómica.
    """
    carrera_data = request.session.get(CLAVE_SESION_CARRERA)
    if not carrera_data:
        messages.warning(request, "Primero completá los datos básicos de la carrera.")
        return redirect('carreras:alta_carrera')

    duracion = int(carrera_data.get('duracion_anios', 3))

    if request.method == 'POST':
        accion = request.POST.get('accion', 'guardar')

        if accion == 'volver':
            return redirect('carreras:alta_carrera')

        if accion == 'cancelar':
            request.session.pop(CLAVE_SESION_CARRERA, None)
            request.session.pop(CLAVE_SESION_MATRIZ, None)
            messages.info(request, "Carga de carrera cancelada.")
            return redirect('carreras:carreras_list')

        if accion == 'guardar':
            materias_a_crear, errores = RegistrarCarrera.procesar_matriz(
                request.POST.getlist('materia_codigo[]'),
                request.POST.getlist('materia_nombre[]'),
                request.POST.getlist('materia_anio[]'),
                request.POST.getlist('materia_modalidad[]'),
                request.POST.getlist('materia_hs_semanal[]'),
                request.POST.getlist('materia_correlatividades[]'),
            )

            if errores:
                for err in errores:
                    messages.error(request, err)
                return render(request, 'carreras/alta_carrera_matriz.html', {
                    'carrera': carrera_data,
                    'duracion': duracion,
                    'anios_rango': range(1, duracion + 1),
                    'materias_cargadas': [vars(m) for m in materias_a_crear],
                })

            try:
                carrera = contenedor.registrar_carrera.ejecutar(carrera_data, materias_a_crear)
                request.session.pop(CLAVE_SESION_CARRERA, None)
                request.session.pop(CLAVE_SESION_MATRIZ, None)
                messages.success(
                    request,
                    f"¡Carrera '{carrera.nombre_carrera}' registrada exitosamente con {len(materias_a_crear)} materias en su plan de estudios!"
                )
                return redirect('carreras:carreras_list')
            except Exception as ex:
                messages.error(request, f"Ocurrió un error al guardar la carrera: {str(ex)}")

    return render(request, 'carreras/alta_carrera_matriz.html', {
        'carrera': carrera_data,
        'duracion': duracion,
        'anios_rango': range(1, duracion + 1),
        'materias_cargadas': [],
    })


@directivo_requerido
@csrf_protect
def carrera_editar(request, codigo_carrera: str):
    """
    Edición de datos de una carrera existente (nombre, resoluciones).
    Soporta peticiones AJAX retornando JSON y formularios tradicionales.
    """
    try:
        carrera = contenedor.carrera_repositorio.obtener(codigo_carrera)
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))

    if request.method == 'POST':
        form = CarreraEditForm(request.POST, instance=carrera)
        if form.is_valid():
            form.save()
            mensaje = f"Carrera '{carrera.nombre_carrera}' actualizada correctamente."
            if _es_ajax(request):
                return JsonResponse({'success': True, 'mensaje': mensaje})
            messages.success(request, mensaje)
            return redirect('carreras:carreras_list')
        else:
            errores = {campo: [str(e) for e in errs] for campo, errs in form.errors.items()}
            primer_error = next(iter(form.errors.values()))[0] if form.errors else "Error de validación."
            if _es_ajax(request):
                return JsonResponse({'success': False, 'mensaje': str(primer_error), 'errores': errores}, status=400)
            messages.error(request, str(primer_error))

    return JsonResponse({
        'success': True,
        'codigo_carrera': carrera.codigo_carrera,
        'nombre_carrera': carrera.nombre_carrera,
        'resolucion_vigente': carrera.resolucion_vigente or '',
        'resolucion_anterior': carrera.resolucion_anterior or '',
    })


@directivo_requerido
@csrf_protect
def carrera_eliminar(request, codigo_carrera: str):
    """Eliminación segura de una carrera y su plan de estudios asociado tras confirmación."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)

    try:
        mensaje = contenedor.eliminar_carrera.ejecutar(codigo_carrera)
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    except SGAError as e:
        if _es_ajax(request):
            return JsonResponse({'success': False, 'mensaje': str(e)}, status=400)
        messages.error(request, str(e))
        return redirect('carreras:carreras_list')

    if _es_ajax(request):
        return JsonResponse({'success': True, 'mensaje': mensaje})
    messages.success(request, mensaje)
    return redirect('carreras:carreras_list')


@directivo_requerido
def imprimir_plan_estudio(request, codigo_carrera: str):
    """Vista imprimible del plan de estudios oficial con membrete del ISFT N° 188."""
    try:
        contexto = contenedor.plan_imprimible.ejecutar(codigo_carrera)
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    return render(request, 'carreras/imprimir_plan.html', contexto)


@directivo_requerido
@csrf_protect
def materia_agregar_carrera(request, codigo_carrera: str):
    """Agrega una nueva materia al plan de estudios de la carrera especificada."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)
    try:
        plan, mensaje = contenedor.materias_plan.agregar(codigo_carrera, request.POST)
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    except SGAError as e:
        return _json_error(e)
    return JsonResponse({'success': True, 'mensaje': mensaje, 'id_plan': plan.id_plan})


@directivo_requerido
@csrf_protect
def materia_editar_carrera(request, codigo_carrera: str, id_plan: int):
    """Edita los datos de una materia dentro del plan de estudios de la carrera."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)
    try:
        plan, mensaje = contenedor.materias_plan.editar(codigo_carrera, id_plan, request.POST)
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    except SGAError as e:
        return _json_error(e)
    return JsonResponse({'success': True, 'mensaje': mensaje, 'id_plan': plan.id_plan})


@directivo_requerido
@csrf_protect
def materia_eliminar_carrera(request, codigo_carrera: str, id_plan: int):
    """
    Elimina una materia del plan de estudios tras validar que no posea
    cursadas con alumnos ni registros académicos asociados.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido.'}, status=405)
    try:
        mensaje = contenedor.materias_plan.eliminar(codigo_carrera, id_plan)
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    except SGAError as e:
        return _json_error(e)
    return JsonResponse({'success': True, 'mensaje': mensaje})

