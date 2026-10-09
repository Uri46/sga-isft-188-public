"""Acceso a base de datos de alumnos (buscador institucional y carga de alumnos)."""
import datetime
from typing import Any, Dict, List

from django.db.models import Q

from core.excepciones import RegistroNoEncontradoError
from modulo_base_datos.models import (
    Alumno as AlumnoPerfil, Carrera, Cursada, Persona,
)
from .dominio import Alumno as AlumnoCarga


class AlumnoRepositorio:
    # ------------------------------------------------------------------ Buscador
    def buscar(self, query: str, plan_id: str, carrera_nombre: str, genero: str,
               nacionalidad: str, anio: str, localidad: str):
        alumnos = AlumnoPerfil.objects.select_related('persona').prefetch_related(
            'cursadas__comision__plan_estudio__carrera',
            'cursadas__comision__plan_estudio__materia',
            'cursadas__evaluaciones'
        ).all()

        # Busqueda flexible por DNI (limpio/con puntos), CUIL, Nombre, Apellido, Legajo o Localidad
        if query:
            query_clean = query.replace('.', '').replace(' ', '').replace('-', '').replace(',', '')
            filtros_q = (
                Q(persona__nombre__icontains=query) |
                Q(persona__apellido__icontains=query) |
                Q(persona__localidad__icontains=query) |
                Q(legajo__icontains=query) |
                Q(legajo__icontains=query_clean)
            )
            if query_clean.isdigit() or any(c.isdigit() for c in query):
                filtros_q |= Q(persona__dni__icontains=query) | Q(persona__dni__icontains=query_clean)
                filtros_q |= (
                    (Q(persona__cuil__icontains=query) | Q(persona__cuil__icontains=query_clean)) &
                    ~Q(persona__cuil__isnull=True) &
                    ~Q(persona__cuil__exact='')
                )
            alumnos = alumnos.filter(filtros_q).distinct()

        # Filtro por Plan de Estudio o Carrera
        if plan_id:
            alumnos = alumnos.filter(cursadas__comision__plan_estudio__carrera__codigo_carrera=plan_id).distinct()
        elif carrera_nombre:
            alumnos = alumnos.filter(cursadas__comision__plan_estudio__carrera__nombre_carrera=carrera_nombre).distinct()

        if genero in ['M', 'F', 'I', 'N']:
            alumnos = alumnos.filter(persona__identidad=genero)
        if nacionalidad:
            alumnos = alumnos.filter(persona__nacionalidad__iexact=nacionalidad)
        if anio and anio.isdigit():
            alumnos = alumnos.filter(cursadas__comision__plan_estudio__anio_carrera=int(anio)).distinct()
        if localidad:
            alumnos = alumnos.filter(persona__localidad__iexact=localidad)
        return alumnos

    def resolver_carrera_legacy(self, carrera_legacy: str):
        """Compatibilidad con el parámetro 'carrera' previo: devuelve (plan_id, carrera_nombre)."""
        carrera = Carrera.objects.filter(codigo_carrera=carrera_legacy).first()
        if carrera:
            return carrera_legacy, carrera.nombre_carrera
        return '', carrera_legacy

    def opciones_filtros(self) -> Dict[str, Any]:
        return {
            'carreras_unicas': list(Carrera.objects.values_list('nombre_carrera', flat=True).distinct().order_by('nombre_carrera')),
            'carreras_planes': list(Carrera.objects.values('codigo_carrera', 'nombre_carrera', 'resolucion_vigente').order_by('nombre_carrera', 'resolucion_vigente')),
            'carreras': Carrera.objects.all().order_by('nombre_carrera', 'resolucion_vigente'),
            'localidades': list(Persona.objects.exclude(localidad__isnull=True).exclude(localidad__exact='').values_list('localidad', flat=True).distinct().order_by('localidad')),
            'nacionalidades': list(Persona.objects.exclude(nacionalidad__isnull=True).exclude(nacionalidad__exact='').values_list('nacionalidad', flat=True).distinct().order_by('nacionalidad')),
        }

    # ------------------------------------------------------------------ Consultas puntuales
    def obtener_persona_alumno(self, dni_limpio: str):
        persona = Persona.objects.filter(dni=dni_limpio).first()
        alumno = AlumnoPerfil.objects.filter(persona=persona).first() if persona else None
        if not alumno:
            raise RegistroNoEncontradoError("Alumno no encontrado.")
        return persona, alumno

    def cursadas_con_detalle(self, alumno: AlumnoPerfil):
        return Cursada.objects.filter(alumno=alumno).select_related(
            'comision__plan_estudio__carrera',
            'comision__plan_estudio__materia'
        )

    # ------------------------------------------------------------------ Carga de alumnos
    def existe_dni_carga(self, dni: str) -> bool:
        return AlumnoCarga.objects.filter(dni=dni).exists()

    def existe_cuil_carga(self, cuil: str) -> bool:
        return AlumnoCarga.objects.filter(cuil=cuil).exists()

    def crear_carga(self, dni: str, cuil: str, fecha_nacimiento: datetime.date, datos: Dict[str, Any]) -> AlumnoCarga:
        nuevo = AlumnoCarga(
            dni=dni,
            cuil=cuil,
            nombre=str(datos.get('nombre', '')),
            apellido=str(datos.get('apellido', '')),
            fecha_nacimiento=fecha_nacimiento,
            email=str(datos.get('email', '')),
            telefono=str(datos.get('telefono', '')),
            direccion=str(datos.get('direccion', '')),
            localidad=str(datos.get('localidad', 'General Rodríguez')),
            genero=str(datos.get('genero', 'N')),
            nacionalidad=str(datos.get('nacionalidad', 'Argentina')),
        )
        nuevo.save()
        return nuevo

    def sincronizar_con_gestion(self, alumno: AlumnoCarga) -> None:
        """Persistencia en los modelos principales de gestión (Persona + perfil de Alumno)."""
        try:
            persona, _ = Persona.objects.update_or_create(
                dni=alumno.dni,
                defaults={
                    'cuil': alumno.cuil,
                    'nombre': alumno.nombre,
                    'apellido': alumno.apellido,
                    'domicilio': alumno.direccion,
                    'localidad': alumno.localidad,
                    'telefono': alumno.telefono,
                    'mail': alumno.email,
                    'nacionalidad': alumno.nacionalidad,
                    'fecha_nacimiento': alumno.fecha_nacimiento,
                    'identidad': alumno.genero,
                }
            )
            AlumnoPerfil.objects.get_or_create(
                persona=persona,
                defaults={'legajo': f"LEG-{alumno.dni}"}
            )
        except Exception:
            pass

