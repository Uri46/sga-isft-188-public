"""Comando de sembrado de datos de demostración 100% sintéticos para el SGA (ISFT N° 188).

Genera:
1. Catálogo oficial de Carreras, Materias y Planes de Estudio.
2. Comisiones académicas para el ciclo lectivo actual.
3. Docentes ficticios con asignaciones a comisiones.
4. Alumnos ficticios con cursadas y evaluaciones (notas de parciales y finales).

Todos los nombres, DNI, CUIL, teléfonos y direcciones son generados sintéticamente
y no corresponden a personas reales.
"""

import datetime
import random
from django.core.management.base import BaseCommand
from django.db import transaction
from modulo_base_datos.models import (
    Persona, Alumno, Docente, Carrera, Materia, PlanEstudio,
    Comision, ComisionDocente, Cursada, Evaluacion
)
from modulo_base_datos.catalogo_planes import (
    CATALOGO_CARRERAS, CATALOGO_MATERIAS, CATALOGO_PLANES
)
from core.validaciones import calcular_digito_cuil

# Nombres y apellidos comunes de Argentina para combinatoria sintética
NOMBRES_MASCULINOS = [
    "Santiago", "Mateo", "Joaquín", "Lucas", "Agustín", "Nicolás", "Tomás", "Facundo",
    "Ignacio", "Martín", "Gonzalo", "Diego", "Julián", "Sebastián", "Federico", "Lautaro",
    "Ezequiel", "Maximiliano", "Alejandro", "Leonardo"
]

NOMBRES_FEMENINOS = [
    "Sofía", "Valentina", "Martina", "Camila", "Lucía", "Catalina", "Florencia", "Micaela",
    "Julieta", "Milagros", "Abril", "Delfina", "Antonella", "Belén", "Rocío", "Paula",
    "Daniela", "Mariana", "Victoria", "Carolina"
]

APELLIDOS = [
    "González", "Rodríguez", "López", "Fernández", "García", "Pérez", "Martínez", "Romero",
    "Sánchez", "Díaz", "Torres", "Álvarez", "Ruiz", "Ramírez", "Flores", "Acosta",
    "Benítez", "Medina", "Herrera", "Suárez", "Castro", "Giménez", "Gutiérrez", "Pereyra",
    "Ríos", "Molina", "Silva", "Morales", "Ortiz", "Navarro"
]

LOCALIDADES = [
    "General Rodríguez", "Moreno", "Luján", "Pilar", "Mercedes", "San Miguel", "Marcos Paz", "Merlo"
]

CALLES = [
    "Av. San Martín", "Belgrano", "Rivadavia", "Sarmiento", "Mitre", "España", "Moreno",
    "Urquiza", "25 de Mayo", "9 de Julio", "Alvear", "Pellegrini", "Alsina", "Las Heras"
]


def generar_cuil_sintetico(dni: str, genero: str) -> str:
    """Calcula un CUIL válido por módulo 11 para un DNI sintético."""
    prefijo = "27" if genero == "F" else "20"
    base10 = f"{prefijo}{dni.zfill(8)}"
    digito = calcular_digito_cuil(base10 + "0")
    if digito == 9 and prefijo == "20":
        prefijo = "23"
        base10 = f"{prefijo}{dni.zfill(8)}"
        digito = calcular_digito_cuil(base10 + "0")
    elif digito == 4 and prefijo == "27":
        prefijo = "23"
        base10 = f"{prefijo}{dni.zfill(8)}"
        digito = calcular_digito_cuil(base10 + "0")
    return f"{base10[:2]}{dni.zfill(8)}{digito}"


class Command(BaseCommand):
    help = 'Poblar la base de datos con catálogo académico y datos demostrativos 100% ficticios.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--alumnos',
            type=int,
            default=40,
            help='Cantidad de alumnos sintéticos a generar (por defecto 40)'
        )
        parser.add_argument(
            '--docentes',
            type=int,
            default=15,
            help='Cantidad de docentes sintéticos a generar (por defecto 15)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        cant_alumnos = options['alumnos']
        cant_docentes = options['docentes']

        self.stdout.write(self.style.NOTICE("Iniciando sembrado de datos sintéticos..."))

        # 1. Purgar datos existentes para garantizar consistencia limpia
        self.stdout.write("Limpiando tablas de demostración previas...")
        Evaluacion.objects.all().delete()
        Cursada.objects.all().delete()
        ComisionDocente.objects.all().delete()
        Comision.objects.all().delete()
        PlanEstudio.objects.all().delete()
        Materia.objects.all().delete()
        Docente.objects.all().delete()
        Alumno.objects.all().delete()
        Persona.objects.all().delete()
        Carrera.objects.all().delete()

        # 2. Cargar Catálogo Académico (Carreras, Materias, Planes de Estudio)
        self.stdout.write("Cargando catálogo oficial de Carreras, Materias y Planes...")
        carreras_dict = {}
        for c in CATALOGO_CARRERAS:
            fields = c['fields']
            carr_obj, _ = Carrera.objects.get_or_create(
                codigo_carrera=c['pk'],
                defaults={
                    'nombre_carrera': fields.get('nombre_carrera', ''),
                    'resolucion_vigente': fields.get('resolucion_vigente', ''),
                    'resolucion_anterior': fields.get('resolucion_anterior', ''),
                }
            )
            carreras_dict[c['pk']] = carr_obj

        materias_dict = {}
        for m in CATALOGO_MATERIAS:
            fields = m['fields']
            mat_obj, _ = Materia.objects.get_or_create(
                codigo_materia=m['pk'],
                defaults={'nombre_materia': fields.get('nombre_materia', '')}
            )
            materias_dict[m['pk']] = mat_obj

        planes_creados = []
        for p in CATALOGO_PLANES:
            fields = p['fields']
            carr = carreras_dict.get(fields['carrera'])
            mat = materias_dict.get(fields['materia'])
            if carr and mat:
                plan_obj, _ = PlanEstudio.objects.get_or_create(
                    id_plan=p['pk'],
                    defaults={
                        'carrera': carr,
                        'materia': mat,
                        'anio_carrera': fields.get('anio_carrera', 1),
                        'modalidad': fields.get('modalidad', 'Anual'),
                        'carga_horaria_anual': fields.get('carga_horaria_anual'),
                        'carga_horaria_semanal': fields.get('carga_horaria_semanal'),
                        'correlatividades': fields.get('correlatividades', ''),
                    }
                )
                planes_creados.append(plan_obj)

        self.stdout.write(f"  - {len(carreras_dict)} Carreras, {len(materias_dict)} Materias y {len(planes_creados)} Planes cargados.")

        # 3. Crear Comisiones para cada Plan de Estudio en ciclo lectivo actual
        self.stdout.write("Generando Comisiones academicas...")
        anio_actual = datetime.date.today().year
        comisiones_creadas = []
        for plan in planes_creados:
            cod_com = f"COM_{plan.id_plan}_{anio_actual}"
            com_obj, _ = Comision.objects.get_or_create(
                codigo_comision=cod_com,
                defaults={
                    'plan_estudio': plan,
                    'anio_lectivo': anio_actual,
                    'cuatrimestre': 'Anual',
                    'turno': 'Vespertino',
                    'division': 'A'
                }
            )
            comisiones_creadas.append(com_obj)

        self.stdout.write(f"  - {len(comisiones_creadas)} Comisiones creadas.")

        # 4. Generar Docentes Sintéticos y asignarlos a Comisiones
        self.stdout.write(f"Generando {cant_docentes} docentes sinteticos...")
        docentes_creados = []
        titulos = [
            "Licenciado en Sistemas", "Ingeniero Industrial", "Profesor en Ciencias Exactas",
            "Licenciada en Enfermería", "Técnico Superior en Logística", "Especialista en Seguridad e Higiene"
        ]

        dni_doc_base = 25000000
        for i in range(cant_docentes):
            dni_doc = str(dni_doc_base + i)
            genero = "M" if i % 2 == 0 else "F"
            nombre = NOMBRES_MASCULINOS[i % len(NOMBRES_MASCULINOS)] if genero == "M" else NOMBRES_FEMENINOS[i % len(NOMBRES_FEMENINOS)]
            apellido = APELLIDOS[(i * 3) % len(APELLIDOS)]
            cuil = generar_cuil_sintetico(dni_doc, genero)
            fecha_nac = datetime.date(1975 + (i % 15), 1 + (i % 12), 1 + (i % 25))

            persona = Persona.objects.create(
                dni=dni_doc,
                cuil=cuil,
                nombre=nombre,
                apellido=apellido,
                domicilio=f"{CALLES[i % len(CALLES)]} {100 + i * 15}",
                localidad=LOCALIDADES[i % len(LOCALIDADES)],
                telefono=f"119000{i:04d}",
                mail=f"docente.{i+1}@ejemplo.edu.ar",
                nacionalidad="Argentina",
                fecha_nacimiento=fecha_nac,
                identidad=genero
            )
            docente = Docente.objects.create(
                persona=persona,
                titulo_mn=titulos[i % len(titulos)]
            )
            docentes_creados.append(docente)

        # Asignar docentes a comisiones
        for idx, comision in enumerate(comisiones_creadas):
            doc = docentes_creados[idx % len(docentes_creados)]
            ComisionDocente.objects.get_or_create(
                comision=comision,
                docente=doc,
                defaults={'rol': 'Titular'}
            )

        self.stdout.write(f"  - {len(docentes_creados)} Docentes generados y asignados a comisiones.")

        # 5. Generar Alumnos Sintéticos con Cursadas y Evaluaciones
        self.stdout.write(f"Generando {cant_alumnos} alumnos sinteticos con cursadas y calificaciones...")
        dni_alu_base = 40000000
        random.seed(42)  # Semilla determinística para reproducibilidad
        situaciones = ['Promocionado', 'Final', 'Regular', 'Libre', 'En Cursada']

        for i in range(cant_alumnos):
            dni_alu = str(dni_alu_base + i)
            genero = "M" if i % 2 == 0 else "F"
            nombre = NOMBRES_MASCULINOS[(i * 2) % len(NOMBRES_MASCULINOS)] if genero == "M" else NOMBRES_FEMENINOS[(i * 2) % len(NOMBRES_FEMENINOS)]
            apellido = APELLIDOS[(i * 5) % len(APELLIDOS)]
            cuil = generar_cuil_sintetico(dni_alu, genero)
            fecha_nac = datetime.date(1998 + (i % 8), 1 + (i % 12), 1 + (i % 28))

            persona = Persona.objects.create(
                dni=dni_alu,
                cuil=cuil,
                nombre=nombre,
                apellido=apellido,
                domicilio=f"{CALLES[(i * 2) % len(CALLES)]} {200 + i * 20}",
                localidad=LOCALIDADES[i % len(LOCALIDADES)],
                telefono=f"118000{i:04d}",
                mail=f"alumno.{i+1}@ejemplo.edu.ar",
                nacionalidad="Argentina",
                fecha_nacimiento=fecha_nac,
                identidad=genero
            )
            alumno = Alumno.objects.create(
                persona=persona,
                legajo=f"LEG-{anio_actual}-{i+1:04d}"
            )

            # Inscribir al alumno en 3 comisiones sintéticas
            comisiones_muestra = random.sample(comisiones_creadas, min(3, len(comisiones_creadas)))
            for com in comisiones_muestra:
                situacion = random.choice(situaciones)
                asistencia = round(random.uniform(70.0, 100.0), 2)
                cursada = Cursada.objects.create(
                    comision=com,
                    alumno=alumno,
                    porcentaje_asistencia=asistencia,
                    situacion_final=situacion
                )

                # Evaluaciones asociadas
                nota1 = round(random.uniform(4.0, 10.0), 1)
                nota2 = round(random.uniform(4.0, 10.0), 1)
                Evaluacion.objects.create(
                    cursada=cursada,
                    instancia="Primer Parcial",
                    nota=nota1,
                    fecha=datetime.date(anio_actual, 5, 15)
                )
                Evaluacion.objects.create(
                    cursada=cursada,
                    instancia="Segundo Parcial",
                    nota=nota2,
                    fecha=datetime.date(anio_actual, 10, 20)
                )

        self.stdout.write(self.style.SUCCESS(
            f"¡Sembrado sintético finalizado con éxito! {cant_alumnos} Alumnos y {cant_docentes} Docentes cargados."
        ))
