"""Acceso a la base de datos de carreras, materias y planes de estudio."""
from typing import Iterable, List

from django.db import transaction
from django.db.models import Count, Max, Min, Q, Sum

from core.excepciones import RegistroNoEncontradoError
from .dominio import Carrera, Comision, Materia, MateriaPlanDatos, PlanEstudio


class CarreraRepositorio:
    def listar_anotadas(self, query: str, con_materias: str, orden: str):
        carreras = Carrera.objects.annotate(
            total_materias=Count('planes_estudio', distinct=True),
            anio_min=Min('planes_estudio__anio_carrera'),
            anio_max=Max('planes_estudio__anio_carrera'),
            total_horas_anuales=Sum('planes_estudio__carga_horaria_anual')
        )
        if query:
            carreras = carreras.filter(
                Q(nombre_carrera__icontains=query) |
                Q(codigo_carrera__icontains=query) |
                Q(resolucion_vigente__icontains=query) |
                Q(resolucion_anterior__icontains=query)
            )
        if con_materias == 'con_materias':
            carreras = carreras.filter(total_materias__gt=0)
        elif con_materias == 'sin_materias':
            carreras = carreras.filter(total_materias=0)

        orden_map = {
            'nombre': ['nombre_carrera'],
            'codigo': ['codigo_carrera'],
            'materias_desc': ['-total_materias', 'nombre_carrera'],
            'materias_asc': ['total_materias', 'nombre_carrera'],
        }
        return carreras.order_by(*orden_map.get(orden, ['nombre_carrera']))

    def obtener(self, codigo_carrera: str) -> Carrera:
        carrera = Carrera.objects.filter(codigo_carrera=codigo_carrera).first()
        if not carrera:
            raise RegistroNoEncontradoError("Carrera no encontrada.")
        return carrera

    def planes_de_carrera(self, carrera: Carrera):
        return PlanEstudio.objects.filter(carrera=carrera).select_related('materia').order_by(
            'anio_carrera', 'materia__nombre_materia')

    def obtener_plan(self, id_plan: int, carrera: Carrera) -> PlanEstudio:
        plan = PlanEstudio.objects.filter(id_plan=id_plan, carrera=carrera).first()
        if not plan:
            raise RegistroNoEncontradoError("Materia del plan no encontrada.")
        return plan

    def existe_materia_en_plan(self, carrera: Carrera, codigo_materia: str) -> bool:
        return PlanEstudio.objects.filter(carrera=carrera, materia__codigo_materia=codigo_materia).exists()

    def plan_tiene_cursadas(self, plan: PlanEstudio) -> bool:
        return Comision.objects.filter(plan_estudio=plan, cursadas__isnull=False).exists()

    # ---- Escrituras ----
    def crear_carrera_con_plan(self, datos: dict, materias: Iterable[MateriaPlanDatos]) -> Carrera:
        with transaction.atomic():
            carrera = Carrera.objects.create(
                codigo_carrera=datos['codigo_carrera'],
                nombre_carrera=datos['nombre_carrera'],
                resolucion_vigente=datos.get('resolucion_vigente') or None,
                resolucion_anterior=datos.get('resolucion_anterior') or None,
            )
            for m in materias:
                materia, _ = Materia.objects.get_or_create(
                    codigo_materia=m.codigo_materia,
                    defaults={'nombre_materia': m.nombre_materia}
                )
                PlanEstudio.objects.create(
                    carrera=carrera,
                    materia=materia,
                    anio_carrera=m.anio_carrera,
                    modalidad=m.modalidad,
                    carga_horaria_semanal=m.carga_horaria_semanal,
                    carga_horaria_anual=m.carga_horaria_anual,
                    correlatividades=m.correlatividades,
                )
        return carrera

    def eliminar_carrera(self, carrera: Carrera) -> None:
        with transaction.atomic():
            carrera.delete()

    def agregar_materia(self, carrera: Carrera, m: MateriaPlanDatos) -> PlanEstudio:
        with transaction.atomic():
            materia, created = Materia.objects.get_or_create(
                codigo_materia=m.codigo_materia,
                defaults={'nombre_materia': m.nombre_materia}
            )
            if not created and materia.nombre_materia != m.nombre_materia:
                materia.nombre_materia = m.nombre_materia
                materia.save()
            return PlanEstudio.objects.create(
                carrera=carrera,
                materia=materia,
                anio_carrera=m.anio_carrera,
                modalidad=m.modalidad,
                carga_horaria_semanal=m.carga_horaria_semanal,
                carga_horaria_anual=m.carga_horaria_anual,
                correlatividades=m.correlatividades,
            )

    def actualizar_materia(self, plan: PlanEstudio, nombre_materia: str, anio_carrera, modalidad,
                           carga_semanal, carga_anual, correlatividades) -> PlanEstudio:
        with transaction.atomic():
            plan.anio_carrera = anio_carrera
            plan.modalidad = modalidad
            plan.carga_horaria_semanal = carga_semanal
            plan.carga_horaria_anual = carga_anual
            plan.correlatividades = correlatividades
            plan.save()
            if plan.materia.nombre_materia != nombre_materia:
                plan.materia.nombre_materia = nombre_materia
                plan.materia.save()
        return plan

    def eliminar_plan(self, plan: PlanEstudio) -> None:
        with transaction.atomic():
            Comision.objects.filter(plan_estudio=plan).delete()
            plan.delete()

