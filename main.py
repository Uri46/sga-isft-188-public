"""Orquestador Principal e Inyección de Dependencias (SGA Modular - ISFT N° 188).

Este archivo actúa como el punto de entrada unificado y orquestador del sistema:
1. Expone el contenedor de dependencias (`contenedor`) para su inyección en servicios y casos de uso.
2. Provee interfaz de comandos interactiva o ejecución estándar de Django (`runserver`, `migrate`, `seed`, `test`, `shell`).
"""

import os
import sys
from pathlib import Path

# Configurar el entorno de Django por defecto
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

# Exponer el Contenedor de Inyección de Dependencias para importación directa
from config.contenedor import contenedor, ContenedorDependencias


def menu_interactivo():
    """Consola interactiva para administración y diagnóstico del SGA."""
    print("=" * 65)
    print("      SISTEMA DE GESTIÓN ACADÉMICA (SGA) — ISFT N° 188")
    print("                  Arquitectura Modular v2.0")
    print("=" * 65)
    print("1. Iniciar Servidor Web (0.0.0.0:8000)")
    print("2. Ejecutar Migraciones de Base de Datos")
    print("3. Poblar Datos Iniciales (Seed Data)")
    print("4. Crear / Actualizar Administrador (desde variables de entorno)")
    print("5. Ejecutar Suite de Pruebas Unitarias")
    print("6. Abrir Consola Interactiva de Python (Shell)")
    print("0. Salir")
    print("=" * 65)

    opcion = input("Seleccione una opción: ").strip()

    from django.core.management import call_command

    if opcion == '1':
        puerto = os.environ.get('PORT', '8000')
        print(f"\nIniciando servidor en http://127.0.0.1:{puerto}...")
        call_command('runserver', f'0.0.0.0:{puerto}')
    elif opcion == '2':
        print("\nAplicando migraciones...")
        call_command('migrate')
    elif opcion == '3':
        print("\nPoblando base de datos institucional...")
        call_command('seed_data')
    elif opcion == '4':
        print("\nConfigurando administrador...")
        call_command('crear_usuario_admin')
    elif opcion == '5':
        print("\nEjecutando pruebas de la arquitectura modular...")
        call_command('test', 'tests')
    elif opcion == '6':
        print("\nIniciando consola interactiva Django con contenedor inyectado...")
        call_command('shell')
    elif opcion == '0':
        print("\nSaliendo...")
        sys.exit(0)
    else:
        print("\nOpción inválida.")


def main():
    if len(sys.argv) > 1:
        # Ejecución directa de comandos CLI (ej. python main.py runserver 8000)
        from django.core.management import execute_from_command_line
        execute_from_command_line(sys.argv)
    else:
        # Menú interactivo por defecto si se ejecuta sin argumentos
        try:
            menu_interactivo()
        except KeyboardInterrupt:
            print("\nOperación cancelada por el usuario.")


if __name__ == '__main__':
    main()

