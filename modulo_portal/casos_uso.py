"""Armado de la información que consumen los portales de Alumno y Docente."""
from collections import defaultdict
from typing import Any, Dict

from core.excepciones import RegistroNoEncontradoError
from core.formateadores import formatear_cuil, formatear_dni, formatear_telefono
from modulo_base_datos.models import Alumno, Docente


class ArmarPortalAlumno:
    def ejecutar(self, dni: str) -> Dict[str, Any]:
        alumno = Alumno.objects.select_related('persona').filter(persona__dni=dni).first()
        if not alumno:
            raise RegistroNoEncontradoError("Alumno no encontrado.")
        persona = alumno.persona

        cursadas_alumno = alumno.cursadas.select_related(
            'comision__plan_estudio__carrera',
            'comision__plan_estudio__materia',
        ).prefetch_related(
            'evaluaciones',
            'comision__docentes_asignados__docente__persona',
        ).all()

        # Agrupar las cursadas por carrera y dentro por año de carrera
        carreras_agrupadas = {}
        notas_totales = []
        asistencias_totales = []
        total_promocionadas = 0
        total_regulares = 0
        total_finales = 0
        total_libres = 0

        for cursada in cursadas_alumno:
            comision = cursada.comision
            plan = comision.plan_estudio
            carrera = plan.carrera
            materia = plan.materia
            anio = plan.anio_carrera or 1

            codigo_carrera = carrera.codigo_carrera
            if codigo_carrera not in carreras_agrupadas:
                carreras_agrupadas[codigo_carrera] = {
                    'carrera': carrera,
                    'nombre_carrera': carrera.nombre_carrera,
                    'resolucion': carrera.resolucion_vigente or 'Sin resolución',
                    'anios': defaultdict(list),
                }

            # Evaluaciones y notas
            evaluaciones = list(cursada.evaluaciones.all().order_by('fecha', 'codigo_evaluacion'))
            nota_final_obj = None
            evaluaciones_parciales = []

            for evaluacion in evaluaciones:
                if evaluacion.nota is not None:
                    notas_totales.append(float(evaluacion.nota))
                instancia_minuscula = (evaluacion.instancia or '').lower()
                if 'final' in instancia_minuscula:
                    nota_final_obj = evaluacion
                else:
                    evaluaciones_parciales.append(evaluacion)

            # Docentes de la comisión
            docentes_lista = []
            for cd in comision.docentes_asignados.all():
                doc_persona = cd.docente.persona
                docentes_lista.append(f"Prof. {doc_persona.apellido}, {doc_persona.nombre} ({cd.rol})")
            docentes_str = " | ".join(docentes_lista) if docentes_lista else "Docente no asignado"

            # Asistencia
            if cursada.porcentaje_asistencia is not None:
                asistencias_totales.append(float(cursada.porcentaje_asistencia))

            # Conteo de situaciones
            if cursada.situacion_final == 'Promocionado':
                total_promocionadas += 1
            elif cursada.situacion_final == 'Regular':
                total_regulares += 1
            elif cursada.situacion_final == 'Final':
                total_finales += 1
            elif cursada.situacion_final == 'Libre':
                total_libres += 1

            cursada_info = {
                'cursada': cursada,
                'comision': comision,
                'materia': materia,
                'plan': plan,
                'anio_lectivo': comision.anio_lectivo,
                'turno': comision.turno,
                'division': comision.division,
                'cuatrimestre': comision.cuatrimestre,
                'docentes_str': docentes_str,
                'asistencia': f"{float(cursada.porcentaje_asistencia):.0f}%" if cursada.porcentaje_asistencia is not None else "Sin registro",
                'asistencia_val': float(cursada.porcentaje_asistencia) if cursada.porcentaje_asistencia is not None else None,
                'situacion': cursada.situacion_final,
                'evaluaciones_parciales': evaluaciones_parciales,
                'nota_final': nota_final_obj.nota if (nota_final_obj and nota_final_obj.nota is not None) else None,
            }

            carreras_agrupadas[codigo_carrera]['anios'][anio].append(cursada_info)

        # Agrupar por año y ordenar para la vista
        carreras_estructuradas = []
        for codigo_carrera, datos_carrera in carreras_agrupadas.items():
            anios_ordenados = []
            for anio_num in sorted(datos_carrera['anios'].keys()):
                anios_ordenados.append({
                    'numero': anio_num,
                    'titulo': f"{anio_num}° Año",
                    'materias': sorted(datos_carrera['anios'][anio_num], key=lambda x: x['materia'].nombre_materia),
                })
            carreras_estructuradas.append({
                'carrera': datos_carrera['carrera'],
                'nombre_carrera': datos_carrera['nombre_carrera'],
                'resolucion': datos_carrera['resolucion'],
                'anios': anios_ordenados,
                'total_materias_carrera': sum(len(a['materias']) for a in anios_ordenados),
            })

        # Estadísticas globales
        promedio_general = round(sum(notas_totales) / len(notas_totales), 2) if notas_totales else None
        asistencia_promedio = round(sum(asistencias_totales) / len(asistencias_totales), 1) if asistencias_totales else None

        return {
            'alumno': alumno,
            'persona': persona,
            'dni_formateado': formatear_dni(persona.dni),
            'cuil_formateado': formatear_cuil(persona.cuil),
            'telefono_formateado': formatear_telefono(persona.telefono),
            'carreras': carreras_estructuradas,
            'total_materias_cursadas': cursadas_alumno.count(),
            'promedio_general': promedio_general,
            'asistencia_promedio': asistencia_promedio,
            'total_promocionadas': total_promocionadas,
            'total_regulares': total_regulares,
            'total_finales': total_finales,
            'total_libres': total_libres,
        }


class ArmarPortalDocente:
    def ejecutar(self, dni: str) -> Dict[str, Any]:
        docente = Docente.objects.select_related('persona').filter(persona__dni=dni).first()
        if not docente:
            raise RegistroNoEncontradoError("Docente no encontrado.")
        persona = docente.persona

        asignaciones_docente = docente.comisiones_asignadas.select_related(
            'comision__plan_estudio__carrera',
            'comision__plan_estudio__materia',
        ).prefetch_related(
            'comision__cursadas',
        ).all()

        # Agrupar comisiones por carrera y año
        carreras_agrupadas = {}
        total_estudiantes = 0
        codigos_comisiones = set()

        for asignacion in asignaciones_docente:
            comision = asignacion.comision
            plan = comision.plan_estudio
            carrera = plan.carrera
            materia = plan.materia
            anio = plan.anio_carrera or 1

            codigo_carrera = carrera.codigo_carrera
            if codigo_carrera not in carreras_agrupadas:
                carreras_agrupadas[codigo_carrera] = {
                    'carrera': carrera,
                    'nombre_carrera': carrera.nombre_carrera,
                    'resolucion': carrera.resolucion_vigente or 'Sin resolución',
                    'anios': defaultdict(list),
                }

            cant_alumnos = comision.cursadas.count()
            total_estudiantes += cant_alumnos
            codigos_comisiones.add(comision.codigo_comision)

            item = {
                'materia': materia,
                'plan': plan,
                'comision': comision,
                'rol': asignacion.rol,
                'anio_lectivo': comision.anio_lectivo,
                'turno': comision.turno,
                'division': comision.division,
                'cuatrimestre': comision.cuatrimestre,
                'hs_semanales': plan.carga_horaria_semanal,
                'hs_anuales': plan.carga_horaria_anual,
                'cantidad_estudiantes': cant_alumnos,
            }
            carreras_agrupadas[codigo_carrera]['anios'][anio].append(item)

        # Agrupar por año y ordenar para la vista
        carreras_estructuradas = []
        for codigo_carrera, datos_carrera in carreras_agrupadas.items():
            anios_ordenados = []
            for anio_num in sorted(datos_carrera['anios'].keys()):
                anios_ordenados.append({
                    'numero': anio_num,
                    'titulo': f"{anio_num}° Año",
                    'comisiones': sorted(datos_carrera['anios'][anio_num], key=lambda x: x['materia'].nombre_materia),
                })
            carreras_estructuradas.append({
                'carrera': datos_carrera['carrera'],
                'nombre_carrera': datos_carrera['nombre_carrera'],
                'resolucion': datos_carrera['resolucion'],
                'anios': anios_ordenados,
                'total_comisiones_carrera': sum(len(a['comisiones']) for a in anios_ordenados),
            })

        return {
            'docente': docente,
            'persona': persona,
            'dni_formateado': formatear_dni(persona.dni),
            'cuil_formateado': formatear_cuil(persona.cuil),
            'telefono_formateado': formatear_telefono(persona.telefono),
            'carreras': carreras_estructuradas,
            'total_asignaturas': len({asig.comision.plan_estudio.materia.codigo_materia for asig in asignaciones_docente}),
            'total_comisiones': len(codigos_comisiones),
            'total_estudiantes': total_estudiantes,
        }

