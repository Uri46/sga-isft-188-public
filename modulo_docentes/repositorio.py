"""Acceso a base de datos de docentes."""
import datetime
from typing import Any, Dict, Optional

from django.db.models import Q

from core.excepciones import RegistroNoEncontradoError
from .dominio import ComisionDocente, Docente, Persona


class DocenteRepositorio:
    ORDEN_MAP = {
        'apellido': ['persona__apellido', 'persona__nombre'],
        'nombre': ['persona__nombre', 'persona__apellido'],
        'dni': ['persona__dni'],
        'titulo': ['titulo_mn', 'persona__apellido'],
        'localidad': ['persona__localidad', 'persona__apellido'],
        'nacionalidad': ['persona__nacionalidad', 'persona__apellido'],
        'edad_asc': ['-persona__fecha_nacimiento', 'persona__apellido'],
        'edad_desc': ['persona__fecha_nacimiento', 'persona__apellido'],
    }

    def buscar(self, query: str, genero: str, nacionalidad: str, localidad: str, orden: str):
        docentes = Docente.objects.select_related('persona').all()

        if query:
            query_clean = query.replace('.', '').replace(' ', '').replace('-', '').replace(',', '')
            filtros_q = (
                Q(persona__nombre__icontains=query) |
                Q(persona__apellido__icontains=query) |
                Q(persona__localidad__icontains=query) |
                Q(titulo_mn__icontains=query)
            )
            if query_clean.isdigit() or any(c.isdigit() for c in query):
                filtros_q |= Q(persona__dni__icontains=query) | Q(persona__dni__icontains=query_clean)
                filtros_q |= Q(persona__cuil__icontains=query) | Q(persona__cuil__icontains=query_clean)
            docentes = docentes.filter(filtros_q).distinct()

        if genero:
            docentes = docentes.filter(persona__identidad=genero)
        if nacionalidad:
            docentes = docentes.filter(persona__nacionalidad__iexact=nacionalidad)
        if localidad:
            docentes = docentes.filter(persona__localidad__iexact=localidad)

        criterio = self.ORDEN_MAP.get(orden, ['persona__apellido', 'persona__nombre'])
        return docentes.order_by(*criterio)

    def nacionalidades(self):
        return list(Persona.objects.exclude(nacionalidad__isnull=True).exclude(nacionalidad='')
                    .values_list('nacionalidad', flat=True).distinct().order_by('nacionalidad'))

    def localidades(self):
        return list(Persona.objects.exclude(localidad__isnull=True).exclude(localidad='')
                    .values_list('localidad', flat=True).distinct().order_by('localidad'))

    def obtener_por_dni(self, dni: str) -> Docente:
        persona = Persona.objects.filter(dni=dni).first()
        docente = Docente.objects.filter(persona=persona).first() if persona else None
        if not docente:
            raise RegistroNoEncontradoError("Docente no encontrado.")
        return docente

    def comisiones_con_detalle(self, docente: Docente):
        return ComisionDocente.objects.filter(docente=docente).select_related(
            'comision__plan_estudio__carrera',
            'comision__plan_estudio__materia'
        )

    def existe_dni(self, dni: str) -> bool:
        return Persona.objects.filter(dni=dni).exists()

    def existe_cuil(self, cuil: str) -> bool:
        return Persona.objects.filter(cuil=cuil).exists()

    def crear(self, dni: str, cuil: Optional[str], datos: Dict[str, Any],
              fecha_nacimiento: Optional[datetime.date]) -> Docente:
        persona = Persona.objects.create(
            dni=dni,
            cuil=cuil or None,
            nombre=datos.get('nombre', '').strip(),
            apellido=datos.get('apellido', '').strip(),
            fecha_nacimiento=fecha_nacimiento,
            identidad=datos.get('identidad', 'N'),
            nacionalidad=datos.get('nacionalidad', 'Argentina') or 'Argentina',
            localidad=datos.get('localidad', '') or None,
            domicilio=datos.get('domicilio', '') or None,
            telefono=datos.get('telefono', '') or None,
            mail=datos.get('mail', '') or None,
        )
        return Docente.objects.create(
            persona=persona,
            titulo_mn=datos.get('titulo_mn', '').strip() or None
        )

