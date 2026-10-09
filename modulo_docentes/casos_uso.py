"""Reglas de negocio de docentes."""
import datetime
from typing import Any, Dict, List, Tuple

from core.excepciones import ErrorImportacion, RegistroDuplicadoError
from core.formateadores import (
    formatear_carreras_con_resolucion, formatear_cuil, formatear_dni, formatear_telefono,
)
from .dominio import Persona
from .repositorio import DocenteRepositorio


def normalizar_page_size(valor, por_defecto: int = 25) -> int:
    try:
        page_size = int(valor)
        return page_size if page_size in [10, 25, 50, 100] else por_defecto
    except (ValueError, TypeError):
        return por_defecto


class ListarDocentes:
    def __init__(self, repo: DocenteRepositorio):
        self.repo = repo

    def ejecutar(self, query, genero, nacionalidad, localidad, orden):
        return self.repo.buscar(query, genero, nacionalidad, localidad, orden)

    def opciones(self) -> Dict[str, List[str]]:
        return {'nacionalidades': self.repo.nacionalidades(), 'localidades': self.repo.localidades()}

    @staticmethod
    def formatear_pagina(page_obj) -> None:
        for doc in page_obj:
            doc.dni_formateado = formatear_dni(doc.persona.dni)
            doc.cuil_formateado = formatear_cuil(doc.persona.cuil)


class RegistrarDocente:
    """Valida duplicados dentro del lote y confirma el guardado definitivo."""

    def __init__(self, repo: DocenteRepositorio):
        self.repo = repo

    @staticmethod
    def preparar_datos(cleaned: Dict[str, Any]) -> Dict[str, Any]:
        cleaned = dict(cleaned)
        fecha_val = cleaned.get('fecha_nacimiento')
        if isinstance(fecha_val, (datetime.date, datetime.datetime)):
            cleaned['fecha_nacimiento'] = fecha_val.strftime('%Y-%m-%d')
        return cleaned

    @staticmethod
    def validar_lote(matriz, datos: Dict[str, Any]) -> None:
        dni_nuevo = datos.get('dni')
        cuil_nuevo = datos.get('cuil')
        if matriz.duplicado_en_lote('dni', dni_nuevo):
            raise RegistroDuplicadoError(f"El/la docente con DNI {dni_nuevo} ya fue ingresado/a en esta tanda de carga.")
        if cuil_nuevo and matriz.duplicado_en_lote('cuil', cuil_nuevo):
            raise RegistroDuplicadoError(f"El CUIL {cuil_nuevo} ya fue ingresado para otro docente en esta misma tanda.")

    @staticmethod
    def matriz_para_vista(docentes_lista: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        genero_dict = dict(Persona.GENERO_CHOICES)
        resultado = []
        for idx, item in enumerate(docentes_lista):
            copia = item.copy()
            copia['fila_num'] = idx + 1
            copia['fila_index'] = idx
            copia['genero_humano'] = genero_dict.get(item.get('identidad', ''), item.get('identidad', ''))
            copia['dni_formateado'] = formatear_dni(item.get('dni'))
            copia['cuil_formateado'] = formatear_cuil(item.get('cuil'))
            copia['telefono_formateado'] = formatear_telefono(item.get('telefono'))
            resultado.append(copia)
        return resultado

    def confirmar(self, docentes_lista: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        guardados_ok = 0
        errores: List[str] = []

        for datos in docentes_lista:
            dni_candidato = str(datos.get('dni', '')).strip()
            cuil_candidato = str(datos.get('cuil', '')).strip()

            if self.repo.existe_dni(dni_candidato):
                errores.append(f"DNI {dni_candidato} ya existe en la base de datos.")
                continue
            if cuil_candidato and self.repo.existe_cuil(cuil_candidato):
                errores.append(f"CUIL {cuil_candidato} ya existe en la base de datos.")
                continue

            fnac = datos.get('fecha_nacimiento')
            if isinstance(fnac, str) and fnac:
                try:
                    fnac = datetime.datetime.strptime(fnac, '%Y-%m-%d').date()
                except ValueError:
                    fnac = None

            self.repo.crear(dni_candidato, cuil_candidato, datos, fnac)
            guardados_ok += 1
        return guardados_ok, errores


class DetalleDocente:
    def __init__(self, repo: DocenteRepositorio):
        self.repo = repo

    def ejecutar(self, dni_limpio: str) -> Dict[str, Any]:
        docente = self.repo.obtener_por_dni(dni_limpio)
        persona = docente.persona

        comisiones_qs = self.repo.comisiones_con_detalle(docente).prefetch_related('comision__cursadas')

        carreras_dict = {}
        materias_set = set()
        total_alumnos = 0
        comisiones_data = []

        for cd in comisiones_qs:
            com = cd.comision
            plan = com.plan_estudio if com else None
            car = plan.carrera if plan else None
            mat = plan.materia if plan else None

            carrera_name = car.nombre_carrera if car else "Sin Carrera"
            carrera_res = car.resolucion_vigente if car else ""
            materia_name = mat.nombre_materia if mat else "Materia Indefinida"
            anio_carrera = plan.anio_carrera if plan else 1

            if car:
                carreras_dict.setdefault((carrera_name, carrera_res), set()).add(anio_carrera)
            if mat:
                materias_set.add(materia_name)

            cant_inscriptos = com.cursadas.count() if com else 0
            total_alumnos += cant_inscriptos

            comisiones_data.append({
                'comision': com.codigo_comision if com else '-',
                'materia': materia_name,
                'carrera': f"{carrera_name} ({carrera_res})" if carrera_res else carrera_name,
                'anio_carrera': anio_carrera,
                'turno': com.turno if com else '-',
                'division': com.division if com else '-',
                'rol': cd.rol,
                'alumnos_inscriptos': cant_inscriptos,
            })

        return {
            'personal': {
                'dni': formatear_dni(persona.dni),
                'dni_raw': persona.dni,
                'cuil': formatear_cuil(persona.cuil),
                'nombre': persona.nombre,
                'apellido': persona.apellido,
                'nombre_completo': f"Prof. {persona.apellido}, {persona.nombre}",
                'titulo_mn': docente.titulo_mn or 'Sin título/matrícula registrada',
                'fecha_nacimiento': persona.fecha_nacimiento.strftime('%d/%m/%Y') if persona.fecha_nacimiento else '',
                'edad': persona.edad if persona.edad is not None else '',
                'genero_sigla': persona.identidad,
                'genero_desc': persona.genero_descripcion,
                'nacionalidad': persona.nacionalidad or 'Argentina',
                'mail': persona.mail or '',
                'domicilio': persona.domicilio or '',
                'localidad': persona.localidad or '',
                'telefono': formatear_telefono(persona.telefono),
            },
            'resumen_docente': {
                'total_comisiones': len(comisiones_data),
                'total_materias': len(materias_set),
                'carreras': formatear_carreras_con_resolucion(carreras_dict),
                'total_alumnos_a_cargo': total_alumnos,
            },
            'comisiones': comisiones_data,
        }


class FichaDocente:
    def __init__(self, repo: DocenteRepositorio):
        self.repo = repo

    def ejecutar(self, dni_limpio: str) -> Dict[str, Any]:
        docente = self.repo.obtener_por_dni(dni_limpio)
        persona = docente.persona
        comisiones_doc = self.repo.comisiones_con_detalle(docente).order_by(
            '-comision__anio_lectivo',
            'comision__plan_estudio__carrera__nombre_carrera',
            'comision__plan_estudio__materia__nombre_materia',
        )

        materias_set = set()
        carreras_set = set()
        for cd in comisiones_doc:
            pe = cd.comision.plan_estudio
            materias_set.add(pe.materia.nombre_materia)
            carreras_set.add(pe.carrera.nombre_carrera)

        return {
            'persona': persona,
            'docente': docente,
            'dni_formateado': formatear_dni(persona.dni),
            'cuil_formateado': formatear_cuil(persona.cuil),
            'telefono_formateado': formatear_telefono(persona.telefono),
            'comisiones_doc': comisiones_doc,
            'total_comisiones': comisiones_doc.count(),
            'total_materias': len(materias_set),
            'total_carreras': len(carreras_set),
            'fecha_emision': datetime.date.today().strftime('%d/%m/%Y'),
        }


class ImportarDocentesExcel:
    def ejecutar(self, archivo) -> Dict[str, Any]:
        from .importacion_excel import procesar_importacion_docentes_excel
        if not archivo:
            raise ErrorImportacion('No se seleccionó ningún archivo Excel para subir.')
        if not (archivo.name.endswith('.xlsx') or archivo.name.endswith('.xls')):
            raise ErrorImportacion('El archivo debe tener extensión .xlsx o .xls.')
        return procesar_importacion_docentes_excel(archivo)

