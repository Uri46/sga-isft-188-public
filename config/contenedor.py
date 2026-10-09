"""Contenedor de Inyección de Dependencias del SGA.

Instancia e interconecta repositorios y casos de uso de todos los módulos,
permitiendo desacoplar la capa de presentación de la infraestructura de datos.
"""
from typing import Optional

# Módulo Login
from modulo_login.repositorio import UsuarioRepositorio
from modulo_login.casos_uso import ServicioAutenticacion

# Módulo Carreras
from modulo_carreras.repositorio import CarreraRepositorio
from modulo_carreras.casos_uso import (
    ListarCarreras,
    DetalleCarrera,
    PlanImprimible,
    RegistrarCarrera,
    EliminarCarrera,
    GestionarMateriasPlan,
)

# Módulo Docentes
from modulo_docentes.repositorio import DocenteRepositorio
from modulo_docentes.casos_uso import (
    ListarDocentes,
    RegistrarDocente,
    DetalleDocente,
    FichaDocente,
    ImportarDocentesExcel,
)

# Módulo Alumnos
from modulo_alumnos.repositorio import AlumnoRepositorio
from modulo_alumnos.casos_uso import (
    BuscarAlumnos,
    DetalleAlumno,
    EstadoAcademicoImprimible,
    RegistrarAlumno,
)

# Módulo Gestión
from modulo_gestion.casos_uso import (
    GenerarLibroMatriz,
    GenerarPlantillaAlumnos,
    ImportarAlumnosExcel,
    ConsultarPersona,
    EditarPersona,
    EliminarPersona,
)


class ContenedorDependencias:
    """Orquestador central de repositorios y casos de uso del sistema."""

    def __init__(
        self,
        usuario_repo: Optional[UsuarioRepositorio] = None,
        carrera_repo: Optional[CarreraRepositorio] = None,
        docente_repo: Optional[DocenteRepositorio] = None,
        alumno_repo: Optional[AlumnoRepositorio] = None,
    ):
        # Repositorios
        self.usuario_repositorio = usuario_repo or UsuarioRepositorio()
        self.carrera_repositorio = carrera_repo or CarreraRepositorio()
        self.docente_repositorio = docente_repo or DocenteRepositorio()
        self.alumno_repositorio = alumno_repo or AlumnoRepositorio()

        # Casos de uso - Login
        self.servicio_autenticacion = ServicioAutenticacion(self.usuario_repositorio)

        # Casos de uso - Carreras
        self.listar_carreras = ListarCarreras(self.carrera_repositorio)
        self.detalle_carrera = DetalleCarrera(self.carrera_repositorio)
        self.plan_imprimible = PlanImprimible(self.carrera_repositorio)
        self.registrar_carrera = RegistrarCarrera(self.carrera_repositorio)
        self.eliminar_carrera = EliminarCarrera(self.carrera_repositorio)
        self.materias_plan = GestionarMateriasPlan(self.carrera_repositorio)

        # Casos de uso - Docentes
        self.listar_docentes = ListarDocentes(self.docente_repositorio)
        self.registrar_docente = RegistrarDocente(self.docente_repositorio)
        self.detalle_docente = DetalleDocente(self.docente_repositorio)
        self.ficha_docente = FichaDocente(self.docente_repositorio)
        self.importar_docentes = ImportarDocentesExcel()

        # Casos de uso - Alumnos
        self.buscar_alumnos = BuscarAlumnos(self.alumno_repositorio)
        self.detalle_alumno = DetalleAlumno(self.alumno_repositorio)
        self.estado_academico = EstadoAcademicoImprimible(self.alumno_repositorio)
        self.registrar_alumno = RegistrarAlumno(self.alumno_repositorio)

        # Casos de uso - Gestión Administrativa
        self.generar_libro_matriz = GenerarLibroMatriz()
        self.generar_plantilla_alumnos = GenerarPlantillaAlumnos()
        self.importar_alumnos = ImportarAlumnosExcel()
        self.consultar_persona = ConsultarPersona()
        self.editar_persona = EditarPersona()
        self.eliminar_persona = EliminarPersona()


# Instancia singleton accesible globalmente
contenedor = ContenedorDependencias()

