"""Casos de uso para operaciones administrativas: Libro Matriz, Excel y CRUD de personas."""
import logging
from typing import Any, Dict, Optional, Tuple

from django.apps import apps
from django.db.models import Q

from core.excepciones import ErrorImportacion, RegistroNoEncontradoError, ValidacionError
from modulo_base_datos.models import Alumno, Carrera, Docente, Persona
from .importacion_excel import generar_plantilla_alumnos_excel, procesar_importacion_alumnos_excel
from .libro_matriz import generar_libro_matriz_excel

logger = logging.getLogger(__name__)


class GenerarLibroMatriz:
    """Genera el flujo de bytes de un archivo Excel correspondiente al Libro Matriz de una carrera."""

    def ejecutar(self, codigo_carrera: Optional[str] = None) -> Tuple[Any, str]:
        if codigo_carrera:
            carrera_obj = Carrera.objects.filter(codigo_carrera=codigo_carrera).first()
            if not carrera_obj:
                raise RegistroNoEncontradoError(f"Carrera '{codigo_carrera}' no encontrada.")
        else:
            carrera_obj = (
                Carrera.objects.filter(codigo_carrera='ENERGIA-794').first()
                or Carrera.objects.first()
            )
            if not carrera_obj:
                raise RegistroNoEncontradoError("No hay carreras registradas en el sistema.")

        excel_stream = generar_libro_matriz_excel(carrera_obj)
        nombre_limpio = "".join(
            c for c in carrera_obj.nombre_carrera if c.isalnum() or c in (' ', '_', '-')
        ).rstrip()
        filename = f"LIBRO_MATRIZ_{nombre_limpio.replace(' ', '_')}.xlsx"
        return excel_stream, filename


class GenerarPlantillaAlumnos:
    """Genera la plantilla oficial vacía en Excel (.xlsx) para la carga masiva de alumnos."""

    def ejecutar(self) -> Tuple[Any, str]:
        excel_stream = generar_plantilla_alumnos_excel()
        filename = "Plantilla_Carga_Alumnos_ISFT188.xlsx"
        return excel_stream, filename


class ImportarAlumnosExcel:
    """Procesa e importa un archivo Excel con el listado de alumnos."""

    def ejecutar(self, archivo) -> Dict[str, Any]:
        if not archivo:
            raise ErrorImportacion('No se seleccionó ningún archivo Excel para subir.')
        if not (archivo.name.endswith('.xlsx') or archivo.name.endswith('.xls')):
            raise ErrorImportacion('El archivo debe tener extensión .xlsx o .xls.')
        return procesar_importacion_alumnos_excel(archivo)


class ConsultarPersona:
    """Obtiene los datos personales y de rol (Alumno / Docente) para la edición modal."""

    def ejecutar(self, tipo: str, identificador: str) -> Dict[str, Any]:
        identificador_str = str(identificador).strip()
        persona = Persona.objects.filter(
            Q(dni=identificador_str) | Q(id_persona__iexact=identificador_str)
        ).first()

        if not persona and identificador_str.isdigit():
            persona = Persona.objects.filter(id_persona=int(identificador_str)).first()

        if not persona:
            raise RegistroNoEncontradoError('Persona no encontrada.')

        data = {
            'success': True,
            'id_persona': persona.id_persona,
            'tipo': tipo,
            'dni': persona.dni,
            'cuil': persona.cuil or '',
            'nombre': persona.nombre,
            'apellido': persona.apellido,
            'fecha_nacimiento': persona.fecha_nacimiento.strftime('%Y-%m-%d') if persona.fecha_nacimiento else '',
            'identidad': persona.identidad,
            'nacionalidad': persona.nacionalidad or 'Argentina',
            'localidad': persona.localidad or '',
            'domicilio': persona.domicilio or '',
            'telefono': persona.telefono or '',
            'mail': persona.mail or '',
        }

        if tipo == 'alumno':
            alumno = Alumno.objects.filter(persona=persona).first()
            data['legajo'] = alumno.legajo if alumno else ''
        elif tipo == 'docente':
            docente = Docente.objects.filter(persona=persona).first()
            data['titulo_mn'] = docente.titulo_mn if docente else ''

        return data


class EditarPersona:
    """Procesa la actualización de los datos de un Alumno o Docente mediante sus formularios modulares."""

    def ejecutar(self, tipo: str, identificador: str, post_data: Any) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        identificador_str = str(identificador).strip()
        persona = Persona.objects.filter(
            Q(dni=identificador_str) | Q(id_persona__iexact=identificador_str)
        ).first()

        if not persona and identificador_str.isdigit():
            persona = Persona.objects.filter(id_persona=int(identificador_str)).first()

        if not persona:
            raise RegistroNoEncontradoError('Registro no encontrado.')

        if tipo == 'alumno':
            from modulo_alumnos.forms import AlumnoEditForm
            form = AlumnoEditForm(post_data, instance=persona)
            nombre_rol = "Estudiante"
        elif tipo == 'docente':
            from modulo_docentes.forms import DocenteForm
            form = DocenteForm(post_data, instance=persona)
            nombre_rol = "Docente"
        else:
            raise ValidacionError(f"Tipo '{tipo}' inválido.")

        if form.is_valid():
            form.save()
            mensaje = f"{nombre_rol} {persona.apellido}, {persona.nombre} actualizado/a correctamente."
            return True, mensaje, None
        else:
            errores_dict = {campo: [str(e) for e in errs] for campo, errs in form.errors.items()}
            primer_error = next(iter(form.errors.values()))[0] if form.errors else "Error de validación."
            return False, str(primer_error), errores_dict


class EliminarPersona:
    """Eliminación segura de una Persona (Alumno o Docente) preservando la integridad institucional."""

    def ejecutar(self, tipo: str, identificador: str) -> str:
        identificador_str = str(identificador).strip()
        persona = Persona.objects.filter(
            Q(dni=identificador_str) | Q(id_persona__iexact=identificador_str)
        ).first()

        if not persona and identificador_str.isdigit():
            persona = Persona.objects.filter(id_persona=int(identificador_str)).first()

        if not persona:
            raise RegistroNoEncontradoError('Registro no encontrado.')

        nombre_completo = f"{persona.apellido}, {persona.nombre}"
        dni_persona = persona.dni

        if tipo == 'alumno':
            alumno = Alumno.objects.filter(persona=persona).first()
            if not alumno:
                raise RegistroNoEncontradoError('Perfil de alumno no encontrado.')

            tiene_docente = Docente.objects.filter(persona=persona).exists()
            if tiene_docente:
                alumno.delete()
            else:
                persona.delete()

            # Limpiar en tabla de carga si está registrado
            if apps.is_installed('modulo_alumnos') or apps.is_installed('carga_alumnos'):
                try:
                    for app_label in ['modulo_alumnos', 'carga_alumnos']:
                        if apps.is_installed(app_label):
                            AlumnoCarga = apps.get_model(app_label, 'Alumno')
                            AlumnoCarga.objects.filter(dni=dni_persona).delete()
                except Exception:
                    pass

            return f"El/la estudiante {nombre_completo} (DNI: {dni_persona}) ha sido eliminado/a correctamente del sistema."

        elif tipo == 'docente':
            docente = Docente.objects.filter(persona=persona).first()
            if not docente:
                raise RegistroNoEncontradoError('Perfil de docente no encontrado.')

            tiene_alumno = Alumno.objects.filter(persona=persona).exists()
            if tiene_alumno:
                docente.delete()
            else:
                persona.delete()

            return f"El/la docente {nombre_completo} (DNI: {dni_persona}) ha sido eliminado/a correctamente del sistema."

        else:
            raise ValidacionError(f"Tipo '{tipo}' inválido.")

