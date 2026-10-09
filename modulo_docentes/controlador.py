"""Módulo de gestión de docentes: listado, filtros, carga por lotes y ficha institucional."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect

from config.contenedor import contenedor
from core.excepciones import ErrorImportacion, RegistroDuplicadoError, RegistroNoEncontradoError
from core.formateadores import limpiar_dni
from core.matriz_sesion import MatrizSesion
from modulo_login.decorators import directivo_requerido
from .casos_uso import RegistrarDocente, normalizar_page_size
from .dominio import CLAVE_SESION_DOCENTES, CLAVE_SESION_DOCENTES_EDICION, Persona
from .forms import DocenteForm


def _matriz(request) -> MatrizSesion:
    return MatrizSesion(request.session, CLAVE_SESION_DOCENTES, CLAVE_SESION_DOCENTES_EDICION)


def obtener_docentes_sesion(request):
    return _matriz(request).obtener()


@directivo_requerido
@csrf_protect
def docentes(request):
    """Módulo de búsqueda, filtrado y consulta de docentes."""
    req_data = request.POST if request.method == 'POST' else request.GET

    query = req_data.get('q', '').strip()[:100]
    genero_filtro = req_data.get('genero', '').strip()
    nacionalidad_filtro = req_data.get('nacionalidad', '').strip()
    localidad_filtro = req_data.get('localidad', '').strip()
    orden_filtro = req_data.get('orden', 'apellido').strip()
    page_num = req_data.get('page', '1').strip()
    page_size = normalizar_page_size(req_data.get('page_size', '25').strip())

    caso = contenedor.listar_docentes
    queryset = caso.ejecutar(query, genero_filtro, nacionalidad_filtro, localidad_filtro, orden_filtro)
    opciones = caso.opciones()

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_num)
    caso.formatear_pagina(page_obj)

    return render(request, 'gestion/docentes.html', {
        'query': query,
        'genero_filtro': genero_filtro,
        'generos_choices': Persona.GENERO_CHOICES,
        'nacionalidad_filtro': nacionalidad_filtro,
        'nacionalidades': opciones['nacionalidades'],
        'localidad_filtro': localidad_filtro,
        'localidades': opciones['localidades'],
        'orden_filtro': orden_filtro,
        'page_size': page_size,
        'page_obj': page_obj,
        'docentes': page_obj.object_list,
        'total_resultados': paginator.count,
    })


@directivo_requerido
@csrf_protect
def alta_docente(request):
    """
    Formulario guiado para el alta individual de un docente.
    Guarda en la matriz de sesión y redirige al Paso 2 de confirmación.
    """
    matriz = _matriz(request)
    docentes_acumulados = matriz.obtener()

    def _render(form):
        return render(request, 'gestion/docentes/alta.html', {
            'form': form,
            'total_en_matriz': len(docentes_acumulados),
            'hay_borrador_pendiente': bool(docentes_acumulados),
        })

    if request.method == 'POST':
        form = DocenteForm(request.POST)
        if form.is_valid():
            cleaned = RegistrarDocente.preparar_datos(form.cleaned_data)
            try:
                RegistrarDocente.validar_lote(matriz, cleaned)
            except RegistroDuplicadoError as e:
                messages.error(request, str(e))
                return _render(form)

            matriz.agregar(cleaned)
            messages.success(
                request,
                f"Docente {cleaned.get('apellido')}, {cleaned.get('nombre')} incorporado/a a la matriz de verificación."
            )
            return redirect(reverse('gestion:paso2_confirmacion_docentes'))
        else:
            messages.error(
                request,
                "Por favor, revisá los campos señalados en rojo para corregir los datos ingresados."
            )
    else:
        datos_edit = matriz.tomar_edicion()
        form = DocenteForm(initial=datos_edit) if datos_edit else DocenteForm()

    return _render(form)


@directivo_requerido
@csrf_protect
def paso2_confirmacion_docentes(request):
    """
    Paso 2: Previsualización en matriz de datos completa y confirmación para Docentes.
    Permite visualizar uno o más docentes en una matriz completa.
    """
    matriz = _matriz(request)
    docentes_lista = matriz.obtener()

    if not docentes_lista:
        messages.warning(request, "No hay ningún docente en la matriz de carga. Ingresá los datos primero.")
        return redirect(reverse('gestion:alta_docente'))

    docentes_matriz = RegistrarDocente.matriz_para_vista(docentes_lista)

    if request.method == 'POST':
        accion = request.POST.get('accion')

        if accion == 'confirmar':
            guardados_ok, errores = contenedor.registrar_docente.confirmar(docentes_lista)
            matriz.vaciar()

            if guardados_ok > 0:
                messages.success(
                    request,
                    f"¡Excelente! Se confirmaron y guardaron exitosamente {guardados_ok} docente{'s' if guardados_ok != 1 else ''} en el sistema."
                )
            for err in errores:
                messages.error(request, err)
            return redirect(reverse('gestion:docentes'))

        elif accion == 'nuevo_docente':
            return redirect(reverse('gestion:alta_docente'))

        elif accion == 'modificar':
            matriz.extraer()
            return redirect(reverse('gestion:alta_docente'))

        elif accion == 'editar_fila':
            try:
                matriz.extraer(int(request.POST.get('fila_index', -1)))
            except (ValueError, TypeError):
                pass
            return redirect(reverse('gestion:alta_docente'))

        elif accion == 'eliminar_fila':
            try:
                eliminado = matriz.quitar(int(request.POST.get('fila_index', -1)))
                if eliminado:
                    messages.info(
                        request,
                        f"Docente {eliminado.get('apellido')}, {eliminado.get('nombre')} quitado/a de la matriz."
                    )
            except (ValueError, TypeError):
                pass

            if not matriz.obtener():
                return redirect(reverse('gestion:alta_docente'))
            return redirect(reverse('gestion:paso2_confirmacion_docentes'))

        elif accion == 'cancelar':
            matriz.vaciar(incluir_edicion=True)
            messages.info(request, "Se descartó la matriz de docentes.")
            return redirect(reverse('gestion:alta_docente'))

    return render(request, 'gestion/docentes/paso2_confirmacion.html', {
        'docentes_matriz': docentes_matriz,
        'total_docentes': len(docentes_matriz),
    })


@directivo_requerido
@csrf_protect
def docente_detalle_json(request, dni):
    try:
        return JsonResponse(contenedor.detalle_docente.ejecutar(limpiar_dni(dni)))
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))


@directivo_requerido
@csrf_protect
def importar_docentes(request):
    """
    Procesa la subida de un archivo Excel (.xlsx/.xls) para importar o actualizar docentes.
    Retorna el resultado en formato JSON para visualización interactiva con reporte de errores.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'mensaje': 'Método no permitido. Se requiere POST.'}, status=405)
    try:
        resultado = contenedor.importar_docentes.ejecutar(request.FILES.get('archivo_excel'))
    except ErrorImportacion as e:
        return JsonResponse({'success': False, 'mensaje': str(e)}, status=400)
    return JsonResponse(resultado)


@login_required(login_url='login:login')
def imprimir_ficha_docente(request, dni: str):
    """Vista oficial para imprimir la ficha de legajo institucional del docente."""
    dni_clean = limpiar_dni(dni)

    # Acceso exclusivo para el docente o directivos
    if not (request.user.is_staff or request.user.is_superuser):
        user_dni = str(request.user.username).strip()
        if user_dni != dni_clean:
            raise PermissionDenied("Acceso restringido: solo podés consultar o imprimir tu propia ficha docente.")
    try:
        contexto = contenedor.ficha_docente.ejecutar(dni_clean)
    except RegistroNoEncontradoError as e:
        raise Http404(str(e))
    return render(request, 'gestion/docentes/imprimir_docente.html', contexto)

