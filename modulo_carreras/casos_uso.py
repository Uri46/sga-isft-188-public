"""Reglas de negocio de carreras y planes de estudio."""
from decimal import Decimal
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from core.excepciones import ReglaNegocioError, SGAError, ValidacionError, RegistroDuplicadoError
from .dominio import (
    Carrera, MateriaPlanDatos, PlanEstudio, calcular_carga_anual, parsear_decimal,
)
from .repositorio import CarreraRepositorio


def normalizar_page_size(valor, por_defecto: int = 10) -> int:
    try:
        page_size = int(valor)
        return page_size if page_size in [10, 25, 50, 100] else por_defecto
    except (ValueError, TypeError):
        return por_defecto


def _agrupar_por_anio(planes, convertir):
    anios_dict: Dict[int, List[Any]] = {}
    for p in planes:
        anios_dict.setdefault(p.anio_carrera or 1, []).append(convertir(p))
    return anios_dict


class ListarCarreras:
    def __init__(self, repo: CarreraRepositorio):
        self.repo = repo

    def ejecutar(self, query: str, con_materias: str, orden: str):
        return self.repo.listar_anotadas(query, con_materias, orden)


class DetalleCarrera:
    def __init__(self, repo: CarreraRepositorio):
        self.repo = repo

    def ejecutar(self, codigo_carrera: str) -> Dict[str, Any]:
        """Datos detallados de una carrera y su plan agrupado por año (Expediente de Carrera)."""
        carrera = self.repo.obtener(codigo_carrera)
        planes = self.repo.planes_de_carrera(carrera)

        anios_dict: Dict[int, List[Dict[str, Any]]] = {}
        total_horas_anuales = 0
        total_horas_semanales = Decimal('0.0')

        for p in planes:
            anio = p.anio_carrera or 1
            anios_dict.setdefault(anio, [])
            hs_anuales = p.carga_horaria_anual or 0
            hs_semanales = p.carga_horaria_semanal or Decimal('0.0')
            total_horas_anuales += hs_anuales
            total_horas_semanales += hs_semanales
            anios_dict[anio].append({
                'id_plan': p.id_plan,
                'codigo_materia': p.materia.codigo_materia,
                'nombre_materia': p.materia.nombre_materia,
                'modalidad': p.modalidad or 'Anual',
                'carga_horaria_anual': hs_anuales,
                'carga_horaria_semanal': float(hs_semanales),
                'correlatividades': p.correlatividades or '',
            })

        anios_lista = [{
            'numero': anio,
            'nombre': f"{anio}° Año",
            'materias': anios_dict[anio],
            'total_materias_anio': len(anios_dict[anio]),
        } for anio in sorted(anios_dict.keys())]

        return {
            'success': True,
            'codigo_carrera': carrera.codigo_carrera,
            'nombre_carrera': carrera.nombre_carrera,
            'resolucion_vigente': carrera.resolucion_vigente or 'Sin resolución registrada',
            'resolucion_anterior': carrera.resolucion_anterior or 'Ninguna',
            'total_materias': planes.count(),
            'total_horas_anuales': total_horas_anuales,
            'total_horas_semanales': float(total_horas_semanales),
            'anios': anios_lista,
        }


class PlanImprimible:
    def __init__(self, repo: CarreraRepositorio):
        self.repo = repo

    def ejecutar(self, codigo_carrera: str) -> Dict[str, Any]:
        carrera = self.repo.obtener(codigo_carrera)
        planes = self.repo.planes_de_carrera(carrera)

        anios_dict: Dict[int, List[PlanEstudio]] = {}
        total_horas_anuales = 0
        total_horas_semanales = Decimal('0.0')
        for p in planes:
            anios_dict.setdefault(p.anio_carrera or 1, []).append(p)
            total_horas_anuales += (p.carga_horaria_anual or 0)
            total_horas_semanales += (p.carga_horaria_semanal or Decimal('0.0'))

        anios_lista = [{
            'numero': anio,
            'nombre': f"{anio}° Año",
            'planes': anios_dict[anio],
            'total_materias': len(anios_dict[anio]),
        } for anio in sorted(anios_dict.keys())]

        return {
            'carrera': carrera,
            'anios': anios_lista,
            'total_materias': planes.count(),
            'total_horas_anuales': total_horas_anuales,
            'total_horas_semanales': total_horas_semanales,
        }


class RegistrarCarrera:
    """Paso 2 del alta: valida la matriz de materias y guarda carrera + plan de forma atómica."""

    def __init__(self, repo: CarreraRepositorio):
        self.repo = repo

    @staticmethod
    def procesar_matriz(codigos: Sequence[str], nombres: Sequence[str], anios: Sequence[str],
                        modalidades: Sequence[str], hs_semanales: Sequence[str],
                        correlatividades: Sequence[str]) -> Tuple[List[MateriaPlanDatos], List[str]]:
        materias: List[MateriaPlanDatos] = []
        errores: List[str] = []

        for i in range(len(codigos)):
            c_cod = codigos[i].strip().upper()
            c_nom = nombres[i].strip() if i < len(nombres) else ''
            c_anio_raw = anios[i].strip() if i < len(anios) else '1'
            c_mod = modalidades[i].strip() if i < len(modalidades) else 'Anual'
            c_sem_raw = hs_semanales[i].strip() if i < len(hs_semanales) else '0'
            c_corr = correlatividades[i].strip() if i < len(correlatividades) else ''

            if not c_cod and not c_nom:
                continue  # Fila vacía ignorada
            if not c_cod:
                errores.append(f"La materia en fila {i+1} no tiene código.")
                continue
            if not c_nom:
                errores.append(f"La materia con código '{c_cod}' no tiene nombre.")
                continue

            try:
                c_anio = int(c_anio_raw)
            except ValueError:
                c_anio = 1

            c_sem = parsear_decimal(c_sem_raw)
            materias.append(MateriaPlanDatos(
                codigo_materia=c_cod,
                nombre_materia=c_nom,
                anio_carrera=c_anio,
                modalidad=c_mod or 'Anual',
                carga_horaria_semanal=c_sem,
                carga_horaria_anual=calcular_carga_anual(c_sem, c_mod),
                correlatividades=c_corr,
            ))

        if not materias:
            errores.append("Debés ingresar al menos una materia en el plan de estudios.")
        return materias, errores

    def ejecutar(self, carrera_data: Mapping[str, Any], materias: Sequence[MateriaPlanDatos]) -> Carrera:
        return self.repo.crear_carrera_con_plan(dict(carrera_data), materias)


class EliminarCarrera:
    def __init__(self, repo: CarreraRepositorio):
        self.repo = repo

    def ejecutar(self, codigo_carrera: str) -> str:
        carrera = self.repo.obtener(codigo_carrera)
        nombre = carrera.nombre_carrera
        try:
            self.repo.eliminar_carrera(carrera)
        except Exception as ex:
            raise SGAError(f"No se pudo eliminar la carrera: {str(ex)}")
        return f"La carrera '{nombre}' y su plan de estudios han sido eliminados correctamente."


class GestionarMateriasPlan:
    def __init__(self, repo: CarreraRepositorio):
        self.repo = repo

    def agregar(self, codigo_carrera: str, datos: Mapping[str, str]) -> Tuple[PlanEstudio, str]:
        carrera = self.repo.obtener(codigo_carrera)

        codigo_materia = datos.get('codigo_materia', '').strip().upper()
        nombre_materia = datos.get('nombre_materia', '').strip()
        anio_raw = datos.get('anio_carrera', '1').strip()
        modalidad = datos.get('modalidad', 'Anual').strip()
        hs_semanales_raw = datos.get('carga_horaria_semanal', '0').strip()
        correlatividades = datos.get('correlatividades', '').strip()

        if not codigo_materia:
            raise ValidacionError('El código de la materia es obligatorio.')
        if not nombre_materia:
            raise ValidacionError('El nombre de la materia es obligatorio.')

        try:
            anio_carrera = int(anio_raw)
            if anio_carrera < 1 or anio_carrera > 10:
                anio_carrera = 1
        except ValueError:
            anio_carrera = 1

        carga_semanal = parsear_decimal(hs_semanales_raw)

        if self.repo.existe_materia_en_plan(carrera, codigo_materia):
            raise RegistroDuplicadoError(
                f"La materia con código '{codigo_materia}' ya existe en el plan de estudios de esta carrera."
            )

        try:
            plan = self.repo.agregar_materia(carrera, MateriaPlanDatos(
                codigo_materia=codigo_materia,
                nombre_materia=nombre_materia,
                anio_carrera=anio_carrera,
                modalidad=modalidad or 'Anual',
                carga_horaria_semanal=carga_semanal,
                carga_horaria_anual=calcular_carga_anual(carga_semanal, modalidad),
                correlatividades=correlatividades,
            ))
        except Exception as ex:
            raise SGAError(f"Error al agregar materia: {str(ex)}")
        return plan, f"Materia '{nombre_materia}' incorporada exitosamente al {anio_carrera}° año."

    def editar(self, codigo_carrera: str, id_plan: int, datos: Mapping[str, str]) -> Tuple[PlanEstudio, str]:
        carrera = self.repo.obtener(codigo_carrera)
        plan = self.repo.obtener_plan(id_plan, carrera)

        nombre_materia = datos.get('nombre_materia', '').strip()
        anio_raw = datos.get('anio_carrera', str(plan.anio_carrera)).strip()
        modalidad = datos.get('modalidad', plan.modalidad or 'Anual').strip()
        hs_semanales_raw = datos.get('carga_horaria_semanal', str(plan.carga_horaria_semanal or '0')).strip()
        correlatividades = datos.get('correlatividades', '').strip()

        if not nombre_materia:
            raise ValidacionError('El nombre de la materia no puede quedar vacío.')

        try:
            anio_carrera = int(anio_raw)
            if anio_carrera < 1 or anio_carrera > 10:
                anio_carrera = plan.anio_carrera
        except ValueError:
            anio_carrera = plan.anio_carrera

        carga_semanal = parsear_decimal(hs_semanales_raw, por_defecto=plan.carga_horaria_semanal or Decimal('0.0'))

        try:
            self.repo.actualizar_materia(
                plan, nombre_materia, anio_carrera, modalidad or 'Anual', carga_semanal,
                calcular_carga_anual(carga_semanal, modalidad), correlatividades,
            )
        except Exception as ex:
            raise SGAError(f"Error al editar materia: {str(ex)}")
        return plan, f"Materia '{nombre_materia}' actualizada correctamente."

    def eliminar(self, codigo_carrera: str, id_plan: int) -> str:
        carrera = self.repo.obtener(codigo_carrera)
        plan = self.repo.obtener_plan(id_plan, carrera)

        if self.repo.plan_tiene_cursadas(plan):
            raise ReglaNegocioError(
                f"No se puede eliminar '{plan.materia.nombre_materia}' porque tiene comisiones "
                f"con cursadas de estudiantes o notas registradas."
            )
        nombre_mat = plan.materia.nombre_materia
        try:
            self.repo.eliminar_plan(plan)
        except Exception as ex:
            raise SGAError(f"Error al eliminar la materia: {str(ex)}")
        return f"La materia '{nombre_mat}' fue eliminada del plan de estudios exitosamente."

