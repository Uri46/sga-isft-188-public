"""Entidad Carrera y reglas puras de su plan de estudios."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from modulo_base_datos.models import Carrera, Comision, Materia, PlanEstudio  # noqa: F401  (re-export)

CLAVE_SESION_CARRERA = 'carrera_borrador_datos'
CLAVE_SESION_MATRIZ = 'carrera_borrador_materias'


@dataclass
class MateriaPlanDatos:
    codigo_materia: str
    nombre_materia: str
    anio_carrera: int
    modalidad: str
    carga_horaria_semanal: Decimal
    carga_horaria_anual: int
    correlatividades: str = ''


def parsear_decimal(texto: Optional[str], por_defecto: Decimal = Decimal('0.0')) -> Decimal:
    try:
        return Decimal(texto.replace(',', '.')) if texto else Decimal('0.0')
    except Exception:
        return por_defecto


def calcular_carga_anual(carga_semanal: Decimal, modalidad: Optional[str]) -> int:
    """Horas anuales = horas semanales x semanas (16 cuatrimestral, 32 anual)."""
    semanas = 16 if 'cuatrimestre' in (modalidad or '').lower() else 32
    return int(round(float(carga_semanal) * semanas))

