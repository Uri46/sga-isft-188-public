"""Interfaz de registro interactivo de alumnos (Paso 1 y 2) y buscador institucional."""
from typing import Any, Dict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect

from config.contenedor import contenedor
from core.excepciones import RegistroDuplicadoError, RegistroNoEncontradoError
from core.formateadores import limpiar_dni
from core.matriz_sesion import MatrizSesion
from modulo_base_datos.models import Persona
from modulo_login.decorators import directivo_requerido
from .casos_uso import CLAVE_SESION_EDICION, CLAVE_SESION_MATRIZ, RegistrarAlumno, normalizar_page_size
from .forms import AlumnoForm


def _matriz(request) -> MatrizSesion:
    return MatrizSesion(request.session, CLAVE_SESION_MATRIZ, CLAVE_SESION_EDICION)


def obtener_alumnos_sesion(request: Any):
    """Alumnos acumulados en la sesión (compatible con sesiones antiguas que guardaban un dict)."""
    return _matriz(request).obtener()


# ====================================================================== Registro interactivo
@directivo_requerido
def index(request: Any) -> Any:
    """Redirige de forma directa al formulario de carga de alumnos (Paso 1)."""
    return redirect(reverse('carga_alumnos:paso1_carga'))


@directivo_requerido
def paso1_carga(request: Any) -> Any:
    """
    Paso 1: Formulario directo de ingreso secuencial y validado de datos del alumno.
    Permite cargar un alumno o acumular múltiples alumnos en la matriz de la sesión.
    """
    matriz = _matriz(request)
    alumnos_acumulados = matriz.obtener()

    def _render(form):
        return render(request, 'carga_alumnos/paso1_carga.html', {
            'form': form,
            'total_en_matriz': len(alumnos_acumulados),
            'hay_borrador_pendiente': bool(alumnos_acumulados),
        })

    if request.method == 'POST':
        form = AlumnoForm(request.POST)
        if form.is_valid():
            cleaned = RegistrarAlumno.preparar_datos(form.cleaned_data)
            try:
                RegistrarAlumno.validar_lote(matriz, cleaned)
            except RegistroDuplicadoError as e:
                messages.error(request, str(e))
                return _render(form)

            matriz.agregar(cleaned)
            messages.success(
                request,
                f"Alumno {cleaned.get('apellido')}, {cleaned.get('nombre')} incorporado a la matriz de verificación."
            )
            return redirect(reverse('carga_alumnos:paso2_confirmacion'))
        else:
            messages.error(request, RegistrarAlumno.resumir_errores(form))
    else:
        # En GET: Si hay datos para edición, cargarlos en el formulario
        datos_edit = matriz.tomar_edicion()
        form = AlumnoForm(initial=datos_edit) if datos_edit else AlumnoForm()

    return _render(form)


@directivo_requerido
def paso2_confirmacion(request: Any) -> Any:
    """
    Paso 2: Previsualización en matriz de datos completa y confirmación.
    - 'confirmar': guarda todos los alumnos de la matriz en base de datos y sincroniza con gestión.
    - 'nuevo_alumno': conserva la matriz actual y abre el Paso 1 para sumar otro alumno.
    - 'modificar': extrae el último alumno para corregirlo en el Paso 1.
    - 'editar_fila': extrae un alumno específico según índice para corregirlo en el Paso 1.
    - 'eliminar_fila': quita un alumno específico de la matriz antes de confirmar.
    - 'cancelar': descarta toda la matriz y reinicia la carga.
    """
    matriz = _matriz(request)
    alumnos_lista = matriz.obtener()

    if not alumnos_lista:
        messages.warning(request, "No hay ningún alumno en la matriz de carga. Ingrese los datos primero.")
        return redirect(reverse('carga_alumnos:paso1_carga'))

    alumnos_matriz = RegistrarAlumno.matriz_para_vista(alumnos_lista)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'confirmar':
            guardados_ok, errores = contenedor.registrar_alumno.confirmar(alumnos_lista)
            matriz.vaciar()

            if guardados_ok > 0:
                messages.success(
                    request,
                    f"¡Excelente! Se han guardado exitosamente {guardados_ok} alumno(s) en el sistema."
                )
            for err in errores:
                messages.error(request, err)
            return redirect(reverse('carga_alumnos:paso1_carga'))

        elif accion == 'nuevo_alumno':
            messages.info(request, "Completá el formulario para sumar otro alumno a la matriz.")
            return redirect(reverse('carga_alumnos:paso1_carga'))

        elif accion == 'modificar':
            datos_edit = matriz.extraer()
            if datos_edit:
                messages.info(request, f"Modificando datos de {datos_edit.get('apellido', '')}, {datos_edit.get('nombre', '')}.")
            return redirect(reverse('carga_alumnos:paso1_carga'))

        elif accion == 'editar_fila':
            try:
                datos_edit = matriz.extraer(int(request.POST.get('fila_index', -1)))
                if datos_edit:
                    messages.info(request, f"Modificando datos de {datos_edit.get('apellido', '')}, {datos_edit.get('nombre', '')}.")
                    return redirect(reverse('carga_alumnos:paso1_carga'))
            except (ValueError, TypeError):
                pass
            return redirect(reverse('carga_alumnos:paso2_confirmacion'))

        elif accion == 'eliminar_fila':
            try:
                eliminado = matriz.quitar(int(request.POST.get('fila_index', -1)))
                if eliminado:
                    messages.info(request, f"Se quitó a {eliminado.get('apellido', '')}, {eliminado.get('nombre', '')} de la matriz.")
            except (ValueError, TypeError):
                pass

            if not matriz.obtener():
                return redirect(reverse('carga_alumnos:paso1_carga'))
            return redirect(reverse('carga_alumnos:paso2_confirmacion'))

        elif accion == 'cancelar':
            matriz.vaciar()
            messages.info(request, "Carga cancelada. La matriz de alumnos ha sido vaciada.")
            return redirect(reverse('carga_alumnos:paso1_carga'))

    context: Dict[str, Any] = {
        'alumnos_matriz': alumnos_matriz,
        'total_alumnos': len(alumnos_matriz),
    }
    return render(request, 'carga_alumnos/paso2_confirmacion.html', context)


# ====================================================================== Buscador / ficha
@directivo_requerido
@csrf_protect
def buscador(request):
    req_data = request.POST if request.method == 'POST' else request.GET

    query = req_data.get('q', '').strip()
    carrera_nombre = req_data.get('carrera_nombre', '').strip()
    plan_id = req_data.get('plan_id', '').strip()
    # Compatibilidad con parametro 'carrera' previo
    carrera_legacy = req_data.get('carrera', '').strip()
    if carrera_legacy and not carrera_nombre and not plan_id:
        plan_id, carrera_nombre = contenedor.alumno_repositorio.resolver_carrera_legacy(carrera_legacy)

    anio_filtro = req_data.get('anio', '').strip()
    genero_filtro = req_data.get('genero', '').strip()
    nacionalidad_filtro = req_data.get('nacionalidad', '').strip()
    localidad_filtro = req_data.get('localidad', '').strip()
    orden_filtro = req_data.get('orden', 'apellido').strip()
    page_num = req_data.get('page', '1').strip()
    page_size = normalizar_page_size(req_data.get('page_size', '25').strip())

    if len(query) > 100:
        query = query[:100]

    alumnos_list = contenedor.buscar_alumnos.ejecutar(
        query, plan_id, carrera_nombre, anio_filtro, genero_filtro,
        nacionalidad_filtro, localidad_filtro, orden_filtro)
    opciones = contenedor.alumno_repositorio.opciones_filtros()

    paginator = Paginator(alumnos_list, page_size)
    page_obj = paginator.get_page(page_num)

    context = {
        'query': query,
        'carrera_nombre': carrera_nombre,
        'plan_id': plan_id,
        'carrera_id': plan_id or carrera_nombre,
        'anio_filtro': anio_filtro,
        'genero_filtro': genero_filtro,
        'nacionalidad_filtro': nacionalidad_filtro,
        'localidad_filtro': localidad_filtro,
        'orden_filtro': orden_filtro,
        'page_size': page_size,
        'page_obj': page_obj,
        'alumnos_list': page_obj.object_list,
        'total_resultados': len(alumnos_list),
        'generos_choices': Persona.GENERO_CHOICES,
        **opciones,
    }
    return render(request, 'gestion/buscador.html', context)


@directivo_requerido
@csrf_protect
def alumno_detalle_json(request, dni):
    try:
        return JsonResponse(contenedor.detalle_alumno.ejecutar(limpiar_dni(dni)))
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))


@login_required(login_url='login:login')
@csrf_protect
def imprimir_estado_academico(request, dni):
    dni_clean = limpiar_dni(dni)

    # Acceso exclusivo para el alumno o directivos
    if not (request.user.is_staff or request.user.is_superuser):
        user_dni = str(request.user.username).strip()
        if user_dni != dni_clean:
            raise PermissionDenied("Acceso restringido: solo podés consultar o imprimir tu propio expediente.")

    try:
        contexto = contenedor.estado_academico.ejecutar(dni_clean)
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    return render(request, 'gestion/imprimir_analitico.html', contexto)

