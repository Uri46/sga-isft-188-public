"""Reglas de negocio de alumnos: búsqueda, ficha, expediente y carga por lotes."""
import datetime
from typing import Any, Dict, List, Tuple

from core.excepciones import RegistroDuplicadoError
from core.formateadores import (
    formatear_carreras_con_resolucion, formatear_carreras_estructuradas, formatear_cuil, formatear_dni, formatear_telefono,
)
from modulo_base_datos.models import Persona
from .dominio import Alumno as AlumnoCarga, CLAVE_SESION_EDICION, CLAVE_SESION_MATRIZ  # noqa: F401
from .repositorio import AlumnoRepositorio


def normalizar_page_size(valor, por_defecto: int = 25) -> int:
    try:
        page_size = int(valor)
        return page_size if page_size in [10, 25, 50, 100] else por_defecto
    except (ValueError, TypeError):
        return por_defecto


class BuscarAlumnos:
    """Buscador institucional de alumnos con filtros, métricas académicas y ordenamiento."""

    def __init__(self, repo: AlumnoRepositorio):
        self.repo = repo

    def ejecutar(self, query: str, plan_id: str, carrera_nombre: str, anio: str, genero: str,
                 nacionalidad: str, localidad: str, orden: str) -> List[Dict[str, Any]]:
        alumnos = self.repo.buscar(query, plan_id, carrera_nombre, genero, nacionalidad, anio, localidad)

        alumnos_list = []
        for al in alumnos:
            cursadas = al.cursadas.all()
            carreras_dict = {}
            for c in cursadas:
                if c.comision and c.comision.plan_estudio and c.comision.plan_estudio.carrera:
                    car = c.comision.plan_estudio.carrera
                    carreras_dict.setdefault((car.nombre_carrera, car.resolucion_vigente), set()).add(
                        c.comision.plan_estudio.anio_carrera)

            carreras_formatted_list = formatear_carreras_con_resolucion(carreras_dict)
            carreras_estructuradas = formatear_carreras_estructuradas(carreras_dict)

            promocionadas = sum(1 for c in cursadas if c.situacion_final == 'Promocionado')
            regulares = sum(1 for c in cursadas if c.situacion_final == 'Regular')
            finales = sum(1 for c in cursadas if c.situacion_final == 'Final')
            libres = sum(1 for c in cursadas if c.situacion_final == 'Libre')

            notas_list = []
            for c in cursadas:
                for ev in c.evaluaciones.all():
                    if ev.nota is not None:
                        notas_list.append(float(ev.nota))
            promedio = round(sum(notas_list) / len(notas_list), 2) if notas_list else None

            alumnos_list.append({
                'alumno': al,
                'persona': al.persona,
                'dni_formateado': formatear_dni(al.persona.dni),
                'cuil_formateado': formatear_cuil(al.persona.cuil),
                'telefono_formateado': formatear_telefono(al.persona.telefono),
                'edad': al.persona.edad,
                'carreras': ", ".join(carreras_formatted_list) if carreras_formatted_list else "Sin Inscripción Activa",
                'carreras_estructuradas': carreras_estructuradas,
                'localidad': al.persona.localidad or 'Sin registrar',
                'nacionalidad': al.persona.nacionalidad or 'Argentina',
                'genero_sigla': al.persona.identidad,
                'genero_desc': al.persona.genero_descripcion,
                'cuil': al.persona.cuil or '-',
                'total_cursadas': cursadas.count(),
                'promocionadas': promocionadas,
                'regulares': regulares,
                'finales': finales,
                'libres': libres,
                'promedio': promedio,
            })

        self._ordenar(alumnos_list, orden)
        return alumnos_list

    @staticmethod
    def _ordenar(alumnos_list: List[Dict[str, Any]], orden: str) -> None:
        if orden == 'nombre':
            alumnos_list.sort(key=lambda x: (x['persona'].nombre or '').lower())
        elif orden == 'dni':
            alumnos_list.sort(key=lambda x: int(x['persona'].dni) if x['persona'].dni.isdigit() else 0)
        elif orden == 'carrera':
            alumnos_list.sort(key=lambda x: x['carreras'].lower())
        elif orden == 'edad_asc':
            alumnos_list.sort(key=lambda x: (x['edad'] is None, x['edad']))
        elif orden == 'edad_desc':
            alumnos_list.sort(key=lambda x: (x['edad'] is None, -(x['edad'] or 0)))
        elif orden == 'localidad':
            alumnos_list.sort(key=lambda x: (x['localidad'] or '').lower())
        elif orden == 'nacionalidad':
            alumnos_list.sort(key=lambda x: (x['nacionalidad'] or '').lower())
        else:
            alumnos_list.sort(key=lambda x: (x['persona'].apellido or '').lower())


class DetalleAlumno:
    def __init__(self, repo: AlumnoRepositorio):
        self.repo = repo

    def ejecutar(self, dni_limpio: str) -> Dict[str, Any]:
        persona, alumno = self.repo.obtener_persona_alumno(dni_limpio)
        cursadas_qs = self.repo.cursadas_con_detalle(alumno).prefetch_related(
            'evaluaciones', 'comision__docentes_asignados__docente__persona')

        carreras_dict = {}
        total_notas = 0
        cant_notas = 0
        cursadas_data = []

        for c in cursadas_qs:
            car = c.comision.plan_estudio.carrera if c.comision and c.comision.plan_estudio else None
            materia_name = c.comision.plan_estudio.materia.nombre_materia if c.comision and c.comision.plan_estudio and c.comision.plan_estudio.materia else "Materia Indefinida"
            carrera_name = car.nombre_carrera if car else "Sin Carrera"
            carrera_res = car.resolucion_vigente if car else ""
            anio_carrera = c.comision.plan_estudio.anio_carrera if c.comision and c.comision.plan_estudio else 1

            if car:
                carreras_dict.setdefault((carrera_name, carrera_res), set()).add(anio_carrera)

            docentes_list = [f"{d.docente.persona.apellido}, {d.docente.persona.nombre}" for d in c.comision.docentes_asignados.all()]
            docentes_str = ", ".join(docentes_list) if docentes_list else "A designar"

            evals_data = []
            nota_final_val = None
            for ev in c.evaluaciones.all():
                evals_data.append({
                    'instancia': ev.instancia,
                    'nota': float(ev.nota) if ev.nota is not None else None,
                    'fecha': ev.fecha.strftime('%d/%m/%Y') if ev.fecha else ''
                })
                if ev.nota is not None:
                    total_notas += float(ev.nota)
                    cant_notas += 1
                    if ev.instancia == 'Nota Final':
                        nota_final_val = float(ev.nota)

            cursadas_data.append({
                'id_cursada': c.id_cursada,
                'carrera': f"{carrera_name} ({carrera_res})" if carrera_res else carrera_name,
                'materia': materia_name,
                'anio_carrera': anio_carrera,
                'comision': c.comision.codigo_comision if c.comision else '-',
                'docentes': docentes_str,
                'situacion': c.situacion_final,
                'nota_final': nota_final_val,
                'evaluaciones': evals_data
            })

        cant_cursadas = len(cursadas_data)
        promedio_notas = round(total_notas / cant_notas, 2) if cant_notas > 0 else "N/A"

        return {
            'personal': {
                'dni': formatear_dni(persona.dni),
                'dni_raw': persona.dni,
                'cuil': formatear_cuil(persona.cuil),
                'nombre': persona.nombre,
                'apellido': persona.apellido,
                'nombre_completo': f"{persona.apellido}, {persona.nombre}",
                'legajo': alumno.legajo or f"LEG-{persona.dni}",
                'fecha_nacimiento': persona.fecha_nacimiento.strftime('%d/%m/%Y') if persona.fecha_nacimiento else '',
                'edad': persona.edad if persona.edad is not None else '',
                'genero_sigla': persona.identidad,
                'genero_desc': persona.genero_descripcion,
                'nacionalidad': persona.nacionalidad or '',
                'mail': persona.mail or '',
                'domicilio': persona.domicilio or '',
                'localidad': persona.localidad or '',
                'telefono': formatear_telefono(persona.telefono)
            },
            'resumen_academico': {
                'carreras': formatear_carreras_con_resolucion(carreras_dict),
                'total_materias_cursadas': cant_cursadas,
                'promedio_notas': promedio_notas,
                'aprobadas_promocionadas': sum(1 for c in cursadas_data if c['situacion'] == 'Promocionado'),
                'a_final': sum(1 for c in cursadas_data if c['situacion'] == 'Final'),
                'regulares': sum(1 for c in cursadas_data if c['situacion'] == 'Regular'),
                'libres': sum(1 for c in cursadas_data if c['situacion'] == 'Libre'),
            },
            'cursadas': cursadas_data
        }


class EstadoAcademicoImprimible:
    def __init__(self, repo: AlumnoRepositorio):
        self.repo = repo

    def ejecutar(self, dni_limpio: str) -> Dict[str, Any]:
        persona, alumno = self.repo.obtener_persona_alumno(dni_limpio)
        cursadas = self.repo.cursadas_con_detalle(alumno).prefetch_related(
            'evaluaciones', 'comision__docentes_asignados__docente__persona')
        return {
            'persona': persona,
            'alumno': alumno,
            'dni_formateado': formatear_dni(persona.dni),
            'cuil_formateado': formatear_cuil(persona.cuil),
            'telefono_formateado': formatear_telefono(persona.telefono),
            'cursadas': cursadas,
            'fecha_emision': datetime.date.today().strftime('%d/%m/%Y')
        }


class RegistrarAlumno:
    """Alta por lotes: validaciones de la tanda y confirmación definitiva (Paso 1 y 2)."""

    def __init__(self, repo: AlumnoRepositorio):
        self.repo = repo

    @staticmethod
    def preparar_datos(cleaned: Dict[str, Any]) -> Dict[str, Any]:
        """Formatea la fecha como string ISO para serialización en sesión."""
        cleaned = dict(cleaned)
        fecha_val = cleaned.get('fecha_nacimiento')
        if isinstance(fecha_val, (datetime.date, datetime.datetime)):
            cleaned['fecha_nacimiento'] = fecha_val.strftime('%Y-%m-%d')
        return cleaned

    @staticmethod
    def validar_lote(matriz, datos: Dict[str, Any]) -> None:
        """Evita repetir DNI/CUIL dentro de la tanda actual de la sesión."""
        dni_nuevo = datos.get('dni')
        cuil_nuevo = datos.get('cuil')
        if matriz.duplicado_en_lote('dni', dni_nuevo):
            raise RegistroDuplicadoError(f"El alumno con DNI {dni_nuevo} ya fue ingresado en esta tanda de carga.")
        if matriz.duplicado_en_lote('cuil', cuil_nuevo):
            raise RegistroDuplicadoError(f"El alumno con CUIL {cuil_nuevo} ya fue ingresado en esta tanda de carga.")

    @staticmethod
    def resumir_errores(form) -> str:
        cant_errores = len(form.errors)
        campos_con_error = [field.label for field in form if field.errors]
        if cant_errores == 1 and campos_con_error:
            return f"Se detectó 1 error en '{campos_con_error[0]}'. Por favor revise el detalle señalado en rojo."
        if campos_con_error:
            lista_nombres = ", ".join(campos_con_error[:3])
            if len(campos_con_error) > 3:
                lista_nombres += f" y {len(campos_con_error) - 3} más"
            return f"Se detectaron {cant_errores} errores en el formulario ({lista_nombres}). Corrija los campos señalados en rojo a continuación."
        return f"Se detectaron {cant_errores} inconsistencias en el formulario. Por favor revise el detalle señalado en rojo."

    @staticmethod
    def matriz_para_vista(alumnos_lista: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        genero_dict = dict(AlumnoCarga.GENERO_CHOICES)
        resultado = []
        for idx, item in enumerate(alumnos_lista):
            copia = item.copy()
            copia['fila_num'] = idx + 1
            copia['fila_index'] = idx
            copia['genero_humano'] = genero_dict.get(item.get('genero', ''), item.get('genero', ''))
            resultado.append(copia)
        return resultado

    def confirmar(self, alumnos_lista: List[Dict[str, Any]]) -> Tuple[int, List[str]]:
        guardados_ok = 0
        errores: List[str] = []

        for datos in alumnos_lista:
            dni_candidato = str(datos.get('dni', '')).strip()
            cuil_candidato = str(datos.get('cuil', '')).strip()

            # Validar duplicados en base de datos
            if self.repo.existe_dni_carga(dni_candidato):
                errores.append(f"DNI {dni_candidato} ya existe en base de datos.")
                continue
            if self.repo.existe_cuil_carga(cuil_candidato):
                errores.append(f"CUIL {cuil_candidato} ya existe en base de datos.")
                continue

            try:
                fecha_obj = datetime.datetime.strptime(str(datos.get('fecha_nacimiento', '')), '%Y-%m-%d').date()
                nuevo = self.repo.crear_carga(dni_candidato, cuil_candidato, fecha_obj, datos)
                self.repo.sincronizar_con_gestion(nuevo)
                guardados_ok += 1
            except Exception as e:
                errores.append(f"Error con DNI {dni_candidato}: {e}")
        return guardados_ok, errores

